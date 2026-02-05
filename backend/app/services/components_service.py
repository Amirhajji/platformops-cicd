from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models.signals import Signal
from app.db.models.alerts import AlertRule
from app.db.models.timeseries import TimeSeriesPoint
from app.db.models.anomalies import InjectedAnomaly
from app.services.analytics_service import component_health, forecast_signal
from app.services.propagation_service import compute_propagation
from app.services.analytics_service import signal_change_impact  # Reuse for deltas
import statistics

def get_related_signals(db: Session, component_code: str, limit: int, min_correlation: float):
    # Get primary signals for component
    primary_signals = [s.signal_code for s in db.query(Signal).filter(Signal.component_code == component_code).all()]
    
    if not primary_signals:
        return {"error": "No signals for component"}
    
    related = []
    for primary in primary_signals:
        # Compute propagation for each primary (aggregate unique)
        for other_signal in db.query(Signal.signal_code).filter(Signal.signal_code != primary).limit(20).all():  # Limit scan
            prop = compute_propagation(db, primary, other_signal[0])
            if prop["correlation"] >= min_correlation:
                related.append({
                    "signal_code": other_signal[0],
                    "component_code": db.query(Signal.component_code).filter(Signal.signal_code == other_signal[0]).scalar(),
                    "lag_ticks": prop["lag_ticks"],
                    "correlation": prop["correlation"],
                    "confidence": prop["confidence_score"],
                    "direction": "upstream" if prop["lag_ticks"] > 0 else "downstream"
                })
    
    # Sort and limit unique
    unique_related = {r["signal_code"]: r for r in related}
    sorted_related = sorted(unique_related.values(), key=lambda x: x["correlation"], reverse=True)[:limit]
    
    return {
        "component_code": component_code,
        "primary_signals": primary_signals,
        "related": sorted_related
    }

def get_health_breakdown(db: Session, component_code: str):
    signals = db.query(Signal).filter(Signal.component_code == component_code).all()
    if not signals:
        return {"error": "No signals for component"}
    
    overall = component_health(db, component_code)
    
    by_family = {}
    for s in signals:
        fam = s.family or 'unknown'
        if fam not in by_family:
            by_family[fam] = {"scores": [], "worst_signals": []}
        # Assume signal health from volatility or baseline; here mock with rule thresholds
        signal_health = 100 - (s.current_value - s.threshold) / s.threshold * 100 if s.threshold else 100  # Placeholder
        by_family[fam]["scores"].append(signal_health)
        if signal_health < 70:
            by_family[fam]["worst_signals"].append(s.signal_code)
    
    for fam, data in by_family.items():
        data["score"] = statistics.mean(data["scores"]) if data["scores"] else 0
        del data["scores"]
    
    critical_families = [fam for fam, data in by_family.items() if data["score"] < 50]
    
    return {
        "component_code": component_code,
        "overall_health": overall,
        "by_family": by_family,
        "critical_families": critical_families
    }

