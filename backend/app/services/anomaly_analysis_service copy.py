from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Dict, Any, List

from app.db.models.anomalies import InjectedAnomaly
from app.db.models.alerts import AlertEvent
from app.services.analytics_service import component_health


PIPELINE_ORDER = {
    "C2": 0,  # Kafka
    "C3": 1,  # Stream proc
    "C6": 2,  # Storage / processing
    "C8": 3,  # API
    "C1": 0,  # Batch ingest
}


def analyze_anomaly(db: Session) -> Dict[str, Any]:
    """
    Deep behavioral analysis of the currently injected anomaly.
    """

    anomalies = db.query(InjectedAnomaly).all()
    if not anomalies:
        return {"active": False}

    anomaly_type = anomalies[0].anomaly_type
    from_tick = min(a.tick for a in anomalies)
    to_tick = max(a.tick for a in anomalies)

    components = sorted(
        {a.component_code for a in anomalies},
        key=lambda c: PIPELINE_ORDER.get(c, 99),
    )

    signals = sorted({a.signal_code for a in anomalies})

    # --------------------------------------------------
    # 1. Narrative
    # --------------------------------------------------
    narrative = {
        "cpu_saturation": "CPU saturation caused sustained utilization pressure.",
        "error_spike": "Error rates increased sharply, indicating failure conditions.",
        "latency_regression": "Request latency increased beyond normal operating bounds.",
        "event_storm": "Excessive internal events stressed system stability.",
        "backlog_growth": "Queue backlog grew upstream and propagated downstream.",
    }.get(anomaly_type, "Anomalous behavior detected across the system.")

    # --------------------------------------------------
    # 2. Alert timeline
    # --------------------------------------------------
    alert_timeline = db.query(
        func.min(AlertEvent.tick_start),
        func.max(AlertEvent.tick_end),
        func.count(AlertEvent.id),
    ).filter(
        AlertEvent.origin == "SIMULATED",
        AlertEvent.status == "OPEN",
    ).one()

    # --------------------------------------------------
    # 3. Component stress analysis
    # --------------------------------------------------
    component_analysis = []

    for c in components:
        alerts = (
            db.query(AlertEvent.severity, func.count(AlertEvent.id))
            .filter(
                AlertEvent.component_code == c,
                AlertEvent.origin == "SIMULATED",
                AlertEvent.status == "OPEN",
            )
            .group_by(AlertEvent.severity)
            .all()
        )

        severity_map = {s: int(cnt) for s, cnt in alerts}

        try:
            health = float(component_health(db, c))
        except Exception:
            health = None

        component_analysis.append({
            "component_code": c,
            "pipeline_position": PIPELINE_ORDER.get(c, 99),
            "health_score": health,
            "alerts": severity_map,
            "total_alerts": sum(severity_map.values()),
        })

    # --------------------------------------------------
    # 4. Signal sensitivity (who reacted first & strongest)
    # --------------------------------------------------
    sensitivity_rows = db.execute(
        text("""
            SELECT
                signal_code,
                MIN(tick) AS first_impact,
                COUNT(*) AS modified_points
            FROM injected_anomalies
            GROUP BY signal_code
            ORDER BY first_impact ASC
        """)
    ).fetchall()

    signal_sensitivity = [
        {
            "signal_code": r.signal_code,
            "first_impact_tick": int(r.first_impact),
            "points_modified": int(r.modified_points),
        }
        for r in sensitivity_rows
    ]

    # --------------------------------------------------
    # 5. Degradation pattern classification
    # --------------------------------------------------
    pattern = "localized"

    if len(components) > 2:
        upstream = PIPELINE_ORDER.get(components[0], 0)
        downstream = PIPELINE_ORDER.get(components[-1], 0)
        if downstream > upstream:
            pattern = "cascading"

    if any(c["total_alerts"] > 10 for c in component_analysis):
        pattern = "amplified_downstream"

    # --------------------------------------------------
    # 6. Stability assessment
    # --------------------------------------------------
    stability = "stable"

    if alert_timeline[2] and alert_timeline[2] > 50:
        stability = "unstable"

    # --------------------------------------------------
    # 7. Observations (derived facts)
    # --------------------------------------------------
    observations: List[str] = []

    if signal_sensitivity:
        observations.append(
            f"{signal_sensitivity[0]['signal_code']} acted as an early indicator."
        )

    if pattern == "cascading":
        observations.append("Pressure propagated across multiple pipeline stages.")

    if stability == "unstable":
        observations.append("Alert pressure escalated rapidly.")

    # --------------------------------------------------
    # Final response
    # --------------------------------------------------
    return {
        "active": True,
        "anomaly_type": anomaly_type,
        "narrative": narrative,
        "window": {
            "from_tick": from_tick,
            "to_tick": to_tick,
            "duration_ticks": to_tick - from_tick + 1,
        },
        "components": component_analysis,
        "signal_sensitivity": signal_sensitivity,
        "degradation_pattern": pattern,
        "stability": stability,
        "observations": observations,
    }
