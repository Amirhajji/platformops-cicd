from typing import List, Optional

from pydantic import BaseModel


class MetricOut(BaseModel):
    id: int
    component_id: str
    column_name: str
    metric_id: str
    name: str
    unit: str
    resource: str
    level: str
    period_min: int
    range_min: float
    range_max: Optional[float]


class MetricValues(BaseModel):
    id: int
    column_name: str
    name: str
    unit: str
    values: List[float]


class MetricSeriesOut(BaseModel):
    bucket_ticks: int
    ts: List[str]
    series: List[MetricValues]
