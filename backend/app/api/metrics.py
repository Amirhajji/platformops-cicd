from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import component_filter, time_window
from app.core.db import get_session
from app.schemas.auth import NO_NUL
from app.schemas.metrics import MetricOut, MetricSeriesOut
from app.services import metrics
from app.services.timeline import Window

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=List[MetricOut])
def search_metrics(component: Optional[str] = Depends(component_filter),
                   q: Optional[str] = Query(None, max_length=100, pattern=NO_NUL),
                   session: Session = Depends(get_session)) -> Any:
    return metrics.search(session, component, q)


@router.get("/series", response_model=MetricSeriesOut)
def get_metric_series(ids: str = Query(..., max_length=100),
                      window: Window = Depends(time_window),
                      session: Session = Depends(get_session)) -> Any:
    return metrics.series(session, metrics.parse_ids(ids), window)
