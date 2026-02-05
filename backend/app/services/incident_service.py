# app/services/incident_service.py
from sqlalchemy.orm import Session
from collections import defaultdict

from app.db.models.alerts import AlertEvent
from app.db.models.incidents import Incident, IncidentAlert
from app.core.config import settings
from app.services.incident_notification_service import send_incident_summary_email


CRITICAL_THRESHOLD = 2
SUSTAINED_TICKS = 10


def evaluate_incidents(db: Session) -> dict:
    created = 0
    resolved = 0

    new_incidents: list[Incident] = []
    alerts_by_incident: dict[int, list[AlertEvent]] = defaultdict(list)

    alerts = (
        db.query(AlertEvent)
        .filter(
            AlertEvent.status == "OPEN",
            AlertEvent.origin == "REAL",
            AlertEvent.severity == "critical",
        )
        .all()
    )

    alerts_by_component = defaultdict(list)
    for a in alerts:
        alerts_by_component[a.component_code].append(a)

    for component, component_alerts in alerts_by_component.items():

        open_incident = (
            db.query(Incident)
            .filter(
                Incident.component_code == component,
                Incident.status == "OPEN",
                Incident.origin == "REAL",
            )
            .one_or_none()
        )

        density_trigger = len(component_alerts) >= CRITICAL_THRESHOLD
        sustained_trigger = any(
            (a.tick_end - a.tick_start) >= SUSTAINED_TICKS
            for a in component_alerts
            if a.tick_end is not None
        )

        if density_trigger or sustained_trigger:
            if not open_incident:
                incident = Incident(
                    component_code=component,
                    start_tick=min(a.tick_start for a in component_alerts),
                    severity="critical",
                    status="OPEN",
                    origin="REAL",
                    summary=f"Critical degradation detected on component {component}",
                )
                db.add(incident)
                db.flush()

                for a in component_alerts:
                    db.add(
                        IncidentAlert(
                            incident_id=incident.id,
                            alert_event_id=a.id,
                        )
                    )
                    alerts_by_incident[incident.id].append(a)

                new_incidents.append(incident)
                created += 1

        else:
            if open_incident:
                open_incident.status = "RESOLVED"
                open_incident.end_tick = max(
                    a.tick_end for a in component_alerts if a.tick_end is not None
                )
                resolved += 1

    db.commit()

    # 🔥 ONE EMAIL FOR ALL INCIDENTS
    if new_incidents:
        send_incident_summary_email(
            incidents=new_incidents,
            alerts_by_incident=alerts_by_incident,
            to_email=settings.SMTP_FROM_EMAIL,
        )

    return {
        "created_incidents": created,
        "resolved_incidents": resolved,
    }
