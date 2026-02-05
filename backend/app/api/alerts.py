# app/api/alerts.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.incidents import IncidentAlert
from app.db.session import get_db
from app.db.models.alerts import AlertRule, AlertEvent
from app.db.models.signals import Signal

from app.services.alerts_insight_service import alert_summary, alerts_by_component
from app.services.alert_service import evaluate_alerts



router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


# ------------------------------------------------------------------
# DEBUG
# ------------------------------------------------------------------

@router.get("/ping")
def ping():
    return {"ok": True}


# ------------------------------------------------------------------
# RULES
# ------------------------------------------------------------------

@router.get("/rules")
def list_rules(db: Session = Depends(get_db)):
    return db.query(AlertRule).all()


@router.post("/rules/generate-all")
def generate_all_rules(db: Session = Depends(get_db)):
    from app.services.alert_rule_generator import generate_rules_for_all_metrics
    created = generate_rules_for_all_metrics(db)
    return {
        "created_rules": created,
        "strategy": "metric-family-based",
    }


# ------------------------------------------------------------------
# EVALUATION
# ------------------------------------------------------------------

@router.post("/evaluate")
def evaluate(
    lookback_ticks: int = 200,
    simulation_mode: bool = False,
    db: Session = Depends(get_db),
):
    return evaluate_alerts(
        db=db,
        lookback_ticks=lookback_ticks,
        simulation_mode=simulation_mode,
    )



@router.post("/reset-and-evaluate")
def reset_and_evaluate(
    lookback_ticks: int = 200,
    db: Session = Depends(get_db),
):
    db.query(IncidentAlert).delete()
    db.query(AlertEvent).delete()
    db.commit()

    return evaluate_alerts(
        db=db,
        lookback_ticks=lookback_ticks,
        simulation_mode=False,
    )



# ------------------------------------------------------------------
# EVENTS & INSIGHTS
# ------------------------------------------------------------------

@router.get("/events")
def list_events(
    signal_code: str | None = None,
    status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(AlertEvent)
    if signal_code:
        q = q.filter(AlertEvent.signal_code == signal_code)
    if status:
        q = q.filter(AlertEvent.status == status)

    return q.order_by(AlertEvent.id.desc()).limit(limit).all()


@router.get("/summary")
def alerts_summary(db: Session = Depends(get_db)):
    return alert_summary(db)


@router.get("/by-component/{component_code}")
def alerts_for_component(component_code: str, db: Session = Depends(get_db)):
    return alerts_by_component(db, component_code)
