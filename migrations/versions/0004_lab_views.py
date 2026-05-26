"""add lab_views table

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_views",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("lab_id", sa.Integer(), sa.ForeignKey("labs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lab_views_lab_id",     "lab_views", ["lab_id"])
    op.create_index("ix_lab_views_session_id",  "lab_views", ["session_id"])
    op.create_index("ix_lab_views_created_at",  "lab_views", ["created_at"])


def downgrade() -> None:
    op.drop_table("lab_views")
