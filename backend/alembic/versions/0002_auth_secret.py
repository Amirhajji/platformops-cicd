"""Secret that signs the login tokens (docs/PLATFORM_V1.md, section 2)

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_secret",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name="auth_secret_single_row_check"),
    )


def downgrade() -> None:
    op.drop_table("auth_secret")
