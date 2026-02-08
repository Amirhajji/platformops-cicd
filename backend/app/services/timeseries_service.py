import statistics
import math
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import Float, text

from app.db.models.signals import Signal
from app.db.models.timeseries import TimeSeriesPoint


def get_timeseries(
    db: Session,
    signal_code: str,
    from_tick: Optional[int],
    to_tick: Optional[int],
):
    # 1️⃣ Load signal metadata
    signal = (
        db.query(Signal)
        .filter(Signal.signal_code == signal_code)
        .one_or_none()
    )

    if not signal:
        raise ValueError(f"Unknown signal_code: {signal_code}")

    component_code = signal.component_code
    column_name = signal.column_name

    # 2️⃣ Build SQL dynamically (JSONB extraction)
    sql = f"""
        SELECT
            tick,
            timestamp,
            (payload ->> :column_name)::double precision AS value
        FROM timeseries_points
        WHERE component_code = :component_code
          AND payload ? :column_name
    """

    params = {
        "component_code": component_code,
        "column_name": column_name,
    }

    if from_tick is not None:
        sql += " AND tick >= :from_tick"
        params["from_tick"] = from_tick

    if to_tick is not None:
        sql += " AND tick <= :to_tick"
        params["to_tick"] = to_tick

    sql += " ORDER BY tick"

    rows = db.execute(text(sql), params).fetchall()

    # 3️⃣ Format for frontend charts
    return [
        {
            "tick": r.tick,
            "timestamp": r.timestamp,
            "value": r.value,
        }
        for r in rows
    ]


def _extract_series(db, component_code, column_name, limit=30):
    rows = (
        db.query(
            TimeSeriesPoint.tick,
            TimeSeriesPoint.payload[column_name].astext.cast(Float)
        )
        .filter(TimeSeriesPoint.component_code == component_code)
        .order_by(TimeSeriesPoint.tick.desc())
        .limit(limit)
        .all()
    )

    return [r[1] for r in reversed(rows) if r[1] is not None]


# ---------- VOLATILITY ----------
def compute_volatility(db: Session, signal_code: str, window: int = 30):
    signal = db.query(Signal).filter(Signal.signal_code == signal_code).first()
    if not signal:
        return 0.0

    values = _extract_series(db, signal.component_code, signal.column_name, window)

    if len(values) < 2:
        return 0.0

    return statistics.stdev(values)


# ---------- DEGRADATION ----------
def detect_degradation(db: Session, role: str, window: int = 20):
    signals = db.query(Signal).all()
    results = []

    for s in signals:
        if role not in s.visible_to_roles and "admin" not in s.visible_to_roles:
            continue

        values = _extract_series(db, s.component_code, s.column_name, window)
        if len(values) < 2:
            continue

        slope = (values[-1] - values[0]) / window

        if s.polarity == "higher_is_worse" and slope > 0:
            results.append({"signal": s.signal_code, "slope": slope})

        if s.polarity == "lower_is_worse" and slope < 0:
            results.append({"signal": s.signal_code, "slope": slope})

    return results


# ---------- COMPONENT HEALTH ----------
def component_health(db: Session, component_code: str):
    signals = (
        db.query(Signal)
        .filter(Signal.component_code == component_code, Signal.signal_type == "yi")
        .all()
    )

    scores = []

    for s in signals:
        values = _extract_series(db, component_code, s.column_name, limit=1)
        if values:
            scores.append(values[0])

    if not scores:
        return 100.0

    return max(0.0, 100.0 - sum(scores) / len(scores))


# ---------- GLOBAL HEALTH ----------
def global_health(db: Session):
    signal = db.query(Signal).filter(
        Signal.signal_code == "GLOBAL.z9_collapse_risk"
    ).first()

    values = _extract_series(db, "GLOBAL", signal.column_name, limit=1)
    risk = values[0] if values else 0.0

    return {
        "collapse_risk": risk,
        "status": "CRITICAL" if risk > 0.7 else "DEGRADED" if risk > 0.4 else "STABLE"
    }


def multi_signal(db, signal_codes):
    result = {}

    for code in signal_codes:
        try:
            result[code] = get_timeseries(
                db=db,
                signal_code=code.strip(),
                from_tick=None,
                to_tick=None,
            )
        except Exception as e:
            result[code] = {"error": str(e)}

    return result


def aggregate_signal(db, signal_code: str, window: int = 10, agg_type: str = "avg"):
    points = get_timeseries(db, signal_code, None, None)

    if not points:
        return []

    result = []

    for i in range(0, len(points), window):
        chunk = points[i:i + window]
        if not chunk:
            continue

        values = [p["value"] for p in chunk]

        if agg_type == "avg":
            agg_value = sum(values) / len(values)
        elif agg_type == "min":
            agg_value = min(values)
        elif agg_type == "max":
            agg_value = max(values)
        elif agg_type == "sum":
            agg_value = sum(values)
        else:
            raise ValueError(f"Unknown aggregation type: {agg_type}")

        result.append({
            "tick": chunk[0]["tick"],
            "timestamp": chunk[0]["timestamp"],
            "value": agg_value
        })

    return result


def derivative_signal(db, signal_code: str):
    signal_code = signal_code.strip()
    points = get_timeseries(db, signal_code, None, None)

    if len(points) < 2:
        return []

    derivatives = []
    prev = points[0]

    for curr in points[1:]:
        derivatives.append({
            "tick": curr["tick"],
            "timestamp": curr["timestamp"],
            "value": curr["value"] - prev["value"]
        })
        prev = curr

    return derivatives


def normalize_signal(db, signal_code: str):
    signal_code = signal_code.strip()
    points = get_timeseries(db, signal_code, None, None)

    if not points:
        return []

    values = [p["value"] for p in points]
    min_v = min(values)
    max_v = max(values)

    if max_v == min_v:
        return [
            {
                "tick": p["tick"],
                "timestamp": p["timestamp"],
                "value": 0.0
            }
            for p in points
        ]

    normalized = []
    for p in points:
        normalized.append({
            "tick": p["tick"],
            "timestamp": p["timestamp"],
            "value": (p["value"] - min_v) / (max_v - min_v)
        })

    return normalized
