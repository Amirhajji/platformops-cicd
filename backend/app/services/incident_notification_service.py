# app/services/incident_notification_service.py
from typing import Dict, List
from collections import defaultdict

from app.db.models.alerts import AlertEvent
from app.db.models.incidents import Incident
from app.services.email_service import send_email


def send_incident_summary_email(
    incidents: List[Incident],
    alerts_by_incident: Dict[int, List[AlertEvent]],
    to_email: str,
):
    subject = f"[INCIDENT REPORT] {len(incidents)} new critical incident(s) detected"

    lines = [
        "🚨 PlatformOPS Incident Report",
        "",
        f"New incidents detected: {len(incidents)}",
        "",
        "=" * 60,
    ]

    for inc in incidents:
        lines.extend([
            "",
            f"📌 Incident #{inc.id}",
            f"Component      : {inc.component_code}",
            f"Severity       : {inc.severity}",
            f"Start tick     : {inc.start_tick}",
            f"Summary        : {inc.summary}",
            "",
            "🔎 Observations:",
            "- Sustained metric violations detected",
            "- Alert density exceeded safe thresholds",
            "",
            "⚠️ Contributing alerts:",
        ])

        alerts = alerts_by_incident.get(inc.id, [])
        for a in alerts:
            duration = (
                a.tick_end - a.tick_start
                if a.tick_end is not None
                else "ongoing"
            )
            lines.append(
                f"  • {a.signal_code} | "
                f"severity={a.severity} | "
                f"duration={duration} | "
                f"peak={a.peak_value}"
            )

        lines.append("-" * 60)

    lines.extend([
        "",
        "🧠 Operational insight:",
        "These incidents indicate real service degradation.",
        "Recommended actions:",
        "- Inspect upstream dependencies",
        "- Check recent deployments",
        "- Monitor recovery metrics",
        "",
        "This email was generated automatically by PlatformOPS.",
    ])

    send_email(
        to_email=to_email,
        subject=subject,
        text="\n".join(lines),
    )
