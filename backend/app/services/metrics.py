"""Metric catalog search and series. Buckets of metric values are averaged."""
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.db.models import Metric, MetricPoint
from app.services.timeline import Window

MAX_SERIES = 6
MAX_ID = 2 ** 31 - 1  # PostgreSQL integer


def search(session: Session, component_id: Optional[str],
           text: Optional[str]) -> List[Dict[str, Any]]:
    query = select(Metric.id, Metric.component_id, Metric.column_name, Metric.metric_id,
                   Metric.name, Metric.unit, Metric.resource, Metric.level,
                   Metric.period_min, Metric.range_min, Metric.range_max)
    if component_id is not None:
        query = query.where(Metric.component_id == component_id)
    for word in (text or "").split():  # every word must be found
        query = query.where(or_(Metric.column_name.icontains(word, autoescape=True),
                                Metric.name.icontains(word, autoescape=True)))
    return [dict(row) for row in session.execute(query.order_by(Metric.id)).mappings()]


def parse_ids(text: str) -> List[int]:
    parts = [part.strip() for part in text.split(",")]
    if not all(part.isascii() and part.isdigit() and int(part) <= MAX_ID
               for part in parts):
        raise bad_request("ids: must be metric ids separated by commas")
    ids = list(dict.fromkeys(int(part) for part in parts))
    if len(ids) > MAX_SERIES:
        raise bad_request(f"ids: at most {MAX_SERIES} metrics")
    return ids


def series(session: Session, ids: List[int], window: Window) -> Dict[str, Any]:
    found = {row["id"]: dict(row) for row in session.execute(
        select(Metric.id, Metric.column_name, Metric.name, Metric.unit)
        .where(Metric.id.in_(ids))).mappings()}
    for metric_id in ids:
        if metric_id not in found:
            raise not_found("metric", metric_id)
    bucket = window.bucket_of(MetricPoint.tick)
    rows = session.execute(
        select(MetricPoint.metric_id, bucket, func.avg(MetricPoint.value))
        .where(MetricPoint.metric_id.in_(ids),
               MetricPoint.tick.between(window.first, window.last))
        .group_by(MetricPoint.metric_id, "bucket")
        .order_by(MetricPoint.metric_id, "bucket"))
    for metric in found.values():
        metric["values"] = []
    for metric_id, _, value in rows:
        found[metric_id]["values"].append(value)
    return {"bucket_ticks": window.bucket_ticks, "ts": window.axis(),
            "series": [found[metric_id] for metric_id in ids]}
