# app/services/signal_service.py
from sqlalchemy.orm import Session
from app.db.models.signals import Signal

def list_signals(db: Session, role: str):
    return (
        db.query(Signal)
        .filter(Signal.visible_to_roles.any(role))
        .order_by(Signal.component_code, Signal.signal_code)
        .all()
    )
