from typing import List

from pydantic import BaseModel


class RunOut(BaseModel):
    spec_version: str
    seed: int
    start_utc: str
    end_utc: str
    tick_seconds: int
    ticks: int


class ScopeOut(BaseModel):
    scope: str
    name: str
    z: float
    status: str
    min_z: float
    alerts: int
    incidents: int


class OverviewOut(BaseModel):
    from_ts: str
    to_ts: str
    scopes: List[ScopeOut]


class KqiSeriesOut(BaseModel):
    scope: str
    bucket_ticks: int
    ts: List[str]
    z: List[float]
    status: List[str]


class ComponentOut(BaseModel):
    id: str
    name: str
    namespace: str


class KpiOut(BaseModel):
    id: str
    name: str
    signal: str
    type: str
    value: float
    health: float
    good: float
    bad: float
    better: str


class ComponentDetailOut(ComponentOut):
    at: str
    z: float
    status: str
    kpis: List[KpiOut]


class KpiSeriesOut(BaseModel):
    id: str
    component_id: str
    name: str
    good: float
    bad: float
    better: str
    bucket_ticks: int
    ts: List[str]
    value: List[float]
    health: List[float]
