# app/schemas/alerts.py
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


Operator = Literal["gt", "gte", "lt", "lte", "eq", "ne"]
Severity = Literal["info", "warning", "critical"]


class AlertRuleCreate(BaseModel):
    signal_code: str = Field(..., min_length=3)
    operator: Operator
    threshold: float
    min_duration_ticks: int = Field(..., ge=1, le=1000000)
    severity: Severity = "warning"
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    operator: Optional[Operator] = None
    threshold: Optional[float] = None
    min_duration_ticks: Optional[int] = Field(default=None, ge=1, le=1000000)
    severity: Optional[Severity] = None
    enabled: Optional[bool] = None


class AlertRuleOut(BaseModel):
    id: int
    signal_code: str
    operator: str
    threshold: float
    min_duration_ticks: int
    severity: str
    enabled: bool

    class Config:
        from_attributes = True


class AlertEventOut(BaseModel):
    id: int
    rule_id: int
    component_code: Optional[str] = None
    signal_code: Optional[str] = None
    tick_start: Optional[int] = None
    tick_end: Optional[int] = None
    peak_value: Optional[float] = None
    severity: Optional[str] = None

    class Config:
        from_attributes = True


class BulkCreateRules(BaseModel):
    rules: List[AlertRuleCreate]


class EvaluateRequest(BaseModel):
    # If not provided, we evaluate last `last_ticks` ticks
    from_tick: Optional[int] = None
    to_tick: Optional[int] = None
    last_ticks: int = Field(default=300, ge=2, le=20000)

    # If true, we delete old events in that tick window first (rebuild clean)
    rebuild_window: bool = True


class EvaluateResponse(BaseModel):
    evaluated_rules: int
    created_events: int
