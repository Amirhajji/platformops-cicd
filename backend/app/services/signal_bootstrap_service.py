# app/services/signal_bootstrap_service.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models.signals import Signal


def bootstrap_signals_from_payload(db: Session):
    """
    Create missing signals directly from payload schema.
    Payload is the source of truth.
    """
    sample = db.execute(
        text("SELECT payload, component_code FROM timeseries_points LIMIT 1")
    ).fetchone()

    if not sample:
        return 0

    payload, component = sample
    existing = {
        s.signal_code for s in db.query(Signal).all()
    }

    created = 0

    for key in payload.keys():
        signal_code = f"{component}.{key}"
        if signal_code in existing:
            continue

        db.add(
            Signal(
                signal_code=signal_code,
                component_code=component,
                column_name=key,
            )
        )
        created += 1

    db.commit()
    return created
