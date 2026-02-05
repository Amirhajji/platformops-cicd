# app/services/anomaly_insight_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any

from app.db.models.anomalies import InjectedAnomaly


def active_anomalies(db: Session) -> Dict[str, Any]:
    rows = (
        db.query(
            InjectedAnomaly.anomaly_type,
            InjectedAnomaly.component_code,
            func.min(InjectedAnomaly.tick).label("from_tick"),
            func.max(InjectedAnomaly.tick).label("to_tick"),
            func.count(InjectedAnomaly.id).label("points"),
        )
        .group_by(
            InjectedAnomaly.anomaly_type,
            InjectedAnomaly.component_code,
        )
        .all()
    )

    components = set()
    total_points = 0
    items = []

    for r in rows:
        components.add(r.component_code)
        total_points += r.points

        items.append({
            "anomaly_type": r.anomaly_type,
            "component_code": r.component_code,
            "from_tick": int(r.from_tick),
            "to_tick": int(r.to_tick),
            "points_modified": int(r.points),
        })

    return {
        "active": len(items) > 0,
        "total_points_modified": int(total_points),
        "affected_components": sorted(list(components)),
        "anomalies": items,
    }
