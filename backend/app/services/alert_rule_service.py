# app/services/alert_rule_service.py
import statistics
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models.alerts import AlertRule
from app.db.models.signals import Signal


def _baseline(db: Session, signal: Signal, window: int = 50):
    rows = db.execute(
        text("""
            SELECT (payload ->> :column)::double precision AS value
            FROM timeseries_points
            WHERE component_code = :component
              AND payload ? :column
            ORDER BY tick DESC
            LIMIT :window
        """),
        {
            "column": signal.column_name,
            "component": signal.component_code,
            "window": window,
        },
    ).fetchall()

    values = [r.value for r in rows if r.value is not None]

    if len(values) < 5:
        return None, None

    return statistics.mean(values), statistics.stdev(values)


def generate_rules_for_all_signals(db: Session) -> int:
    existing = {
        r.signal_code for r in db.query(AlertRule.signal_code).all()
    }

    created = 0

    for s in db.query(Signal).all():
        if s.signal_code in existing:
            continue

        mean, std = _baseline(db, s)

        # ---------------- xi ----------------
        if s.signal_type == "xi":
            if mean is not None and std is not None:
                threshold = (
                    mean + 2 * std
                    if s.polarity == "higher_is_worse"
                    else mean - 2 * std
                )
            else:
                # fallback — safe generic
                threshold = 1.0

            operator = "gt" if s.polarity == "higher_is_worse" else "lt"

            rule = AlertRule(
                signal_code=s.signal_code,
                operator=operator,
                threshold=threshold,
                min_duration_ticks=2,
                severity="warning",
                enabled=True,
            )

        # ---------------- yi ----------------
        elif s.signal_type == "yi":
            rule = AlertRule(
                signal_code=s.signal_code,
                operator="lt",
                threshold=70.0,
                min_duration_ticks=3,
                severity="warning",
                enabled=True,
            )

        # ---------------- zi ----------------
        elif s.signal_type == "zi":
            rule = AlertRule(
                signal_code=s.signal_code,
                operator="gt",
                threshold=0.7,
                min_duration_ticks=5,
                severity="critical",
                enabled=True,
            )

        else:
            # ABSOLUTE SAFETY NET
            rule = AlertRule(
                signal_code=s.signal_code,
                operator="ne",
                threshold=-1,
                min_duration_ticks=999999,
                severity="info",
                enabled=False,
            )

        db.add(rule)
        created += 1

    db.commit()
    return created
