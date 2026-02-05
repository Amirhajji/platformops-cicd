# app/services/analytics_service.py
import statistics
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import Float, func, text , case

from app.db.models.signals import Signal
from app.db.models.timeseries import TimeSeriesPoint
from app.db.models.alerts import AlertRule, AlertEvent
from typing import Dict, Any, List
import statistics
import math

from sqlalchemy import Float
from collections import defaultdict
import statistics
from sqlalchemy import text








# ---------- INTERNAL HELPER ----------
def _extract_series(db: Session, component_code: str, column_name: str, limit: int = 30) -> List[float]:
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
def compute_volatility(db: Session, signal_code: str, window: int):
    signal = (
        db.query(Signal)
        .filter(Signal.signal_code == signal_code)
        .one_or_none()
    )
    if not signal:
        raise ValueError("Signal not found")

    series = _extract_series(db, signal.component_code, signal.column_name, window)

    # 🔥 FIX: extract only values
    values = [v for _, v in series]

    if len(values) < 2:
        return 0.0

    return statistics.stdev(values)



# ---------- DEGRADATION ----------
def detect_degradation(db: Session, role: str, window: int = 20):
    signals = db.query(Signal).all()
    results = []

    for s in signals:
        if s.visible_to_roles and role not in s.visible_to_roles and "admin" not in s.visible_to_roles:
            continue

        values = _extract_series(db, s.component_code, s.column_name, window)
        if len(values) < 2:
            continue

        slope = (values[-1] - values[0]) / max(window, 1)

        if s.polarity == "higher_is_worse" and slope > 0:
            results.append({"signal_code": s.signal_code, "slope": slope, "polarity": s.polarity})

        if s.polarity == "lower_is_worse" and slope < 0:
            results.append({"signal_code": s.signal_code, "slope": slope, "polarity": s.polarity})

    return results


# ---------- COMPONENT HEALTH ----------
def component_health(db: Session, component_code: str):
    signals = (
        db.query(Signal)
        .filter(
            Signal.component_code == component_code,
            Signal.signal_type == "yi",
        )
        .all()
    )

    values = []

    for s in signals:
        series = _extract_series(
            db,
            component_code,
            s.column_name,
            limit=1
        )
        if series:
            value = series[0]
            if isinstance(value, tuple):
                value = value[0]

            if value is not None:
                values.append(float(value))

    if not values:
        return 100.0

    return max(0.0, 100.0 - (sum(values) / len(values)))



# ---------- GLOBAL HEALTH ----------
def global_health(db: Session):
    """
    Compute global health dynamically from OPEN alerts.
    No system_health table required.
    """

    rows = (
        db.query(
            AlertEvent.severity,
            func.count(AlertEvent.id)
        )
        .filter(AlertEvent.status == "OPEN")
        .group_by(AlertEvent.severity)
        .all()
    )

    counts = {sev: cnt for sev, cnt in rows}

    critical = counts.get("critical", 0)
    warning = counts.get("warning", 0)

    total = critical + warning

    if total == 0:
        return {
            "collapse_risk": 0.0,
            "status": "STABLE",
        }

    # Simple, explainable risk model
    collapse_risk = min(1.0, (critical * 2 + warning) / max(total * 2, 1))

    status = (
        "CRITICAL" if collapse_risk > 0.7
        else "DEGRADED" if collapse_risk > 0.3
        else "STABLE"
    )

    return {
        "collapse_risk": round(collapse_risk, 3),
        "status": status,
    }

# =========================================================
# NEW GLOBAL ANALYTICS
# =========================================================

