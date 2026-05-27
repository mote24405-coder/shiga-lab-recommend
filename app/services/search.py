"""横断検索サービス。ILIKE + 同義語展開。"""
from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload

from app.services.search_synonyms import expand_query


@dataclass
class SearchResult:
    lab_id: int
    lab_name: str
    teacher_name: str
    match_reason: str
    official_url: str | None


async def search_labs(
    db: AsyncSession,
    query: str,
    label_ids: list[int] | None = None,
) -> tuple[list[SearchResult], list[str]]:
    """研究室横断検索。(results, expanded_keywords) を返す。"""
    from app.models import Lab, Teacher, Label, LabLabel, Thesis, LabEvidence

    expanded = expand_query(query)

    def ilike_conditions(col):
        return [col.ilike(f"%{kw}%") for kw in expanded]

    # 研究室名・説明
    lab_stmt = (
        select(Lab)
        .options(selectinload(Lab.teachers), selectinload(Lab.lab_labels).selectinload(LabLabel.label))
        .where(or_(
            *ilike_conditions(Lab.name),
            *ilike_conditions(Lab.description),
        ))
    )

    # ラベル絞り込み
    if label_ids:
        lab_stmt = lab_stmt.join(LabLabel).where(LabLabel.label_id.in_(label_ids))

    lab_result = await db.execute(lab_stmt)
    labs_by_name = {lab.id: lab for lab in lab_result.scalars().unique()}

    # 教員名・専門分野でヒット → 研究室IDを取得
    teacher_stmt = select(Teacher).where(or_(
        *ilike_conditions(Teacher.name),
        *ilike_conditions(Teacher.bio),
    ))
    t_result = await db.execute(teacher_stmt)
    teacher_lab_ids = {t.lab_id for t in t_result.scalars() if t.lab_id}

    # ラベル名でヒット → 研究室ID
    label_stmt = (
        select(LabLabel)
        .join(Label)
        .options(selectinload(LabLabel.label))
        .where(or_(*ilike_conditions(Label.name)))
    )
    ll_result = await db.execute(label_stmt)
    label_lab_ids = {ll.lab_id for ll in ll_result.scalars()}

    # 論文タイトルでヒット → 研究室ID
    thesis_stmt = select(Thesis).where(or_(*ilike_conditions(Thesis.title)))
    th_result = await db.execute(thesis_stmt)
    thesis_lab_ids = {t.lab_id for t in th_result.scalars() if t.lab_id}

    all_lab_ids = set(labs_by_name.keys()) | teacher_lab_ids | label_lab_ids | thesis_lab_ids
    if not all_lab_ids:
        return [], expanded

    # 全ヒット研究室を一括取得
    full_stmt = (
        select(Lab)
        .options(selectinload(Lab.teachers), selectinload(Lab.lab_labels).selectinload(LabLabel.label))
        .where(Lab.id.in_(all_lab_ids))
    )
    full_result = await db.execute(full_stmt)
    all_labs = full_result.scalars().unique().all()

    results = []
    for lab in all_labs:
        teacher_name = lab.teachers[0].name if lab.teachers else "—"
        reason = _build_reason(lab, labs_by_name, teacher_lab_ids, label_lab_ids, thesis_lab_ids, expanded)
        results.append(SearchResult(
            lab_id=lab.id,
            lab_name=lab.name,
            teacher_name=teacher_name,
            match_reason=reason,
            official_url=lab.official_url,
        ))

    return results, expanded


def _build_reason(lab, labs_by_name, teacher_ids, label_ids, thesis_ids, expanded) -> str:
    reasons = []
    if lab.id in labs_by_name:
        reasons.append("研究室名・説明")
    if lab.id in teacher_ids:
        reasons.append("教員名・専門分野")
    if lab.id in label_ids:
        reasons.append("ラベル")
    if lab.id in thesis_ids:
        reasons.append("論文タイトル")
    return "、".join(reasons) + "に一致"
