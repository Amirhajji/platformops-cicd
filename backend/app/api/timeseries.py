# app/api/timeseries.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.timeseries_service import get_timeseries
from app.services import timeseries_service

router = APIRouter(prefix="/api/timeseries", tags=["timeseries"])


@router.get("")
def read_timeseries(
    signal_code: str,
    from_tick: int | None = None,
    to_tick: int | None = None,
    db: Session = Depends(get_db),
):
    try:
        return get_timeseries(
            db=db,
            signal_code=signal_code,
            from_tick=from_tick,
            to_tick=to_tick,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/multi")
def multi_timeseries(
    signals: str = Query(...),
    db: Session = Depends(get_db)
):
    return {
        "signals": timeseries_service.multi_signal(
            db, signals.split(",")
        )
    }
#

@router.get("/aggregate")
def aggregate(
    signal_code: str,
    window: int = 10,
    agg: str = "avg",
    db: Session = Depends(get_db)
):
    return timeseries_service.aggregate_signal(
        db, signal_code, window, agg #
    )



@router.get("/derivative")
def derivative(
    signal_code: str,
    db: Session = Depends(get_db)
):
    return timeseries_service.derivative_signal(db, signal_code)


@router.get("/normalized")
def normalized(
    signal_code: str,
    db: Session = Depends(get_db)
):
    return timeseries_service.normalize_signal(db, signal_code)
