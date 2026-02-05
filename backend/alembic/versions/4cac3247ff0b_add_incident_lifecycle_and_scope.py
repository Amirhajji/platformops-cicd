"""add incident lifecycle and scope

Revision ID: 4cac3247ff0b
Revises: d70a10ed7d0c
Create Date: 2026-01-06 09:33:27.699780
"""

from alembic import op
import sqlalchemy as sa

# === REQUIRED BY ALEMBIC ===
revision = "4cac3247ff0b"
down_revision = "d70a10ed7d0c"
branch_labels = None
depends_on = None
# ===========================


def upgrade():
    op.add_column(
        "incidents",
        sa.Column("component_code", sa.Text(), nullable=False),
    )
    op.add_column(
        "incidents",
        sa.Column("status", sa.Text(), server_default="OPEN", nullable=False),
    )
    op.add_column(
        "incidents",
        sa.Column("origin", sa.Text(), server_default="REAL", nullable=False),
    )


def downgrade():
    op.drop_column("incidents", "origin")
    op.drop_column("incidents", "status")
    op.drop_column("incidents", "component_code")
