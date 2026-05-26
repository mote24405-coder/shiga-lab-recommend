from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, String, Text, Boolean, Float, ForeignKey,
    DateTime, func, ARRAY, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# ── 研究室 ─────────────────────────────────────────────
class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_kana: Mapped[Optional[str]] = mapped_column(String(200))
    slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    official_url: Mapped[Optional[str]] = mapped_column(String(500))
    lab_site_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    teachers: Mapped[list[Teacher]] = relationship("Teacher", back_populates="lab")
    lab_labels: Mapped[list[LabLabel]] = relationship("LabLabel", back_populates="lab")
    theses: Mapped[list[Thesis]] = relationship("Thesis", back_populates="lab")
    evidences: Mapped[list[LabEvidence]] = relationship("LabEvidence", back_populates="lab")


# ── 教員 ───────────────────────────────────────────────
class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("labs.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_kana: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    profile_url: Mapped[Optional[str]] = mapped_column(String(500))
    specialties: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lab: Mapped[Optional[Lab]] = relationship("Lab", back_populates="teachers")


# ── ラベルマスタ ────────────────────────────────────────
class Label(Base):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("label_type", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label_type: Mapped[str] = mapped_column(String(20), nullable=False)  # method/data/theme/style
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lab_labels: Mapped[list[LabLabel]] = relationship("LabLabel", back_populates="label")
    thesis_labels: Mapped[list[ThesisLabel]] = relationship("ThesisLabel", back_populates="label")
    evidences: Mapped[list[LabEvidence]] = relationship("LabEvidence", back_populates="label")


# ── 研究室ラベル付与 ────────────────────────────────────
class LabLabel(Base):
    __tablename__ = "lab_labels"
    __table_args__ = (UniqueConstraint("lab_id", "label_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_id: Mapped[int] = mapped_column(Integer, ForeignKey("labs.id"), index=True)
    label_id: Mapped[int] = mapped_column(Integer, ForeignKey("labels.id"), index=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(10))  # high/medium/low
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lab: Mapped[Lab] = relationship("Lab", back_populates="lab_labels")
    label: Mapped[Label] = relationship("Label", back_populates="lab_labels")


# ── 修士論文 ────────────────────────────────────────────
class Thesis(Base):
    __tablename__ = "theses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("labs.id"), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[Optional[str]] = mapped_column(String(200))
    year: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    supervisor_name: Mapped[Optional[str]] = mapped_column(String(200))
    repo_url: Mapped[Optional[str]] = mapped_column(String(500))
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500))
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lab: Mapped[Optional[Lab]] = relationship("Lab", back_populates="theses")
    thesis_labels: Mapped[list[ThesisLabel]] = relationship("ThesisLabel", back_populates="thesis")


# ── 論文ラベル ──────────────────────────────────────────
class ThesisLabel(Base):
    __tablename__ = "thesis_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thesis_id: Mapped[int] = mapped_column(Integer, ForeignKey("theses.id"), index=True)
    label_id: Mapped[int] = mapped_column(Integer, ForeignKey("labels.id"), index=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(10))

    thesis: Mapped[Thesis] = relationship("Thesis", back_populates="thesis_labels")
    label: Mapped[Label] = relationship("Label", back_populates="thesis_labels")


# ── 根拠情報 ────────────────────────────────────────────
class LabEvidence(Base):
    __tablename__ = "lab_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_id: Mapped[int] = mapped_column(Integer, ForeignKey("labs.id"), index=True)
    label_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("labels.id"), nullable=True)
    evidence_text: Mapped[Optional[str]] = mapped_column(Text)
    evidence_url: Mapped[Optional[str]] = mapped_column(String(500))
    source_type: Mapped[Optional[str]] = mapped_column(String(30))  # official_site/lab_site/thesis_title/thesis_pdf/manual
    confidence: Mapped[Optional[str]] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lab: Mapped[Lab] = relationship("Lab", back_populates="evidences")
    label: Mapped[Optional[Label]] = relationship("Label", back_populates="evidences")


# ── 推薦実行ログ ────────────────────────────────────────
class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    input_method_label_ids: Mapped[Optional[list[int]]] = mapped_column(ARRAY(Integer))
    input_data_label_ids: Mapped[Optional[list[int]]] = mapped_column(ARRAY(Integer))
    input_theme_label_ids: Mapped[Optional[list[int]]] = mapped_column(ARRAY(Integer))
    free_text: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    results: Mapped[list[RecommendationResult]] = relationship("RecommendationResult", back_populates="run")
    feedbacks: Mapped[list[Feedback]] = relationship("Feedback", back_populates="run")


# ── 推薦結果 ────────────────────────────────────────────
class RecommendationResult(Base):
    __tablename__ = "recommendation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recommendation_runs.id"), index=True)
    lab_id: Mapped[int] = mapped_column(Integer, ForeignKey("labs.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[float] = mapped_column(Float)
    method_score: Mapped[float] = mapped_column(Float, default=0.0)
    data_score: Mapped[float] = mapped_column(Float, default=0.0)
    theme_score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_labels: Mapped[Optional[dict]] = mapped_column(JSONB)  # {method:[...], data:[...], theme:[...]}
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[RecommendationRun] = relationship("RecommendationRun", back_populates="results")
    lab: Mapped[Lab] = relationship("Lab")
    feedbacks: Mapped[list[Feedback]] = relationship("Feedback", back_populates="result")


# ── アンケート質問マスタ ────────────────────────────────
class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_type: Mapped[str] = mapped_column(String(30), nullable=False)  # recommendation/post_use
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_format: Mapped[str] = mapped_column(String(20), nullable=False)  # scale/choice/text
    options: Mapped[Optional[dict]] = mapped_column(JSONB)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    answers: Mapped[list[SurveyAnswer]] = relationship("SurveyAnswer", back_populates="question")


# ── アンケート回答セッション ────────────────────────────
class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    survey_type: Mapped[str] = mapped_column(String(30))
    recommendation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("recommendation_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    answers: Mapped[list[SurveyAnswer]] = relationship("SurveyAnswer", back_populates="response")


# ── アンケート個別回答 ──────────────────────────────────
class SurveyAnswer(Base):
    __tablename__ = "survey_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("survey_responses.id"), index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("survey_questions.id"))
    answer_value: Mapped[Optional[int]] = mapped_column(Integer)
    answer_text: Mapped[Optional[str]] = mapped_column(Text)
    answer_options: Mapped[Optional[dict]] = mapped_column(JSONB)

    response: Mapped[SurveyResponse] = relationship("SurveyResponse", back_populates="answers")
    question: Mapped[SurveyQuestion] = relationship("SurveyQuestion", back_populates="answers")


# ── フィードバック ──────────────────────────────────────
class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    recommendation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("recommendation_runs.id"), nullable=True)
    result_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("recommendation_results.id"), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(30))  # run_overall/per_result
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[Optional[RecommendationRun]] = relationship("RecommendationRun", back_populates="feedbacks")
    result: Mapped[Optional[RecommendationResult]] = relationship("RecommendationResult", back_populates="feedbacks")


# ── 検索ログ ────────────────────────────────────────────
class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    query_text: Mapped[Optional[str]] = mapped_column(Text)
    expanded_keywords: Mapped[Optional[list]] = mapped_column(JSONB)
    result_count: Mapped[Optional[int]] = mapped_column(Integer)
    clicked_lab_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("labs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# ── 同義語辞書 ──────────────────────────────────────────
class SearchSynonym(Base):
    __tablename__ = "search_synonyms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    synonyms: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
