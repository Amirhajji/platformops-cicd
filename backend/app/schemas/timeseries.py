# app/schemas/timeseries.py
from pydantic import BaseModel
from typing import List, Dict

class Point(BaseModel):
    tick: int
    timestamp: int
    value: float

class SingleSeries(BaseModel):
    signal_code: str
    points: List[Point]

class MultiSeries(BaseModel):
    signals: Dict[str, List[Point]]
