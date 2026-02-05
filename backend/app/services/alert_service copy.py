# app/services/alert_service.py
from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.models.alerts import AlertRule, AlertEvent
from app.db.models.signals import Signal

OPERATORS = {
    "gt":  lambda v, t: v > t,
    "gte": lambda v, t: v >= t,
    "lt":  lambda v, t: v < t,
    "lte": lambda v, t: v <= t,
    "eq":  lambda v, t: v == t,
    "ne":  lambda v, t: v != t,
}


def _close_all_open_baseline(db: Session, rule_id: int):
    db.query(AlertEvent).filter(
        AlertEvent.rule_id == rule_id,
        AlertEvent.status == "OPEN",
    ).update({"status": "CLOSED"})


def _delete_simulated_for_rule(db: Session, rule_id: int):
    db.query(AlertEvent).filter(
        AlertEvent.rule_id == rule_id,
        AlertEvent.status == "SIMULATED",
    ).delete()


def evaluate_alerts(
    db: Session,
    lookback_ticks: int = 200,
    simulation_mode: bool = False,
) -> Dict[str, Any]:

    rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()
    signals = {s.signal_code: s for s in db.query(Signal).all()}

    evaluated = created = closed = updated = 0
    origin = "SIMULATED" if simulation_mode else "REAL"

    for rule in rules:
        signal = signals.get(rule.signal_code)
        if not signal:
            continue

        op = OPERATORS.get(rule.operator)
        if not op:
            continue

        # Fetch existing OPEN alert (if any)
        open_alert = (
            db.query(AlertEvent)
            .filter(
                AlertEvent.rule_id == rule.id,
                AlertEvent.component_code == signal.component_code,
                AlertEvent.status == "OPEN",
                AlertEvent.origin == origin,
            )
            .one_or_none()
        )

        sql = """
            SELECT tick,
                   (payload ->> :column)::double precision AS value
            FROM timeseries_points
            WHERE component_code = :component
              AND payload ? :column
            ORDER BY tick DESC
            LIMIT :limit
        """

        rows = db.execute(
            text(sql),
            {
                "component": signal.component_code,
                "column": signal.column_name,
                "limit": lookback_ticks,
            },
        ).fetchall()

        if not rows:
            continue

        rows = list(reversed(rows))

        streak = 0
        start_tick = None
        peak = None
        violated_now = False

        for tick, value in rows:
            if value is None:
                streak = 0
                start_tick = None
                peak = None
                continue

            if op(value, rule.threshold):
                streak += 1
                peak = value if peak is None else max(peak, value)
                start_tick = start_tick or tick

                if streak >= rule.min_duration_ticks:
                    violated_now = True
                    break
            else:
                streak = 0
                start_tick = None
                peak = None

        # ---------- STATE TRANSITIONS ----------

        if violated_now:
            if open_alert:
                open_alert.tick_end = tick
                open_alert.peak_value = max(open_alert.peak_value, peak)
                updated += 1
            else:
                db.add(
                    AlertEvent(
                        rule_id=rule.id,
                        component_code=signal.component_code,
                        signal_code=signal.signal_code,
                        tick_start=start_tick,
                        tick_end=tick,
                        peak_value=peak,
                        severity=rule.severity,
                        status="OPEN",
                        origin=origin,
                    )
                )
                created += 1
        else:
            if open_alert:
                open_alert.status = "CLOSED"
                closed += 1

        evaluated += 1

    db.commit()

    return {
        "evaluated_rules": evaluated,
        "created_events": created,
        "updated_events": updated,
        "closed_events": closed,
        "origin": origin,
    }