def system_stats(db: Session) -> Dict[str, Any]:
    # ingestion stats
    total_rows = db.query(func.count(TimeSeriesPoint.id)).scalar() or 0

    tick_min, tick_max = db.query(
        func.min(TimeSeriesPoint.tick),
        func.max(TimeSeriesPoint.tick),
    ).one()

    components_count = db.query(func.count(func.distinct(TimeSeriesPoint.component_code))).scalar() or 0

    latest_ticks = db.query(
        TimeSeriesPoint.component_code,
        func.max(TimeSeriesPoint.tick)
    ).group_by(TimeSeriesPoint.component_code).all()

    latest_tick_by_component = {c: int(t) for c, t in latest_ticks if t is not None}

    # signals inventory
    total_signals = db.query(func.count(Signal.signal_code)).scalar() or 0

    by_type_rows = db.query(Signal.signal_type, func.count(Signal.signal_code)).group_by(Signal.signal_type).all()
    by_type = {t or "unknown": int(cnt) for t, cnt in by_type_rows}

    by_family_rows = db.query(Signal.family, func.count(Signal.signal_code)).group_by(Signal.family).all()
    by_family = {f or "unknown": int(cnt) for f, cnt in by_family_rows}

    # role visibility distribution
    # visible_to_roles is an ARRAY, easiest is to iterate (signals count is small ~1k)
    role_counts: Dict[str, int] = {}
    for s in db.query(Signal.visible_to_roles).all():
        roles = s[0] or []
        for r in roles:
            role_counts[r] = role_counts.get(r, 0) + 1

    # rules coverage
    total_rules = db.query(func.count(AlertRule.id)).scalar() or 0
    signals_with_rule = db.query(func.count(func.distinct(AlertRule.signal_code))).scalar() or 0
    coverage_ratio = float(signals_with_rule / total_signals) if total_signals else 0.0

    # events stats
    total_events = db.query(func.count(AlertEvent.id)).scalar() or 0

    by_sev_rows = db.query(AlertEvent.severity, func.count(AlertEvent.id)).group_by(AlertEvent.severity).all()
    by_severity = {s or "unknown": int(cnt) for s, cnt in by_sev_rows}

    by_status_rows = db.query(AlertEvent.status, func.count(AlertEvent.id)).group_by(AlertEvent.status).all()
    by_status = {s or "unknown": int(cnt) for s, cnt in by_status_rows}

    return {
        "ingestion": {
            "total_rows": int(total_rows),
            "components": int(components_count),
            "tick_range": {"min_tick": tick_min, "max_tick": tick_max},
            "latest_tick_by_component": latest_tick_by_component,
        },
        "signals": {
            "total_signals": int(total_signals),
            "by_type": by_type,
            "by_family": by_family,
            "by_role_visibility": role_counts,
        },
        "rules": {
            "total_rules": int(total_rules),
            "signals_with_rule": int(signals_with_rule),
            "rule_coverage_ratio": coverage_ratio,
        },
        "events": {
            "total_events": int(total_events),
            "by_severity": by_severity,
            "by_status": by_status,
        }
    }


