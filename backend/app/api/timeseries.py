from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.timeseries_service import (
    get_timeseries,
    compute_volatility,
    detect_degradation,
    component_health,
    global_health,
    multi_signal,
    aggregate_signal,
    derivative_signal,
    normalize_signal,
)

router = APIRouter(prefix="/api/timeseries", tags=["Timeseries"])


# ---------------------------------------------------------
# SINGLE SIGNAL
# ---------------------------------------------------------
@router.get("/{signal_code}")
def fetch_timeseries(
    signal_code: str,
    from_tick: Optional[int] = Query(None),
    to_tick: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return get_timeseries(db, signal_code, from_tick, to_tick)


# ---------------------------------------------------------
# MULTI SIGNAL
# ---------------------------------------------------------
@router.post("/multi")
def multi_fetch(
    signal_codes: List[str],
    db: Session = Depends(get_db),
):
    return multi_signal(db, signal_codes)


# ---------------------------------------------------------
# VOLATILITY
# ---------------------------------------------------------
@router.get("/volatility/{signal_code}")
def volatility(
    signal_code: str,
    window: int = 30,
    db: Session = Depends(get_db),
):
    return {
        "signal_code": signal_code,
        "window": window,
        "volatility": compute_volatility(db, signal_code, window),
    }


# ---------------------------------------------------------
# DEGRADATION
# ---------------------------------------------------------
@router.get("/degradation")
def degradation(
    role: str,
    window: int = 20,
    db: Session = Depends(get_db),
):
    return detect_degradation(db, role, window)


# ---------------------------------------------------------
# COMPONENT HEALTH
# ---------------------------------------------------------
@router.get("/component-health/{component_code}")
def component_health_endpoint(
    component_code: str,
    db: Session = Depends(get_db),
):
    return {
        "component_code": component_code,
        "health_score": component_health(db, component_code),
    }


# ---------------------------------------------------------
# GLOBAL HEALTH
# ---------------------------------------------------------
@router.get("/global-health")
def global_health_endpoint(db: Session = Depends(get_db)):
    return global_health(db)


# ---------------------------------------------------------
# AGGREGATIONS
# ---------------------------------------------------------
@router.get("/aggregate/{signal_code}")
def aggregate(
    signal_code: str,
    window: int = 10,
    agg_type: str = "avg",
    db: Session = Depends(get_db),
):
    return aggregate_signal(db, signal_code, window, agg_type)


# ---------------------------------------------------------
# DERIVATIVE
# ---------------------------------------------------------
@router.get("/derivative/{signal_code}")
def derivative(
    signal_code: str,
    db: Session = Depends(get_db),
):
    return derivative_signal(db, signal_code)


# ---------------------------------------------------------
# NORMALIZATION
# ---------------------------------------------------------
@router.get("/normalize/{signal_code}")
def normalize(
    signal_code: str,
    db: Session = Depends(get_db),
):
    return normalize_signal(db, signal_code)