def get_family_snapshot(db: Session, component_code: str, family: str, window: int):
    signals = db.query(Signal).filter(Signal.component_code == component_code, Signal.family == family).all()
    if not signals:
        return {"error": "No signals in family"}
    
    # Aggregate values across signals in family (last window ticks)
    max_tick = db.query(func.max(TimeSeriesPoint.tick)).scalar()
    start_tick = max_tick - window
    
    values = []
    mini_series = []
    for s in signals:
        rows = db.query(
            TimeSeriesPoint.tick,
            TimeSeriesPoint.payload[s.column_name].astext.cast(float).label('value')
        ).filter(
            TimeSeriesPoint.component_code == component_code,
            TimeSeriesPoint.tick.between(start_tick, max_tick)
        ).order_by(TimeSeriesPoint.tick).all()
        
        sig_values = [r.value for r in rows if r.value is not None]
        values.extend(sig_values)
        
        # Downsample to ~10 points for mini
        if len(rows) > 10:
            step = len(rows) // 10
            mini = [{'tick': rows[i].tick, 'avg': statistics.mean([r.value for r in rows[i:i+step] if r.value is not None])} for i in range(0, len(rows), step)]
        else:
            mini = [{'tick': r.tick, 'avg': r.value} for r in rows if r.value is not None]
        mini_series.append({s.signal_code: mini})
    
    if not values:
        return {"error": "No data in window"}
    
    avg = statistics.mean(values)
    p95 = statistics.quantiles(values, n=20)[18]
    trend = 'up' if avg > statistics.mean(values[:len(values)//2]) else 'down' if avg < statistics.mean(values[:len(values)//2]) else 'flat'
    
    return {
        "family": family,
        "signal_count": len(signals),
        "avg_value": avg,
        "p95_value": p95,
        "trend": trend,
        "health_contribution": 100 - (p95 / avg * 10) if avg else 0,  # Placeholder
        "mini_series": mini_series,
        "threshold_breaches_last_hour": db.query(AlertEvent).filter(AlertEvent.component_code == component_code, AlertEvent.family == family, AlertEvent.tick_start > max_tick - 60).count()
    }

def get_anomaly_contribution(db: Session, component_code: str):
    active_anomaly = db.query(InjectedAnomaly).filter(InjectedAnomaly.rollback_tick.is_(None)).first()
    if not active_anomaly:
        return {"error": "No active anomaly"}
    
    pivot_tick = active_anomaly.from_tick  # Use anomaly start as pivot
    
    signals = db.query(Signal).filter(Signal.component_code == component_code).all()
    affected = []
    total_impact = 0
    
    for s in signals:
        impact = signal_change_impact(db, s.signal_code, pivot_tick)
        if "delta" in impact and impact["delta"]["mean_change"] != 0:
            delta_percent = (impact["delta"]["mean_change"] / impact["before"]["mean"]) * 100 if impact["before"]["mean"] else 0
            affected.append({
                "signal_code": s.signal_code,
                "delta_percent": delta_percent,
                "before_p95": impact["before"]["p95"],
                "after_p95": impact["after"]["p95"]
            })
            total_impact += abs(delta_percent)
    
    affected.sort(key=lambda x: abs(x["delta_percent"]), reverse=True)
    
    return {
        "component_code": component_code,
        "affected_signals": affected,
        "total_impact_score": total_impact / len(signals) if signals else 0
    }

def get_forecast_summary(db: Session, component_code: str, horizon_ticks: int):
    signals = db.query(Signal).filter(Signal.component_code == component_code, Signal.signal_type.in_(["yi", "zi"])).all()  # Focus on KPIs/KQIs
    if not signals:
        return {"error": "No health signals"}
    
    predicted_health = 0
    risky = []
    
    for s in signals:
        forecast = forecast_signal(db, s.signal_code, horizon_ticks)
        predicted_value = forecast["predicted_mean"]  # Assume forecast returns predicted_mean
        threshold = db.query(AlertRule.threshold).filter(AlertRule.signal_code == s.signal_code).scalar() or float('inf')
        breach_in_ticks = next((i for i, v in enumerate(forecast["series"]) if v["value"] > threshold), horizon_ticks) if s.polarity == "higher_is_worse" else horizon_ticks
        
        if breach_in_ticks < horizon_ticks:
            risky.append({
                "signal_code": s.signal_code,
                "breach_in_ticks": breach_in_ticks,
                "predicted_value": predicted_value
            })
        
        predicted_health += predicted_value / len(signals)
    
    risk_level = "HIGH" if len(risky) > len(signals) * 0.3 else "MEDIUM" if len(risky) > 0 else "LOW"
    
    return {
        "component_code": component_code,
        "horizon_ticks": horizon_ticks,
        "predicted_health": predicted_health,
        "risk_level": risk_level,
        "risky_signals": sorted(risky, key=lambda x: x["breach_in_ticks"])
    }