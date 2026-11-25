"""Alerts and incidents."""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.deps import MAX_INT, component_filter, current_run, time_window
from app.core.db import get_session
from app.schemas.detections import AlertOut, IncidentDetailOut, IncidentOut
from app.services import detections
from app.services.timeline import Run, Window

router = APIRouter(tags=["detections"])


@router.get("/alerts", response_model=List[AlertOut])
def get_alerts(component: Optional[str] = Depends(component_filter),
               window: Window = Depends(time_window),
               session: Session = Depends(get_session)) -> Any:
    return detections.list_alerts(session, component, window)


@router.get("/incidents", response_model=List[IncidentOut])
def get_incidents(component: Optional[str] = Depends(component_filter),
                  window: Window = Depends(time_window),
                  session: Session = Depends(get_session)) -> Any:
    return detections.list_incidents(session, component, window)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailOut)
def get_incident(incident_id: int = Path(..., ge=1, le=MAX_INT),
                 run: Run = Depends(current_run),
                 session: Session = Depends(get_session)) -> Any:
    return detections.incident_detail(session, incident_id, run)
