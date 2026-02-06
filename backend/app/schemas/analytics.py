from pydantic import BaseModel, Field
from typing import Dict, List, Optional


# -------------------------
# Existing
# -------------------------
class VolatilityResponse(BaseModel):
    signal_code: str
    window: int
    volatility: float


class DegradingSignal(BaseModel):
    signal_code: str
    slope: float
    polarity: str


class ComponentHealth(BaseModel):
    component_code: str
    health_score: float


# -------------------------
# New: System stats
# -------------------------
class TickRange(BaseModel):
    min_tick: Optional[int] = None
    max_tick: Optional[int] = None


class SystemIngestionStats(BaseModel):
    total_rows: int
    components: int
    tick_range: TickRange
    latest_tick_by_component: Dict[str, int] = Field(default_factory=dict)


class SignalInventoryStats(BaseModel):
    total_signals: int
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_family: Dict[str, int] = Field(default_factory=dict)
    by_role_visibility: Dict[str, int] = Field(default_factory=dict)


class RuleCoverageStats(BaseModel):
    total_rules: int
    signals_with_rule: int
    rule_coverage_ratio: float


class EventStats(BaseModel):
    total_events: int
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)


class SystemStatsResponse(BaseModel):
    ingestion: SystemIngestionStats
    signals: SignalInventoryStats
    rules: RuleCoverageStats
    events: EventStats


# -------------------------
# New: Alerts stats
# -------------------------
class TopItem(BaseModel):
    key: str
    count: int


class LongestOpenAlert(BaseModel):
    alert_event_id: int
    component_code: Optional[str] = None
    signal_code: Optional[str] = None
    severity: Optional[str] = None
    tick_start: Optional[int] = None
    tick_end: Optional[int] = None
    duration_ticks: Optional[int] = None


class AlertsStatsResponse(BaseModel):
    window: Dict[str, Optional[int]]  # FIXED
    totals: Dict[str, int]
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    top_components: List[TopItem]
    top_signals: List[TopItem]
    longest_open: List[LongestOpenAlert]


# -------------------------
# New: Component rankings
# -------------------------
class ComponentRanking(BaseModel):
    component_code: str
    health_score: float
    open_alerts: int
    critical_open_alerts: int
    warning_open_alerts: int
    risk_score: float


class ComponentRankingsResponse(BaseModel):
    ranked: List[ComponentRanking]


# -------------------------
# New: Signal coverage
# -------------------------
class SignalCoverageItem(BaseModel):
    signal_code: str
    component_code: str
    column_name: str
    window_ticks: int
    total_component_points_in_window: int
    points_with_metric_present: int
    coverage_ratio: float


class SignalCoverageResponse(BaseModel):
    window_ticks: int
    worst: List[SignalCoverageItem]


# -------------------------
# New: Active hotspots
# -------------------------
class HotspotItem(BaseModel):
    signal_code: str
    component_code: Optional[str] = None
    open_events: int
    critical_open: int
    warning_open: int
    max_duration_ticks: int
    last_tick_seen: int


class HotspotsResponse(BaseModel):
    hotspots: List[HotspotItem]
