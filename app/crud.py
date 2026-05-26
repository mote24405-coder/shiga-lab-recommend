"""DB操作の集約。routers からはここを呼ぶ。"""
from __future__ import annotations
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, delete, text, desc
from sqlalchemy.orm import selectinload

from app.models import (
    Lab, Teacher, Label, LabLabel, Thesis, ThesisLabel,
    LabEvidence, RecommendationRun, RecommendationResult,
    SurveyQuestion, SurveyResponse, SurveyAnswer,
    Feedback, SearchLog, SearchSynonym, LabView,
)


# ── Labs ───────────────────────────────────────────────
async def get_labs(
    db: AsyncSession,
    label_ids: list[int] | None = None,
    match: str = "or",
    skip: int = 0,
    limit: int = 100,
) -> list[Lab]:
    # 論文が1件以上紐づいている研究室のみ
    has_thesis = select(Thesis.lab_id).where(Thesis.lab_id == Lab.id).exists()

    stmt = (
        select(Lab)
        .options(
            selectinload(Lab.teachers),
            selectinload(Lab.lab_labels).selectinload(LabLabel.label),
            selectinload(Lab.theses),
        )
        .where(has_thesis)
        .offset(skip).limit(limit)
        .order_by(Lab.name)
    )
    if label_ids:
        if match == "and":
            # lab_labels に全ラベルが揃っている研究室のみ
            subq = (
                select(LabLabel.lab_id)
                .where(LabLabel.label_id.in_(label_ids))
                .group_by(LabLabel.lab_id)
                .having(func.count(LabLabel.label_id) == len(label_ids))
            )
        else:
            subq = (
                select(LabLabel.lab_id)
                .where(LabLabel.label_id.in_(label_ids))
                .distinct()
            )
        stmt = stmt.where(Lab.id.in_(subq))
    result = await db.execute(stmt)
    return result.scalars().unique().all()


