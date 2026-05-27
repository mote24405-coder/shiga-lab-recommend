"""推薦スコアリングサービス。説明可能なラベル一致スコア。"""
from __future__ import annotations
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

WEIGHTS = {"method": 0.30, "data": 0.35, "theme": 0.25}
# 将来: WEIGHTS["style"] = 0.10 を追加し残りを調整


@dataclass
class RecommendationScore:
    lab_id: int
    lab_name: str
    teacher_name: str
    total_score: float
    method_score: float
    data_score: float
    theme_score: float
    matched_method: list[str] = field(default_factory=list)
    matched_data: list[str] = field(default_factory=list)
    matched_theme: list[str] = field(default_factory=list)
    explanation: str = ""


def _jaccard(user_ids: set[int], lab_ids: set[int]) -> float:
    if not user_ids:
        return 0.0
    intersection = user_ids & lab_ids
    return len(intersection) / len(user_ids)


async def compute_recommendations(
    db: AsyncSession,
    method_label_ids: list[int],
    data_label_ids: list[int],
    theme_label_ids: list[int],
) -> list[RecommendationScore]:
    from app.models import Lab, LabLabel, Label, Teacher, Thesis

    # 論文が1件以上ある研究室のみ対象
    has_thesis = select(Thesis.lab_id).where(Thesis.lab_id == Lab.id).exists()
    stmt = (
        select(Lab)
        .options(
            selectinload(Lab.lab_labels).selectinload(LabLabel.label),
            selectinload(Lab.teachers),
        )
        .where(has_thesis)
    )
    result = await db.execute(stmt)
    labs = result.scalars().all()

    user_method = set(method_label_ids)
    user_data = set(data_label_ids)
    user_theme = set(theme_label_ids)

    scores: list[RecommendationScore] = []
    for lab in labs:
        # high のみを使用 (medium は補助情報だが discriminability が下がるため除外)
        high_labels = [ll for ll in lab.lab_labels if ll.confidence == "high"]
        lab_method_ids = {ll.label_id for ll in high_labels if ll.label.label_type == "method"}
        lab_data_ids = {ll.label_id for ll in high_labels if ll.label.label_type == "data"}
        lab_theme_ids = {ll.label_id for ll in high_labels if ll.label.label_type == "theme"}

        method_score = _jaccard(user_method, lab_method_ids)
        data_score = _jaccard(user_data, lab_data_ids)
        theme_score = _jaccard(user_theme, lab_theme_ids)

        total = (
            WEIGHTS["method"] * method_score
            + WEIGHTS["data"] * data_score
            + WEIGHTS["theme"] * theme_score
        )

        if total == 0.0:
            continue

        label_map = {ll.label_id: ll.label.name for ll in high_labels}
        matched_method = [label_map[i] for i in user_method & lab_method_ids]
        matched_data = [label_map[i] for i in user_data & lab_data_ids]
        matched_theme = [label_map[i] for i in user_theme & lab_theme_ids]

        explanation = _build_explanation(lab.name, matched_method, matched_data, matched_theme)
        teacher_name = lab.teachers[0].name if lab.teachers else "—"

        scores.append(RecommendationScore(
            lab_id=lab.id,
            lab_name=lab.name,
            teacher_name=teacher_name,
            total_score=round(total, 4),
            method_score=round(method_score, 4),
            data_score=round(data_score, 4),
            theme_score=round(theme_score, 4),
            matched_method=matched_method,
            matched_data=matched_data,
            matched_theme=matched_theme,
            explanation=explanation,
        ))

    scores.sort(key=lambda s: s.total_score, reverse=True)
    return scores


def _build_explanation(
    lab_name: str,
    method: list[str],
    data: list[str],
    theme: list[str],
) -> str:
    parts = []
    if method:
        parts.append(f"手法「{'、'.join(method)}」")
    if data:
        parts.append(f"データ「{'、'.join(data)}」")
    if theme:
        parts.append(f"テーマ「{'、'.join(theme)}」")
    if not parts:
        return ""
    return f"{lab_name}は{'と'.join(parts)}があなたの興味と一致しています。"
