"""Database schema (docs/PLATFORM_V1.md, section 2).

Timestamps are not stored per point: ts = start_utc + tick * tick_seconds.
Every end_tick is included in its interval.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Double, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SimulationRun(Base):
    __tablename__ = "simulation_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    spec_version: Mapped[str] = mapped_column(Text)
    seed: Mapped[int]
    start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tick_seconds: Mapped[int]
    ticks: Mapped[int]
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    manifest_sha256: Mapped[str] = mapped_column(String(64))


class Component(Base):
    __tablename__ = "components"

    id: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    namespace: Mapped[str] = mapped_column(Text)


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[str] = mapped_column(ForeignKey("components.id"), index=True)
    level: Mapped[str] = mapped_column(Text)
    resource: Mapped[str] = mapped_column(Text)
    metric_id: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(Text)
    range_min: Mapped[float] = mapped_column(Double)
    range_max: Mapped[Optional[float]] = mapped_column(Double)
    period_min: Mapped[int]
    decimals: Mapped[int]
    column_name: Mapped[str] = mapped_column(Text, unique=True)


class MetricPoint(Base):
    __tablename__ = "metric_points"

    metric_id: Mapped[int] = mapped_column(
        ForeignKey("metrics.id"), primary_key=True, autoincrement=False)
    tick: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    value: Mapped[float] = mapped_column(Double)


class Kpi(Base):
    __tablename__ = "kpis"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    component_id: Mapped[str] = mapped_column(ForeignKey("components.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    signal: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(Text)
    input: Mapped[str] = mapped_column(Text)
    good: Mapped[float] = mapped_column(Double)
    bad: Mapped[float] = mapped_column(Double)
    better: Mapped[str] = mapped_column(Text)


class KpiPoint(Base):
    __tablename__ = "kpi_points"

    kpi_id: Mapped[str] = mapped_column(ForeignKey("kpis.id"), primary_key=True)
    tick: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    value: Mapped[float] = mapped_column(Double)
    health: Mapped[float] = mapped_column(Double)


class KqiPoint(Base):
    __tablename__ = "kqi_points"

    scope: Mapped[str] = mapped_column(Text, primary_key=True)  # C1..C8 or GLOBAL
    tick: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    z: Mapped[float] = mapped_column(Double)
    status: Mapped[str] = mapped_column(Text)


class SimulatedIncident(Base):
    __tablename__ = "simulated_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[str] = mapped_column(ForeignKey("components.id"))
    start_tick: Mapped[int]
    end_tick: Mapped[int]
    description: Mapped[str] = mapped_column(Text)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    kpi_id: Mapped[str] = mapped_column(ForeignKey("kpis.id"))
    component_id: Mapped[str] = mapped_column(ForeignKey("components.id"))
    start_tick: Mapped[int]
    end_tick: Mapped[int]
    min_health: Mapped[float] = mapped_column(Double)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[str] = mapped_column(ForeignKey("components.id"))
    start_tick: Mapped[int]
    end_tick: Mapped[int]
    alert_count: Mapped[int]
    min_z: Mapped[float] = mapped_column(Double)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'viewer')", name="users_role_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
