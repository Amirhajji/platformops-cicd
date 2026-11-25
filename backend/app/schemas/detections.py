from typing import List, Optional

from pydantic import BaseModel


class IntervalOut(BaseModel):
    id: int
    start_ts: str
    end_ts: str
    duration_seconds: int


class AlertOut(IntervalOut):
    kpi_id: str
    kpi_name: str
    component_id: str
    min_health: float


class IncidentOut(IntervalOut):
    component_id: str
    alert_count: int
    min_z: float


class SimulatedIncidentOut(IntervalOut):
    description: str


class IncidentDetailOut(IncidentOut):
    alerts: List[AlertOut]
    simulated_incident: Optional[SimulatedIncidentOut]
