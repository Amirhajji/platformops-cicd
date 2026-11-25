"""Run, overview, KQIs, components and KPIs."""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import ID_PATTERN, current_run, time_window
from app.core.db import get_session
from app.schemas.scores import (ComponentDetailOut, ComponentOut, KpiSeriesOut,
                                KqiSeriesOut, OverviewOut, RunOut)
from app.services import scores
from app.services.timeline import Run, Window

router = APIRouter(tags=["scores"])


@router.get("/run", response_model=RunOut)
def get_run(run: Run = Depends(current_run)) -> Any:
    return {"spec_version": run.spec_version, "seed": run.seed, "start_utc": run.ts(0),
            "end_utc": run.ts(run.ticks - 1), "tick_seconds": run.tick_seconds,
            "ticks": run.ticks}


@router.get("/overview", response_model=OverviewOut)
def get_overview(window: Window = Depends(time_window),
                 session: Session = Depends(get_session)) -> Any:
    return scores.overview(session, window)


@router.get("/kqi/series", response_model=KqiSeriesOut)
def get_kqi_series(scope: str = Query(..., pattern=ID_PATTERN),
                   window: Window = Depends(time_window),
                   session: Session = Depends(get_session)) -> Any:
    return scores.kqi_series(session, scope, window)


@router.get("/components", response_model=List[ComponentOut])
def get_components(session: Session = Depends(get_session)) -> Any:
    return scores.list_components(session)


@router.get("/components/{component_id}", response_model=ComponentDetailOut)
def get_component(component_id: str = Path(..., pattern=ID_PATTERN),
                  at: Optional[str] = Query(None), run: Run = Depends(current_run),
                  session: Session = Depends(get_session)) -> Any:
    tick = run.tick("at", at, run.ticks - 1)
    return scores.component_detail(session, component_id, run, tick)


@router.get("/kpis/{kpi_id}/series", response_model=KpiSeriesOut)
def get_kpi_series(kpi_id: str = Path(..., pattern=ID_PATTERN),
                   window: Window = Depends(time_window),
                   session: Session = Depends(get_session)) -> Any:
    return scores.kpi_series(session, kpi_id, window)
