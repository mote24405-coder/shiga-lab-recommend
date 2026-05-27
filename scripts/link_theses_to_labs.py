"""
PDF本文に含まれる教員名を手がかりに thesis.lab_id を設定し、
lab_labels を集計する。
実行: docker compose run --rm web python scripts/link_theses_to_labs.py
"""
import json, os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Teacher, Thesis, ThesisLabel, LabLabel

PDF_TEXTS_JSON = "data/processed/pdf_texts.json"
TEACHERS_JSON = "data/raw/teachers.json"


async def main():
    with open(PDF_TEXTS_JSON, encoding="utf-8") as f:
        pdf_texts = json.load(f)
    with open(TEACHERS_JSON, encoding="utf-8") as f:
        teachers_data = json.load(f)

    # 教員名 → lab_id マップ
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Teacher).where(Teacher.lab_id.isnot(None)))
        teacher_lab_map = {t.name: t.lab_id for t in result.scalars().all()}

    print(f"登録済み教員: {len(teacher_lab_map)} 名")

    linked, label_added, skipped = 0, 0, 0

    for repo_id, data in pdf_texts.items():
        text_content = data.get("text", "")

        # 教員名をPDF本文から検索（最初にマッチした1名）
        matched_teacher = None
        for td in teachers_data:
            name = td["name"]
            if name.replace(" ", "") in text_content or name in text_content:
                matched_teacher = name
                break

        if not matched_teacher:
            skipped += 1
            continue

        lab_id = teacher_lab_map.get(matched_teacher)
        if not lab_id:
            skipped += 1
            continue

        async with AsyncSessionLocal() as session:
            async with session.begin():
                t_result = await session.execute(
                    select(Thesis).where(Thesis.repo_item_id == int(repo_id))
                )
                thesis = t_result.scalar_one_or_none()
                if not thesis:
                    skipped += 1
                    continue

                thesis.lab_id = lab_id
                thesis.supervisor_name = matched_teacher
                await session.flush()

                # thesis_labels → lab_labels 集計
                tl_result = await session.execute(
                    select(ThesisLabel).where(ThesisLabel.thesis_id == thesis.id)
                )
                for tl in tl_result.scalars().all():
                    ex = await session.execute(
                        select(LabLabel).where(
                            LabLabel.lab_id == lab_id,
                            LabLabel.label_id == tl.label_id,
                        )
                    )
                    if not ex.scalar_one_or_none():
                        session.add(LabLabel(
                            lab_id=lab_id,
                            label_id=tl.label_id,
                            confidence=tl.confidence,
                        ))
                        label_added += 1

        linked += 1
        print(f"  [{repo_id}] {matched_teacher}研究室 ← {data.get('title', '')[:40]}")

    print(f"\n=== 完了 ===")
    print(f"  論文紐付け: {linked} 件")
    print(f"  lab_labels 追加: {label_added} 件")
    print(f"  マッチなし: {skipped} 件")


if __name__ == "__main__":
    asyncio.run(main())
