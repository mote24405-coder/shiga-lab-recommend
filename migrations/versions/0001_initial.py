"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-05-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "labs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_kana", sa.String(200)),
        sa.Column("slug", sa.String(100), unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("official_url", sa.String(500)),
        sa.Column("lab_site_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "teachers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_id", sa.Integer(), sa.ForeignKey("labs.id"), index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_kana", sa.String(200)),
        sa.Column("email", sa.String(200)),
        sa.Column("profile_url", sa.String(500)),
        sa.Column("specialties", sa.ARRAY(sa.Text())),
        sa.Column("bio", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("label_type", "name"),
    )

    op.create_table(
        "lab_labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_id", sa.Integer(), sa.ForeignKey("labs.id"), index=True),
        sa.Column("label_id", sa.Integer(), sa.ForeignKey("labels.id"), index=True),
        sa.Column("confidence", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("lab_id", "label_id"),
    )

    op.create_table(
        "theses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_id", sa.Integer(), sa.ForeignKey("labs.id"), index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(200)),
        sa.Column("year", sa.Integer(), index=True),
        sa.Column("supervisor_name", sa.String(200)),
        sa.Column("repo_url", sa.String(500)),
        sa.Column("pdf_url", sa.String(500)),
        sa.Column("abstract", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "thesis_labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thesis_id", sa.Integer(), sa.ForeignKey("theses.id"), index=True),
        sa.Column("label_id", sa.Integer(), sa.ForeignKey("labels.id"), index=True),
        sa.Column("confidence", sa.String(10)),
    )

    op.create_table(
        "lab_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_id", sa.Integer(), sa.ForeignKey("labs.id"), index=True),
        sa.Column("label_id", sa.Integer(), sa.ForeignKey("labels.id")),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("evidence_url", sa.String(500)),
        sa.Column("source_type", sa.String(30)),
        sa.Column("confidence", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "recommendation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(100), index=True),
        sa.Column("input_method_label_ids", sa.ARRAY(sa.Integer())),
        sa.Column("input_data_label_ids", sa.ARRAY(sa.Integer())),
        sa.Column("input_theme_label_ids", sa.ARRAY(sa.Integer())),
        sa.Column("free_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "recommendation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("recommendation_runs.id"), index=True),
        sa.Column("lab_id", sa.Integer(), sa.ForeignKey("labs.id"), index=True),
        sa.Column("rank", sa.Integer()),
        sa.Column("total_score", sa.Float()),
        sa.Column("method_score", sa.Float(), server_default="0"),
        sa.Column("data_score", sa.Float(), server_default="0"),
        sa.Column("theme_score", sa.Float(), server_default="0"),
        sa.Column("matched_labels", JSONB()),
        sa.Column("explanation", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "survey_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("survey_type", sa.String(30), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_format", sa.String(20), nullable=False),
        sa.Column("options", JSONB()),
        sa.Column("display_order", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )

    op.create_table(
        "survey_responses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(100)),
        sa.Column("survey_type", sa.String(30)),
        sa.Column("recommendation_run_id", UUID(as_uuid=True), sa.ForeignKey("recommendation_runs.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "survey_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("response_id", UUID(as_uuid=True), sa.ForeignKey("survey_responses.id"), index=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("survey_questions.id")),
        sa.Column("answer_value", sa.Integer()),
        sa.Column("answer_text", sa.Text()),
        sa.Column("answer_options", JSONB()),
    )

    op.create_table(
        "feedbacks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(100)),
        sa.Column("recommendation_run_id", UUID(as_uuid=True), sa.ForeignKey("recommendation_runs.id")),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("recommendation_results.id")),
        sa.Column("feedback_type", sa.String(30)),
        sa.Column("rating", sa.Integer()),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "search_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(100), index=True),
        sa.Column("query_text", sa.Text()),
        sa.Column("expanded_keywords", JSONB()),
        sa.Column("result_count", sa.Integer()),
        sa.Column("clicked_lab_id", sa.Integer(), sa.ForeignKey("labs.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    op.create_table(
        "search_synonyms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term", sa.String(200), unique=True, nullable=False),
        sa.Column("synonyms", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for tbl in [
        "search_synonyms", "search_logs", "feedbacks", "survey_answers",
        "survey_responses", "survey_questions", "recommendation_results",
        "recommendation_runs", "lab_evidence", "thesis_labels", "theses",
        "lab_labels", "labels", "teachers", "labs",
    ]:
        op.drop_table(tbl)
