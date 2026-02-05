# app/services/alert_autogen_service.py
import statistics
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.models.signals import Signal
from app.db.models.alerts import AlertRule


def _baseline(db: Session, signal: Signal, window: int = 50):
    sql = """
        SELECT
            (payload ->> :column)::double precision AS value
        FROM timeseries_points
        WHERE component_code = :component
          AND payload ? :column
        ORDER BY tick DESC
        LIMIT :window
    """

    rows = db.execute(
        text(sql),
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


def autogenerate_alert_rules(db: Session):
    created = 0

    signals = db.query(Signal).all()

    for s in signals:
        # Avoid duplicates
        exists = (
            db.query(AlertRule)
            .filter(AlertRule.signal_code == s.signal_code)
            .first()
        )
        if exists:
            continue

        mean, std = _baseline(db, s)

        # ---------- xi ----------
        if s.signal_type == "xi" and mean is not None:
            threshold = mean + 2 * std if s.polarity == "higher_is_worse" else mean - 2 * std
            rule = AlertRule(
                signal_code=s.signal_code,
                operator=">" if s.polarity == "higher_is_worse" else "<",
                threshold=threshold,
                min_duration_ticks=2,
                severity="MEDIUM",
            )

        # ---------- yi ----------
        elif s.signal_type == "yi":
            rule = AlertRule(
                signal_code=s.signal_code,
                operator="<",
                threshold=70.0,
                min_duration_ticks=3,
                severity="HIGH",
            )

        # ---------- zi ----------
        elif s.signal_type == "zi":
            rule = AlertRule(
                signal_code=s.signal_code,
                operator=">",
                threshold=0.7,
                min_duration_ticks=5,
                severity="CRITICAL",
            )

        else:
            continue

        db.add(rule)
        created += 1

    db.commit()
    return created