async def get_lab(db: AsyncSession, lab_id: int) -> Lab | None:
    stmt = (
        select(Lab)
        .options(
            selectinload(Lab.teachers),
            selectinload(Lab.lab_labels).selectinload(LabLabel.label),
            selectinload(Lab.theses).selectinload(Thesis.thesis_labels).selectinload(ThesisLabel.label),
            selectinload(Lab.evidences).selectinload(LabEvidence.label),
        )
        .where(Lab.id == lab_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_labs_by_ids(db: AsyncSession, lab_ids: list[int]) -> list[Lab]:
    stmt = (
        select(Lab)
        .options(
            selectinload(Lab.teachers),
            selectinload(Lab.lab_labels).selectinload(LabLabel.label),
            selectinload(Lab.theses),
            selectinload(Lab.evidences).selectinload(LabEvidence.label),
        )
        .where(Lab.id.in_(lab_ids))
    )
    result = await db.execute(stmt)
    return result.scalars().unique().all()


# ── Labels ─────────────────────────────────────────────
async def get_labels(db: AsyncSession, label_type: str | None = None) -> list[Label]:
    stmt = select(Label).order_by(Label.label_type, Label.name)
    if label_type:
        stmt = stmt.where(Label.label_type == label_type)
    result = await db.execute(stmt)
    return result.scalars().all()


# ── Recommendation ─────────────────────────────────────
async def create_recommendation_run(
    db: AsyncSession,
    session_id: str,
    method_ids: list[int],
    data_ids: list[int],
    theme_ids: list[int],
    free_text: str | None,
) -> RecommendationRun:
    run = RecommendationRun(
        session_id=session_id,
        input_method_label_ids=method_ids,
        input_data_label_ids=data_ids,
        input_theme_label_ids=theme_ids,
        free_text=free_text,
    )
    db.add(run)
    await db.flush()
    return run


async def create_recommendation_results(
    db: AsyncSession,
    run_id: uuid.UUID,
    scores,
) -> None:
    from app.services.recommendation import RecommendationScore
    for rank, score in enumerate(scores, start=1):
        result = RecommendationResult(
            run_id=run_id,
            lab_id=score.lab_id,
            rank=rank,
            total_score=score.total_score,
            method_score=score.method_score,
            data_score=score.data_score,
            theme_score=score.theme_score,
            matched_labels={
                "method": score.matched_method,
                "data": score.matched_data,
                "theme": score.matched_theme,
            },
            explanation=score.explanation,
        )
        db.add(result)
    await db.flush()


async def get_recommendation_run(
    db: AsyncSession, run_id: uuid.UUID
) -> RecommendationRun | None:
    stmt = (
        select(RecommendationRun)
        .options(
            selectinload(RecommendationRun.results)
            .selectinload(RecommendationResult.lab)
            .selectinload(Lab.teachers)
        )
        .where(RecommendationRun.id == run_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Feedback ───────────────────────────────────────────
async def create_feedback(
    db: AsyncSession,
    session_id: str,
    run_id: uuid.UUID | None,
    result_id: int | None,
    feedback_type: str,
    rating: int | None,
    comment: str | None,
) -> Feedback:
    fb = Feedback(
        session_id=session_id,
        recommendation_run_id=run_id,
        result_id=result_id,
        feedback_type=feedback_type,
        rating=rating,
        comment=comment,
    )
    db.add(fb)
    await db.flush()
    return fb


# ── Survey ─────────────────────────────────────────────
async def get_survey_questions(
    db: AsyncSession, survey_type: str
) -> list[SurveyQuestion]:
    stmt = (
        select(SurveyQuestion)
        .where(SurveyQuestion.survey_type == survey_type, SurveyQuestion.is_active == True)
        .order_by(SurveyQuestion.display_order)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_survey_response(
    db: AsyncSession,
    session_id: str,
    survey_type: str,
    run_id: uuid.UUID | None,
    answers: list[dict],
) -> SurveyResponse:
    response = SurveyResponse(
        session_id=session_id,
        survey_type=survey_type,
        recommendation_run_id=run_id,
    )
    db.add(response)
    await db.flush()
    for a in answers:
        ans = SurveyAnswer(
            response_id=response.id,
            question_id=a["question_id"],
            answer_value=a.get("answer_value"),
            answer_text=a.get("answer_text"),
        )
        db.add(ans)
    await db.flush()
    return response


# ── Search Log ─────────────────────────────────────────
async def create_search_log(
    db: AsyncSession,
    session_id: str,
    query_text: str,
    expanded_keywords: list[str],
    result_count: int,
) -> None:
    log = SearchLog(
        session_id=session_id,
        query_text=query_text,
        expanded_keywords=expanded_keywords,
        result_count=result_count,
    )
    db.add(log)
    await db.flush()


# ── Admin reads ────────────────────────────────────────
async def get_feedbacks(db: AsyncSession, limit: int = 100) -> list[Feedback]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_search_logs(db: AsyncSession, limit: int = 100) -> list[SearchLog]:
    stmt = select(SearchLog).order_by(SearchLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def record_lab_view(
    db: AsyncSession, session_id: str, lab_id: int, duration_sec: int
) -> None:
    db.add(LabView(session_id=session_id, lab_id=lab_id, duration_sec=max(0, duration_sec)))
    await db.flush()


async def get_popular_labs(db: AsyncSession, limit: int = 5) -> list[dict]:
    stmt = (
        select(
            LabView.lab_id,
            func.count().label("view_count"),
            func.round(func.avg(LabView.duration_sec)).label("avg_duration"),
        )
        .group_by(LabView.lab_id)
        .order_by(desc("view_count"))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return []
    lab_ids = [r.lab_id for r in rows]
    labs_map = {
        lab.id: lab
        for lab in (
            await db.execute(
                select(Lab)
                .options(selectinload(Lab.teachers))
                .where(Lab.id.in_(lab_ids))
            )
        ).scalars()
    }
    return [
        {
            "lab": labs_map[r.lab_id],
            "view_count": r.view_count,
            "avg_duration": int(r.avg_duration or 0),
        }
        for r in rows if r.lab_id in labs_map
    ]


async def get_popular_labels(db: AsyncSession, limit: int = 10) -> list[dict]:
    """recommendation_runs の入力ラベルIDを集計して人気ラベルを返す。"""
    stmt = text("""
        SELECT label_id, COUNT(*) AS cnt
        FROM (
            SELECT unnest(input_method_label_ids) AS label_id FROM recommendation_runs
            UNION ALL
            SELECT unnest(input_data_label_ids)   AS label_id FROM recommendation_runs
            UNION ALL
            SELECT unnest(input_theme_label_ids)  AS label_id FROM recommendation_runs
        ) sub
        WHERE label_id IS NOT NULL
        GROUP BY label_id
        ORDER BY cnt DESC
        LIMIT :limit
    """)
    rows = (await db.execute(stmt, {"limit": limit})).all()
    if not rows:
        return []
    label_ids = [r.label_id for r in rows]
    labels_map = {
        label.id: label
        for label in (
            await db.execute(select(Label).where(Label.id.in_(label_ids)))
        ).scalars()
    }
    return [
        {"label": labels_map[r.label_id], "count": r.cnt}
        for r in rows if r.label_id in labels_map
    ]


async def get_survey_responses(
    db: AsyncSession, survey_type: str | None = None, limit: int = 100
) -> list[SurveyResponse]:
    stmt = (
        select(SurveyResponse)
        .options(selectinload(SurveyResponse.answers).selectinload(SurveyAnswer.question))
        .order_by(SurveyResponse.created_at.desc())
        .limit(limit)
    )
    if survey_type:
        stmt = stmt.where(SurveyResponse.survey_type == survey_type)
    result = await db.execute(stmt)
    return result.scalars().all()
