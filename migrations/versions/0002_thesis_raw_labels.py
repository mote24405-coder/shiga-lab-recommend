"""add raw_labels and summary to theses

Revision ID: 0002
Revises: 0001
Create Date: 2025-05-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 細粒度ラベル・要約・根拠文 をJSONBで保存
    op.add_column("theses", sa.Column("raw_labels", JSONB(), nullable=True))
    op.add_column("theses", sa.Column("summary_ja", sa.Text(), nullable=True))
    # リポジトリ固有IDで重複チェック用
    op.add_column("theses", sa.Column("repo_item_id", sa.Integer(), nullable=True))
    op.create_index("idx_theses_repo_item_id", "theses", ["repo_item_id"])


def downgrade() -> None:
    op.drop_index("idx_theses_repo_item_id", "theses")
    op.drop_column("theses", "repo_item_id")
    op.drop_column("theses", "summary_ja")
    op.drop_column("theses", "raw_labels")
