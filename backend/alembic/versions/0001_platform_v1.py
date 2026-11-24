"""PlatformOPS V1 schema (docs/PLATFORM_V1.md, section 2)

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_run",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("spec_version", sa.Text, nullable=False),
        sa.Column("seed", sa.Integer, nullable=False),
        sa.Column("start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tick_seconds", sa.Integer, nullable=False),
        sa.Column("ticks", sa.Integer, nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
    )
    op.create_table(
        "components",
        sa.Column("id", sa.String(2), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("namespace", sa.Text, nullable=False),
    )
    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("component_id", sa.String(2),
                  sa.ForeignKey("components.id"), nullable=False, index=True),
        sa.Column("level", sa.Text, nullable=False),
        sa.Column("resource", sa.Text, nullable=False),
        sa.Column("metric_id", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("range_min", sa.Double, nullable=False),
        sa.Column("range_max", sa.Double, nullable=True),
        sa.Column("period_min", sa.Integer, nullable=False),
        sa.Column("decimals", sa.Integer, nullable=False),
        sa.Column("column_name", sa.Text, nullable=False, unique=True),
    )
    op.create_table(
        "metric_points",
        sa.Column("metric_id", sa.Integer, sa.ForeignKey("metrics.id"),
                  primary_key=True, autoincrement=False),
        sa.Column("tick", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("value", sa.Double, nullable=False),
    )
    op.create_table(
        "kpis",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("component_id", sa.String(2),
                  sa.ForeignKey("components.id"), nullable=False, index=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("signal", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("level", sa.Text, nullable=False),
        sa.Column("input", sa.Text, nullable=False),
        sa.Column("good", sa.Double, nullable=False),
        sa.Column("bad", sa.Double, nullable=False),
        sa.Column("better", sa.Text, nullable=False),
    )
    op.create_table(
        "kpi_points",
        sa.Column("kpi_id", sa.Text, sa.ForeignKey("kpis.id"), primary_key=True),
        sa.Column("tick", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("value", sa.Double, nullable=False),
        sa.Column("health", sa.Double, nullable=False),
    )
    op.create_table(
        "kqi_points",
        sa.Column("scope", sa.Text, primary_key=True),
        sa.Column("tick", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("z", sa.Double, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
    )
    op.create_table(
        "simulated_incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("component_id", sa.String(2),
                  sa.ForeignKey("components.id"), nullable=False),
        sa.Column("start_tick", sa.Integer, nullable=False),
        sa.Column("end_tick", sa.Integer, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kpi_id", sa.Text, sa.ForeignKey("kpis.id"), nullable=False),
        sa.Column("component_id", sa.String(2),
                  sa.ForeignKey("components.id"), nullable=False),
        sa.Column("start_tick", sa.Integer, nullable=False),
        sa.Column("end_tick", sa.Integer, nullable=False),
        sa.Column("min_health", sa.Double, nullable=False),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("component_id", sa.String(2),
                  sa.ForeignKey("components.id"), nullable=False),
        sa.Column("start_tick", sa.Integer, nullable=False),
        sa.Column("end_tick", sa.Integer, nullable=False),
        sa.Column("alert_count", sa.Integer, nullable=False),
        sa.Column("min_z", sa.Double, nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.Text, nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'viewer')", name="users_role_check"),
    )


def downgrade() -> None:
    for table in ("users", "incidents", "alerts", "simulated_incidents", "kqi_points",
                  "kpi_points", "kpis", "metric_points", "metrics", "components",
                  "simulation_run"):
        op.drop_table(table)