def alerts_stats(
    db: Session,
    from_tick: Optional[int] = None,
    to_tick: Optional[int] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    q = db.query(AlertEvent)

    if from_tick is not None:
        q = q.filter(AlertEvent.tick_end >= from_tick)
    if to_tick is not None:
        q = q.filter(AlertEvent.tick_start <= to_tick)

    total_events = q.count()

    # severity / status breakdown
    by_sev = dict(
        q.with_entities(AlertEvent.severity, func.count(AlertEvent.id))
        .group_by(AlertEvent.severity)
        .all()
    )
    by_sev = {k or "unknown": int(v) for k, v in by_sev.items()}

    by_status = dict(
        q.with_entities(AlertEvent.status, func.count(AlertEvent.id))
        .group_by(AlertEvent.status)
        .all()
    )
    by_status = {k or "unknown": int(v) for k, v in by_status.items()}

    # top components and signals
    top_components = (
        q.with_entities(AlertEvent.component_code, func.count(AlertEvent.id).label("cnt"))
        .group_by(AlertEvent.component_code)
        .order_by(text("cnt DESC"))
        .limit(limit)
        .all()
    )

    top_signals = (
        q.with_entities(AlertEvent.signal_code, func.count(AlertEvent.id).label("cnt"))
        .group_by(AlertEvent.signal_code)
        .order_by(text("cnt DESC"))
        .limit(limit)
        .all()
    )

    # longest open alerts
    open_q = q.filter(AlertEvent.status == "OPEN")

    # duration_ticks = tick_end - tick_start (tick_end can be None during creation, but in your code it's set)
    longest_open = (
        open_q.with_entities(
            AlertEvent.id,
            AlertEvent.component_code,
            AlertEvent.signal_code,
            AlertEvent.severity,
            AlertEvent.tick_start,
            AlertEvent.tick_end,
            (AlertEvent.tick_end - AlertEvent.tick_start).label("duration_ticks"),
        )
        .order_by(text("duration_ticks DESC"))
        .limit(limit)
        .all()
    )

    return {
        "window": {"from_tick": from_tick, "to_tick": to_tick},
        "totals": {"total_events": int(total_events)},
        "by_severity": by_sev,
        "by_status": by_status,
        "top_components": [{"key": c or "unknown", "count": int(cnt)} for c, cnt in top_components],
        "top_signals": [{"key": s or "unknown", "count": int(cnt)} for s, cnt in top_signals],
        "longest_open": [
            {
                "alert_event_id": int(r[0]),
                "component_code": r[1],
                "signal_code": r[2],
                "severity": r[3],
                "tick_start": r[4],
                "tick_end": r[5],
                "duration_ticks": int(r[6]) if r[6] is not None else None,
            }
            for r in longest_open
        ],
    }


def component_rankings(db: Session, limit: int = 10) -> Dict[str, Any]:
    components = db.query(Signal.component_code).distinct().all()
    components = [c[0] for c in components if c and c[0]]

    ranked = []

    for comp in components:
        health = float(component_health(db, comp))

        open_events = (
            db.query(func.count(AlertEvent.id))
            .filter(AlertEvent.component_code == comp, AlertEvent.status == "OPEN")
            .scalar()
            or 0
        )

        critical_open = (
            db.query(func.count(AlertEvent.id))
            .filter(
                AlertEvent.component_code == comp,
                AlertEvent.status == "OPEN",
                AlertEvent.severity == "critical",
            )
            .scalar()
            or 0
        )

        warning_open = (
            db.query(func.count(AlertEvent.id))
            .filter(
                AlertEvent.component_code == comp,
                AlertEvent.status == "OPEN",
                AlertEvent.severity == "warning",
            )
            .scalar()
            or 0
        )

        # Composite risk score (simple but meaningful):
        # - critical weighs heavily
        # - warning weighs moderately
        # - low health increases risk
        risk_score = (critical_open * 5.0) + (warning_open * 1.5) + max(0.0, (100.0 - health) / 10.0)

        ranked.append({
            "component_code": comp,
            "health_score": health,
            "open_alerts": int(open_events),
            "critical_open_alerts": int(critical_open),
            "warning_open_alerts": int(warning_open),
            "risk_score": float(risk_score),
        })

    ranked.sort(key=lambda x: x["risk_score"], reverse=True)
    return {"ranked": ranked[:limit]}


def signal_coverage(db: Session, window_ticks: int = 200, limit: int = 20) -> Dict[str, Any]:
    # find max tick globally
    max_tick = db.query(func.max(TimeSeriesPoint.tick)).scalar()
    if max_tick is None:
        return {"window_ticks": window_ticks, "worst": []}

    from_tick = int(max_tick) - int(window_ticks) + 1

    # total points per component in window
    component_points = dict(
        db.query(
            TimeSeriesPoint.component_code,
            func.count(TimeSeriesPoint.id)
        )
        .filter(TimeSeriesPoint.tick >= from_tick, TimeSeriesPoint.tick <= int(max_tick))
        .group_by(TimeSeriesPoint.component_code)
        .all()
    )
    component_points = {c: int(cnt) for c, cnt in component_points.items()}

    # for each signal, count points where payload contains column
    # We do a SQL per signal (924 signals -> still ok for a button click, but could be heavy).
    # To keep it efficient, we compute coverage and then return only worst 'limit'.
    worst_list: List[Dict[str, Any]] = []

    signals = db.query(Signal).all()
    for s in signals:
        total = component_points.get(s.component_code, 0)
        if total == 0:
            continue

        sql = """
            SELECT COUNT(*) AS present_count
            FROM timeseries_points
            WHERE component_code = :component
              AND tick >= :from_tick
              AND tick <= :to_tick
              AND payload ? :column
        """
        present_count = db.execute(
            text(sql),
            {
                "component": s.component_code,
                "from_tick": from_tick,
                "to_tick": int(max_tick),
                "column": s.column_name,
            }
        ).scalar() or 0

        ratio = float(present_count / total) if total else 0.0

        worst_list.append({
            "signal_code": s.signal_code,
            "component_code": s.component_code,
            "column_name": s.column_name,
            "window_ticks": int(window_ticks),
            "total_component_points_in_window": int(total),
            "points_with_metric_present": int(present_count),
            "coverage_ratio": float(ratio),
        })

    worst_list.sort(key=lambda x: x["coverage_ratio"])
    return {"window_ticks": int(window_ticks), "worst": worst_list[:limit]}


def active_hotspots(db: Session, limit: int = 15):

    rows = (
        db.query(
            AlertEvent.signal_code,
            AlertEvent.component_code,
            func.count(AlertEvent.id).label("open_events"),

            func.sum(
                case(
                    (AlertEvent.severity == "critical", 1),
                    else_=0
                )
            ).label("critical_open"),

            func.sum(
                case(
                    (AlertEvent.severity == "warning", 1),
                    else_=0
                )
            ).label("warning_open"),

            func.max(AlertEvent.tick_end).label("last_tick"),
            func.max(AlertEvent.tick_end - AlertEvent.tick_start).label("max_duration"),
        )
        .filter(AlertEvent.status == "OPEN")
        .group_by(AlertEvent.signal_code, AlertEvent.component_code)
        .order_by(text("open_events DESC"))
        .limit(limit)
        .all()
    )

    return {
        "hotspots": [
            {
                "signal_code": r.signal_code,
                "component_code": r.component_code,
                "open_events": int(r.open_events or 0),
                "critical_open": int(r.critical_open or 0),
                "warning_open": int(r.warning_open or 0),
                "last_tick_seen": int(r.last_tick or 0),
                "max_duration_ticks": int(r.max_duration or 0),
            }
            for r in rows
        ]
    }

def component_time_analysis(
    db: Session,
    component_code: str,
    max_ticks: int = 500,
) -> Dict[str, Any]:
    """
    Adaptive time-interval analysis for a component.
    Automatically segments time based on behavior changes.
    """

    # 1️⃣ Collect ticks
    ticks = (
        db.query(TimeSeriesPoint.tick)
        .filter(TimeSeriesPoint.component_code == component_code)
        .order_by(TimeSeriesPoint.tick)
        .limit(max_ticks)
        .all()
    )
    ticks = [t[0] for t in ticks]

    if not ticks:
        return {"component_code": component_code, "intervals": []}

    # 2️⃣ Build per-tick stress score
    stress_by_tick = {}

    for t in ticks:
        # open alerts
        open_alerts = (
            db.query(func.count(AlertEvent.id))
            .filter(
                AlertEvent.component_code == component_code,
                AlertEvent.status == "OPEN",
                AlertEvent.tick_start <= t,
                AlertEvent.tick_end >= t,
            )
            .scalar()
            or 0
        )

        critical_alerts = (
            db.query(func.count(AlertEvent.id))
            .filter(
                AlertEvent.component_code == component_code,
                AlertEvent.status == "OPEN",
                AlertEvent.severity == "critical",
                AlertEvent.tick_start <= t,
                AlertEvent.tick_end >= t,
            )
            .scalar()
            or 0
        )

        # component health
        health = component_health(db, component_code)

        # stress score (simple but meaningful)
        stress = (
            critical_alerts * 10.0
            + open_alerts * 2.0
            + (100.0 - health) * 0.3
        )

        stress_by_tick[t] = {
            "stress": stress,
            "open_alerts": open_alerts,
            "critical_alerts": critical_alerts,
            "health": health,
        }

    # 3️⃣ Adaptive interval splitting
    intervals = []
    current = {
        "start_tick": ticks[0],
        "end_tick": ticks[0],
        "samples": [],
    }

    last_stress = stress_by_tick[ticks[0]]["stress"]

    for t in ticks:
        s = stress_by_tick[t]["stress"]

        # split condition
        if abs(s - last_stress) > 15:
            intervals.append(current)
            current = {
                "start_tick": t,
                "end_tick": t,
                "samples": [],
            }

        current["end_tick"] = t
        current["samples"].append(stress_by_tick[t])
        last_stress = s

    intervals.append(current)

    # 4️⃣ Score & classify intervals
    analyzed = []

    for i in intervals:
        samples = i["samples"]
        avg_stress = sum(x["stress"] for x in samples) / len(samples)
        max_critical = max(x["critical_alerts"] for x in samples)
        avg_health = sum(x["health"] for x in samples) / len(samples)

        if max_critical > 0 or avg_stress > 60:
            status = "BAD"
        elif avg_stress > 25:
            status = "DEGRADED"
        else:
            status = "GOOD"

        analyzed.append({
            "start_tick": i["start_tick"],
            "end_tick": i["end_tick"],
            "duration_ticks": i["end_tick"] - i["start_tick"] + 1,
            "avg_health": round(avg_health, 2),
            "avg_stress": round(avg_stress, 2),
            "max_critical_alerts": max_critical,
            "status": status,
        })

    return {
        "component_code": component_code,
        "intervals": analyzed,
    }






# -------------------------------------------------
# Helpers
# -------------------------------------------------

def _extract_series(db, component_code, column_name, limit=1440):
    rows = (
        db.query(
            TimeSeriesPoint.tick,
            TimeSeriesPoint.payload[column_name].astext.cast(Float),
        )
        .filter(TimeSeriesPoint.component_code == component_code)
        .order_by(TimeSeriesPoint.tick.desc())
        .limit(limit)
        .all()
    )
    rows = [(int(t), float(v)) for t, v in reversed(rows) if v is not None]
    return rows


def _linear_forecast(xs: List[int], ys: List[float]):
    """
    Simple least-squares linear regression.
    Returns slope and intercept.
    """
    n = len(xs)
    if n < 2:
        return 0.0, ys[-1] if ys else 0.0

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    den = sum((x - x_mean) ** 2 for x in xs)

    slope = num / den if den != 0 else 0.0
    intercept = y_mean - slope * x_mean
    return slope, intercept


# -------------------------------------------------
# SIGNAL FORECAST
# -------------------------------------------------

def forecast_signal(
    db: Session,
    signal_code: str,
    horizon_ticks: int = 30,
    history_ticks: int = 1440,
) -> Dict[str, Any]:
    """
    Forecast next N ticks for a signal.
    """

    signal = (
        db.query(Signal)
        .filter(Signal.signal_code == signal_code)
        .one_or_none()
    )
    if not signal:
        raise ValueError("Signal not found")

    series = _extract_series(
        db,
        signal.component_code,
        signal.column_name,
        history_ticks,
    )

    if len(series) < 10:
        return {
            "signal_code": signal_code,
            "status": "INSUFFICIENT_DATA",
        }

    ticks = [t for t, _ in series]
    values = [v for _, v in series]

    slope, intercept = _linear_forecast(ticks, values)
    volatility = statistics.stdev(values) if len(values) >= 2 else 0.0

    last_tick = ticks[-1]
    last_value = values[-1]

    predictions = []
    for i in range(1, horizon_ticks + 1):
        future_tick = last_tick + i
        mean = slope * future_tick + intercept
        predictions.append({
            "tick": future_tick,
            "expected": mean,
            "min": mean - 2 * volatility,
            "max": mean + 2 * volatility,
        })

    # rule-aware risk estimation
    rule = (
        db.query(AlertRule)
        .filter(AlertRule.signal_code == signal_code)
        .filter(AlertRule.enabled == True)
        .first()
    )

    risk_ahead = None
    breach_tick = None

    if rule:
        for p in predictions:
            v = p["expected"]
            if rule.operator == "gt" and v > rule.threshold:
                risk_ahead = "LIKELY"
                breach_tick = p["tick"]
                break
            if rule.operator == "lt" and v < rule.threshold:
                risk_ahead = "LIKELY"
                breach_tick = p["tick"]
                break

        if risk_ahead is None:
            risk_ahead = "UNLIKELY"

    return {
        "signal_code": signal_code,
        "component_code": signal.component_code,
        "signal_type": signal.signal_type,
        "polarity": signal.polarity,
        "history_ticks_used": len(series),
        "horizon_ticks": horizon_ticks,
        "last_tick": last_tick,
        "last_value": last_value,
        "trend": {
            "slope_per_tick": slope,
            "direction": "UP" if slope > 0 else "DOWN" if slope < 0 else "FLAT",
        },
        "volatility": volatility,
        "forecast": predictions,
        "risk_ahead": {
            "status": risk_ahead,
            "breach_tick": breach_tick,
            "rule_threshold": rule.threshold if rule else None,
        },
    }


# -------------------------------------------------
# COMPONENT FORECAST
# -------------------------------------------------

def forecast_component(
    db: Session,
    component_code: str,
    horizon_ticks: int = 30,
) -> Dict[str, Any]:
    """
    Forecast component health & risks.
    """

    signals = (
        db.query(Signal)
        .filter(Signal.component_code == component_code)
        .all()
    )

    forecasts = []
    risky_signals = []

    for s in signals:
        try:
            f = forecast_signal(
                db,
                s.signal_code,
                horizon_ticks=horizon_ticks,
            )
        except Exception:
            continue

        if f.get("risk_ahead", {}).get("status") == "LIKELY":
            risky_signals.append({
                "signal_code": s.signal_code,
                "breach_tick": f["risk_ahead"]["breach_tick"],
            })

        forecasts.append(f)

    status = "STABLE"
    if len(risky_signals) > 0:
        status = "DEGRADED"
    if len(risky_signals) > 3:
        status = "CRITICAL"

    return {
        "component_code": component_code,
        "horizon_ticks": horizon_ticks,
        "predicted_status": status,
        "risky_signals_count": len(risky_signals),
        "risky_signals": risky_signals,
    }





def component_regimes(
    db: Session,
    component_code: str,
    window: int = 1440,
    bucket_size: int = 60,
):
    """
    Splits time into buckets and classifies each bucket into a regime.
    """

    max_tick = (
        db.query(func.max(TimeSeriesPoint.tick))
        .filter(TimeSeriesPoint.component_code == component_code)
        .scalar()
    )

    if max_tick is None:
        return {"component_code": component_code, "regimes": []}

    start_tick = max(0, max_tick - window)
    regimes = []

    for bucket_start in range(start_tick, max_tick, bucket_size):
        bucket_end = bucket_start + bucket_size - 1

        # ---- alerts in bucket
        alert_count = (
            db.query(func.count(AlertEvent.id))
            .filter(
                AlertEvent.component_code == component_code,
                AlertEvent.tick_start <= bucket_end,
                AlertEvent.tick_end >= bucket_start,
            )
            .scalar()
            or 0
        )

        # ---- collect numeric values
        values = []
        rows = (
            db.query(TimeSeriesPoint.payload)
            .filter(
                TimeSeriesPoint.component_code == component_code,
                TimeSeriesPoint.tick >= bucket_start,
                TimeSeriesPoint.tick <= bucket_end,
            )
            .limit(500)
            .all()
        )

        for (payload,) in rows:
            if isinstance(payload, dict):
                for v in payload.values():
                    if isinstance(v, (int, float)):
                        values.append(float(v))

        volatility = statistics.stdev(values) if len(values) >= 2 else 0.0

        # ---- regime classification
        if alert_count == 0 and volatility < 2:
            regime = "STABLE"
        elif alert_count < 5 and volatility < 5:
            regime = "DEGRADED"
        elif alert_count >= 5 or volatility >= 5:
            regime = "UNSTABLE"
        else:
            regime = "UNKNOWN"

        regimes.append({
            "from_tick": bucket_start,
            "to_tick": bucket_end,
            "regime": regime,
            "alert_count": int(alert_count),
            "avg_volatility": round(float(volatility), 3),
        })

    return {
        "component_code": component_code,
        "window_ticks": window,
        "bucket_size": bucket_size,
        "regimes": regimes,
    }


def signal_influence(
    db: Session,
    signal_code: str,
    window: int = 500,
    lag_window: int = 20,
):
    """
    Finds signals that tend to lead or follow a given signal.
    """

    base_events = (
        db.query(AlertEvent)
        .filter(AlertEvent.signal_code == signal_code)
        .order_by(AlertEvent.tick_start)
        .all()
    )

    if not base_events:
        return {"signal_code": signal_code, "leads": [], "follows": []}

    lead_counts = defaultdict(list)
    follow_counts = defaultdict(list)

    for e in base_events:
        t0 = e.tick_start

        neighbors = (
            db.query(AlertEvent)
            .filter(
                AlertEvent.tick_start >= t0 - lag_window,
                AlertEvent.tick_start <= t0 + lag_window,
                AlertEvent.signal_code != signal_code,
            )
            .all()
        )

        for n in neighbors:
            delta = n.tick_start - t0
            if delta < 0:
                lead_counts[n.signal_code].append(abs(delta))
            elif delta > 0:
                follow_counts[n.signal_code].append(delta)

    def summarize(d):
        out = []
        for k, vals in d.items():
            if len(vals) >= 3:
                out.append({
                    "signal_code": k,
                    "avg_ticks": round(sum(vals) / len(vals), 2),
                    "occurrences": len(vals),
                })
        return sorted(out, key=lambda x: x["occurrences"], reverse=True)

    return {
        "signal_code": signal_code,
        "analysis_window": window,
        "leads": summarize(lead_counts),
        "follows": summarize(follow_counts),
    }


def signal_envelope(
    db: Session,
    signal_code: str,
    window: int = 300,
    bucket: int = 10,
):
    signal = (
        db.query(Signal)
        .filter(Signal.signal_code == signal_code)
        .one_or_none()
    )
    if not signal:
        return {"error": f"Signal '{signal_code}' not found"}

    max_tick = db.query(func.max(TimeSeriesPoint.tick)).scalar()
    if max_tick is None:
        return {"error": "No timeseries data"}

    start_tick = max_tick - window

    rows = (
        db.query(
            TimeSeriesPoint.tick,
            TimeSeriesPoint.payload[signal.column_name].astext.cast(Float),
        )
        .filter(
            TimeSeriesPoint.component_code == signal.component_code,
            TimeSeriesPoint.tick >= start_tick,
        )
        .order_by(TimeSeriesPoint.tick)
        .all()
    )

    series = []

    for i in range(0, len(rows), bucket):
        chunk = rows[i : i + bucket]
        values = [v for _, v in chunk if v is not None]

        if len(values) < 3:
            continue

        values_sorted = sorted(values)

        series.append({
            "from_tick": chunk[0][0],
            "to_tick": chunk[-1][0],
            "p10": statistics.quantiles(values_sorted, n=10)[0],
            "p50": statistics.median(values_sorted),
            "p90": statistics.quantiles(values_sorted, n=10)[8],
            "mean": statistics.mean(values_sorted),
            "out_of_band": (
                statistics.mean(values_sorted) < statistics.quantiles(values_sorted, n=10)[0]
                or statistics.mean(values_sorted) > statistics.quantiles(values_sorted, n=10)[8]
            ),
        })

    return {
        "signal_code": signal_code,
        "component_code": signal.component_code,
        "window": window,
        "bucket": bucket,
        "series": series,
    }


def component_stress_curve(db: Session, component_code: str, window: int = 600, bucket: int = 20):
    max_tick = db.query(func.max(TimeSeriesPoint.tick)).scalar()
    start = max_tick - window
    series = []

    for t in range(start, max_tick, bucket):
        alerts = (
            db.query(AlertEvent.severity, func.count(AlertEvent.id))
            .filter(
                AlertEvent.component_code == component_code,
                AlertEvent.tick_start <= t + bucket,
                AlertEvent.tick_end >= t
            )
            .group_by(AlertEvent.severity)
            .all()
        )

        counts = {s: c for s, c in alerts}
        stress = (
            counts.get("critical", 0) * 30 +
            counts.get("warning", 0) * 10
        )
        stress = min(100, stress)

        series.append({
            "from_tick": t,
            "to_tick": t + bucket - 1,
            "stress_score": stress,
            "alerts": counts
        })

    return {
        "component_code": component_code,
        "window": window,
        "bucket": bucket,
        "series": series
    }

{
  "signal_code": "C2.consumer_lag",
  "pivot_tick": 1000,
  "before": {
    "mean": 240,
    "p95": 380
  },
  "after": {
    "mean": 160,
    "p95": 210
  },
  "delta": {
    "mean_change": -80,
    "p95_change": -170,
    "improvement": True
  }
}

def signal_change_impact(
    db: Session,
    signal_code: str,
    pivot_tick: int,
    window: int = 200,
):
    signal = (
        db.query(Signal)
        .filter(Signal.signal_code == signal_code)
        .one_or_none()
    )
    if not signal:
        return {"error": f"Signal '{signal_code}' not found"}

    rows = (
        db.query(
            TimeSeriesPoint.tick,
            TimeSeriesPoint.payload[signal.column_name].astext.cast(Float),
        )
        .filter(TimeSeriesPoint.component_code == signal.component_code)
        .all()
    )

    before = [v for t, v in rows if v is not None and pivot_tick - window <= t < pivot_tick]
    after = [v for t, v in rows if v is not None and pivot_tick <= t <= pivot_tick + window]

    if len(before) < 3 or len(after) < 3:
        return {"error": "Not enough data around pivot"}

    before_sorted = sorted(before)
    after_sorted = sorted(after)

    return {
        "signal_code": signal_code,
        "pivot_tick": pivot_tick,
        "before": {
            "mean": statistics.mean(before_sorted),
            "p95": statistics.quantiles(before_sorted, n=20)[18],
        },
        "after": {
            "mean": statistics.mean(after_sorted),
            "p95": statistics.quantiles(after_sorted, n=20)[18],
        },
        "delta": {
            "mean_change": statistics.mean(after_sorted) - statistics.mean(before_sorted),
            "p95_change": (
                statistics.quantiles(after_sorted, n=20)[18]
                - statistics.quantiles(before_sorted, n=20)[18]
            ),
            "improvement": statistics.mean(after_sorted) < statistics.mean(before_sorted),
        },
    }
