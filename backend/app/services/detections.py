"""Alerts and incidents. They are computed by the loader and only read here."""
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.models import Alert, Incident, Kpi, SimulatedIncident
from app.services.timeline import Run, Window

ALERT = (Alert.id, Alert.kpi_id, Kpi.name.label("kpi_name"), Alert.component_id,
         Alert.start_tick, Alert.end_tick, Alert.min_health)
INCIDENT = (Incident.id, Incident.component_id, Incident.start_tick, Incident.end_tick,
            Incident.alert_count, Incident.min_z)


def _with_times(row: Any, run: Run) -> Dict[str, Any]:
    """Replace ticks by timestamps. end_ts is the last tick of the interval."""
    values = dict(row)
    start, end = values.pop("start_tick"), values.pop("end_tick")
    values.update(start_ts=run.ts(start), end_ts=run.ts(end),
                  duration_seconds=(end - start + 1) * run.tick_seconds)
    return values


def _find(session: Session, query: Any, model: Any, component_id: Optional[str],
          window: Window) -> List[Dict[str, Any]]:
    """Rows whose interval overlaps the window, oldest first."""
    query = query.where(model.start_tick <= window.last,
                        model.end_tick >= window.first)
    if component_id is not None:
        query = query.where(model.component_id == component_id)
    rows = session.execute(query.order_by(model.start_tick, model.id)).mappings()
    return [_with_times(row, window.run) for row in rows]


def list_alerts(session: Session, component_id: Optional[str],
                window: Window) -> List[Dict[str, Any]]:
    query = select(*ALERT).join(Kpi, Kpi.id == Alert.kpi_id)
    return _find(session, query, Alert, component_id, window)


def list_incidents(session: Session, component_id: Optional[str],
                   window: Window) -> List[Dict[str, Any]]:
    return _find(session, select(*INCIDENT), Incident, component_id, window)


def incident_detail(session: Session, incident_id: int, run: Run) -> Dict[str, Any]:
    incident = session.execute(
        select(*INCIDENT).where(Incident.id == incident_id)).mappings().first()
    if incident is None:
        raise not_found("incident", incident_id)
    component_id = incident["component_id"]
    start, end = incident["start_tick"], incident["end_tick"]
    alerts = list_alerts(session, component_id, Window(run, start, end))
    simulated = session.execute(
        select(SimulatedIncident.id, SimulatedIncident.start_tick,
               SimulatedIncident.end_tick, SimulatedIncident.description)
        .where(SimulatedIncident.component_id == component_id,
               SimulatedIncident.start_tick <= end, SimulatedIncident.end_tick >= start)
        .order_by(SimulatedIncident.start_tick)).mappings().first()
    detail = _with_times(incident, run)
    detail.update(alerts=alerts, simulated_incident=(
        None if simulated is None else _with_times(simulated, run)))
    return detail
