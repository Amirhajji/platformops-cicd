# app/services/anomaly_impact_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Dict, Any

from app.db.models.alerts import AlertEvent
from app.db.models.anomalies import InjectedAnomaly
from app.services.analytics_service import component_health, global_health


def anomaly_impact_summary(db: Session) -> Dict[str, Any]:
    """
    Deep impact analysis of the currently active anomaly.
    Read-only, rollback-safe.
    """

    # -------------------------------------------------
    # 0. Is there an active anomaly?
    # -------------------------------------------------
    anomaly_rows = db.query(InjectedAnomaly).all()
    if not anomaly_rows:
        return {
            "active": False,
            "global_health": global_health(db),
        }

    # -------------------------------------------------
    # 1. Anomaly context
    # -------------------------------------------------
    anomaly_type = anomaly_rows[0].anomaly_type
    from_tick = min(a.tick for a in anomaly_rows)
    to_tick = max(a.tick for a in anomaly_rows)

    affected_components = sorted({a.component_code for a in anomaly_rows})
    affected_signals = sorted({a.signal_code for a in anomaly_rows})

    anomaly_context = {
        "type": anomaly_type,
        "from_tick": from_tick,
        "to_tick": to_tick,
        "duration_ticks": to_tick - from_tick + 1,
        "affected_components": affected_components,
        "affected_signals": len(affected_signals),
        "points_modified": len(anomaly_rows),
    }

    # -------------------------------------------------
    # 2. Alert impact (SIMULATED only)
    # -------------------------------------------------
    alert_rows = (
        db.query(
            AlertEvent.component_code,
            AlertEvent.severity,
            func.count(AlertEvent.id),
        )
        .filter(
            AlertEvent.status == "OPEN",
            AlertEvent.origin == "SIMULATED",
        )
        .group_by(AlertEvent.component_code, AlertEvent.severity)
        .all()
    )

    alerts_by_severity: Dict[str, int] = {}
    alerts_by_component: Dict[str, int] = {}
    component_severity: Dict[str, Dict[str, int]] = {}

    for component, severity, cnt in alert_rows:
        alerts_by_severity[severity] = alerts_by_severity.get(severity, 0) + cnt
        alerts_by_component[component] = alerts_by_component.get(component, 0) + cnt
        component_severity.setdefault(component, {})[severity] = cnt

    alert_impact = {
        "total": sum(alerts_by_severity.values()),
        "by_severity": alerts_by_severity,
        "by_component": alerts_by_component,
    }

    # -------------------------------------------------
    # 3. Component degradation
    # -------------------------------------------------
    component_impacts = []

    for component in affected_components:
        try:
            health = component_health(db, component)
        except Exception:
            continue

        component_impacts.append({
            "component_code": component,
            "health_score": float(health),
            "open_alerts": alerts_by_component.get(component, 0),
            "severity_pressure": component_severity.get(component, {}),
        })

    component_impacts.sort(key=lambda x: x["health_score"])

    # -------------------------------------------------
    # 4. Metric deviation analysis
    # -------------------------------------------------
    deviation_rows = db.execute(
        text("""
            SELECT
                ia.signal_code,
                AVG(
                    ABS(
                        ((ts.payload ->> split_part(ia.signal_code, '.', 2))::double precision
                         - (ia.original_value)::double precision)
                        / NULLIF((ia.original_value)::double precision, 0)
                    ) * 100
                ) AS avg_delta_pct,
                MAX(
                    ABS(
                        ((ts.payload ->> split_part(ia.signal_code, '.', 2))::double precision
                         - (ia.original_value)::double precision)
                        / NULLIF((ia.original_value)::double precision, 0)
                    ) * 100
                ) AS max_delta_pct
            FROM injected_anomalies ia
            JOIN timeseries_points ts
              ON ts.component_code = ia.component_code
             AND ts.tick = ia.tick
            GROUP BY ia.signal_code
        """)
    ).fetchall()

    metric_deviation = [
        {
            "signal_code": r.signal_code,
            "avg_delta_pct": float(r.avg_delta_pct or 0.0),
            "max_delta_pct": float(r.max_delta_pct or 0.0),
        }
        for r in deviation_rows
    ]

    metric_deviation.sort(key=lambda x: x["max_delta_pct"], reverse=True)

    # -------------------------------------------------
    # 5. Final response
    # -------------------------------------------------
    return {
        "active": True,
        "anomaly": anomaly_context,
        "alerts": alert_impact,
        "components": component_impacts,
        "metric_deviation": metric_deviation,
        "global_health": global_health(db),
    }
