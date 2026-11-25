"""KPIs and KQIs: overview, components, series.

Buckets: KPI values are averaged, health and z keep their minimum, so that incidents
stay visible.
"""
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.models import Alert, Component, Incident, Kpi, KpiPoint, KqiPoint
from app.services.timeline import Run, Window

GLOBAL = "GLOBAL"


def list_components(session: Session) -> List[Dict[str, Any]]:
    rows = session.execute(select(Component.id, Component.name, Component.namespace)
                           .order_by(Component.id))
    return [dict(row) for row in rows.mappings()]


def require_component(session: Session, component_id: str) -> Dict[str, Any]:
    for component in list_components(session):
        if component["id"] == component_id:
            return component
    raise not_found("component", component_id)


def overview(session: Session, window: Window) -> Dict[str, Any]:
    at_end = {scope: (z, status) for scope, z, status in session.execute(
        select(KqiPoint.scope, KqiPoint.z, KqiPoint.status)
        .where(KqiPoint.tick == window.last))}
    lowest = {scope: z for scope, z in session.execute(
        select(KqiPoint.scope, func.min(KqiPoint.z))
        .where(KqiPoint.tick.between(window.first, window.last))
        .group_by(KqiPoint.scope))}
    alerts = _count_by_component(session, Alert, window)
    incidents = _count_by_component(session, Incident, window)
    alerts[GLOBAL], incidents[GLOBAL] = sum(alerts.values()), sum(incidents.values())
    names = [(GLOBAL, "Global")] + [(c["id"], c["name"]) for c in list_components(session)]
    return {
        "from_ts": window.run.ts(window.first),
        "to_ts": window.run.ts(window.last),
        "scopes": [{"scope": scope, "name": name, "z": at_end[scope][0],
                    "status": at_end[scope][1], "min_z": lowest[scope],
                    "alerts": alerts.get(scope, 0), "incidents": incidents.get(scope, 0)}
                   for scope, name in names],
    }


def _count_by_component(session: Session, model: Any, window: Window) -> Dict[str, int]:
    """Alerts or incidents whose interval overlaps the window."""
    rows = session.execute(
        select(model.component_id, func.count())
        .where(model.start_tick <= window.last, model.end_tick >= window.first)
        .group_by(model.component_id))
    return {component_id: count for component_id, count in rows}


def kqi_series(session: Session, scope: str, window: Window) -> Dict[str, Any]:
    if scope != GLOBAL:
        require_component(session, scope)
    bucket = window.bucket_of(KqiPoint.tick)
    worst_first = aggregate_order_by(KqiPoint.status, KqiPoint.z, KqiPoint.tick)
    rows = session.execute(
        select(bucket, func.min(KqiPoint.z), func.array_agg(worst_first)[1])
        .where(KqiPoint.scope == scope,
               KqiPoint.tick.between(window.first, window.last))
        .group_by("bucket").order_by("bucket")).all()
    return {"scope": scope, "bucket_ticks": window.bucket_ticks, "ts": window.axis(),
            "z": [row[1] for row in rows], "status": [row[2] for row in rows]}


def component_detail(session: Session, component_id: str, run: Run,
                     tick: int) -> Dict[str, Any]:
    component = require_component(session, component_id)
    z, status = session.execute(
        select(KqiPoint.z, KqiPoint.status)
        .where(KqiPoint.scope == component_id, KqiPoint.tick == tick)).one()
    kpis = session.execute(
        select(Kpi.id, Kpi.name, Kpi.signal, Kpi.type, KpiPoint.value, KpiPoint.health,
               Kpi.good, Kpi.bad, Kpi.better)
        .join(KpiPoint, KpiPoint.kpi_id == Kpi.id)
        .where(Kpi.component_id == component_id, KpiPoint.tick == tick)
        .order_by(Kpi.id))
    detail = dict(component)
    detail.update(at=run.ts(tick), z=z, status=status,
                  kpis=[dict(row) for row in kpis.mappings()])
    return detail


def kpi_series(session: Session, kpi_id: str, window: Window) -> Dict[str, Any]:
    kpi = session.execute(
        select(Kpi.id, Kpi.component_id, Kpi.name, Kpi.good, Kpi.bad, Kpi.better)
        .where(Kpi.id == kpi_id)).mappings().first()
    if kpi is None:
        raise not_found("KPI", kpi_id)
    bucket = window.bucket_of(KpiPoint.tick)
    rows = session.execute(
        select(bucket, func.avg(KpiPoint.value), func.min(KpiPoint.health))
        .where(KpiPoint.kpi_id == kpi_id,
               KpiPoint.tick.between(window.first, window.last))
        .group_by("bucket").order_by("bucket")).all()
    series = dict(kpi)
    series.update(bucket_ticks=window.bucket_ticks, ts=window.axis(),
                  value=[row[1] for row in rows], health=[row[2] for row in rows])
    return series
