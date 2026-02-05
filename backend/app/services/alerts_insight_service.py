# app/services/alerts_insight_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models.alerts import AlertEvent


def alert_summary(db: Session):
    rows = (
        db.query(
            AlertEvent.severity,
            func.count(AlertEvent.id)
        )
        .group_by(AlertEvent.severity)
        .all()
    )

    return {severity: count for severity, count in rows}


def alerts_by_component(db: Session, component_code: str):
    return (
        db.query(AlertEvent)
        .filter(AlertEvent.component_code == component_code)
        .order_by(AlertEvent.id.desc())
        .all()
    )
