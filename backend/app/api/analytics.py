from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import ComponentHealth

from app.services.analytics_service import (
    compute_volatility,
    detect_degradation,
    component_health,
    global_health,

    # NEW
    system_stats,
    alerts_stats,
    component_rankings,
    signal_coverage,
    active_hotspots,
)

from app.services.analytics_service import component_time_analysis
from app.services.analytics_service import (
    forecast_signal,
    forecast_component,
)

from app.services.analytics_service import component_regimes
from app.services.analytics_service import signal_influence
from app.services.analytics_service import signal_envelope 
from app.services.analytics_service import component_stress_curve
from app.services.analytics_service import signal_change_impact


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# -------------------------
# Existing endpoints (kept)
# -------------------------
@router.get("/volatility")
def volatility(
    signal_code: str,
    window: int = 10,
    db: Session = Depends(get_db),
):
    return {
        "signal_code": signal_code,
        "window": window,
        "volatility": compute_volatility(db, signal_code, window),
    }


@router.get("/component-health/{component_code}", response_model=ComponentHealth)
def component_health_api(component_code: str, db: Session = Depends(get_db)):
    return {
        "component_code": component_code,
        "health_score": component_health(db, component_code),
    }


@router.get("/global-health")
def global_health_api(db: Session = Depends(get_db)):
    return global_health(db)


@router.get("/top-risk")
def top_risk(role: str, limit: int = 5, db: Session = Depends(get_db)):
    signals = detect_degradation(db, role)
    signals.sort(key=lambda x: abs(x["slope"]), reverse=True)
    return signals[:limit]


@router.get("/degradation")
def degradation(role: str, db: Session = Depends(get_db)):
    return detect_degradation(db, role)


# =========================================================
# NEW: rich global analytics endpoints
# =========================================================

@router.get("/system-stats")
def system_stats_api(db: Session = Depends(get_db)):
    return system_stats(db)


@router.get("/alerts-stats")
def alerts_stats_api(
    from_tick: Optional[int] = None,
    to_tick: Optional[int] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    return alerts_stats(db, from_tick=from_tick, to_tick=to_tick, limit=limit)


@router.get("/component-rankings")
def component_rankings_api(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    return component_rankings(db, limit=limit)


@router.get("/signal-coverage")
def signal_coverage_api(
    window_ticks: int = 200,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    return signal_coverage(db, window_ticks=window_ticks, limit=limit)


@router.get("/active-hotspots")
def active_hotspots_api(
    limit: int = 15,
    db: Session = Depends(get_db),
):
    return active_hotspots(db, limit=limit)


@router.get("/component-time-analysis/{component_code}")
def component_time_analysis_api(
    component_code: str,
    max_ticks: int = 500,
    db: Session = Depends(get_db),
):
    return component_time_analysis(db, component_code, max_ticks)


@router.get("/forecast/signal")
def forecast_signal_api(
    signal_code: str,
    horizon_ticks: int = 30,
    db: Session = Depends(get_db),
):
    return forecast_signal(
        db,
        signal_code=signal_code,
        horizon_ticks=horizon_ticks,
    )


@router.get("/forecast/component/{component_code}")
def forecast_component_api(
    component_code: str,
    horizon_ticks: int = 30,
    db: Session = Depends(get_db),
):
    return forecast_component(
        db,
        component_code=component_code,
        horizon_ticks=horizon_ticks,
    )


@router.get("/component-regimes/{component_code}")
def component_regimes_api(
    component_code: str,
    window: int = 1440,
    bucket_size: int = 60,
    db: Session = Depends(get_db),
):
    return component_regimes(
        db=db,
        component_code=component_code,
        window=window,
        bucket_size=bucket_size,
    )


@router.get("/signal-envelope")
def signal_envelope_api(
    signal_code: str,
    window: int = 300,
    bucket: int = 10,
    db: Session = Depends(get_db),
):
    return signal_envelope(db, signal_code, window, bucket)


@router.get("/component-stress/{component_code}")
def component_stress_api(
    component_code: str,
    window: int = 600,
    bucket: int = 20,
    db: Session = Depends(get_db),
):
    return component_stress_curve(db, component_code, window, bucket)


@router.get("/signal-change-impact")
def signal_change_impact_api(
    signal_code: str,
    pivot_tick: int,
    window: int = 200,
    db: Session = Depends(get_db),
):
    return signal_change_impact(db, signal_code, pivot_tick, window)
