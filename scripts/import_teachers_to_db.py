"""
data/raw/teachers.json をDBに投入。
実行: docker compose run --rm web python scripts/import_teachers_to_db.py

処理:
  1. labs テーブルに研究室を upsert (教員名 + "研究室" で命名)
  2. teachers テーブルに教員を upsert
  3. theses.lab_id を教員名マッチングで再更新
  4. thesis_labels → lab_labels に集計
"""
import json, os, sys, asyncio, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Lab, Label, Teacher, Thesis, ThesisLabel, LabLabel, LabEvidence

TEACHERS_JSON = "data/raw/teachers.json"


def make_slug(name: str) -> str:
    """例: '山田 太郎' → 'yamada'（簡易スラグ）"""
    import unicodedata
    # スペース・記号除去して小文字
    slug = re.sub(r"[^\w]", "_", name.lower())
    return slug[:50]


async def upsert_lab(session, teacher_data: dict) -> int:
    """教員名から研究室を作成/取得してidを返す"""
    name = teacher_data["name"]
    lab_name = f"{name}研究室"
    slug = make_slug(name)

    result = await session.execute(select(Lab).where(Lab.name == lab_name))
    lab = result.scalar_one_or_none()
    if not lab:
        lab = Lab(
            name=lab_name,
            slug=slug,
            description=teacher_data.get("bio", "") or "",
            official_url=teacher_data.get("researchmap_url", "") or None,
            lab_site_url=teacher_data.get("lab_site_url", "") or None,
        )
        session.add(lab)
        await session.flush()
        print(f"  [NEW LAB] {lab_name}")
    else:
        # 情報更新
        if teacher_data.get("bio"):
            lab.description = teacher_data["bio"]
        if teacher_data.get("researchmap_url"):
            lab.official_url = teacher_data["researchmap_url"]
        if teacher_data.get("lab_site_url"):
            lab.lab_site_url = teacher_data["lab_site_url"]
        print(f"  [UPD LAB] {lab_name}")

    return lab.id


async def upsert_teacher(session, lab_id: int, teacher_data: dict) -> int:
    """教員を upsert してidを返す"""
    name = teacher_data["name"]

    result = await session.execute(select(Teacher).where(Teacher.name == name))
    teacher = result.scalar_one_or_none()

    specialties = teacher_data.get("specialties", [])
    if teacher_data.get("keywords"):
        specialties = list(dict.fromkeys(specialties + teacher_data["keywords"]))  # 重複除去

    if not teacher:
        teacher = Teacher(
            lab_id=lab_id,
            name=name,
            profile_url=teacher_data.get("profile_url", "") or None,
            specialties=specialties or None,
            bio=teacher_data.get("bio", "") or None,
        )
        session.add(teacher)
    else:
        teacher.lab_id = lab_id
        teacher.profile_url = teacher_data.get("profile_url") or teacher.profile_url
        if specialties:
            teacher.specialties = specialties
        if teacher_data.get("bio"):
            teacher.bio = teacher_data["bio"]

    await session.flush()
    return teacher.id


async def match_theses_to_labs(session, teacher_name: str, lab_id: int) -> int:
    """
    著者名に教員名が含まれる論文 (指導教員として著者欄に記載されているケース) に
    lab_id を設定。さらに research_group / supervisor_name でもマッチを試みる。
    実際には thesis.author_name は学生名なのでマッチしない場合がほとんどだが、
    raw_labels.evidence_method の文字列内に指導教員名が含まれることがある。
    """
    count = 0
    result = await session.execute(
        select(Thesis).where(Thesis.lab_id.is_(None))
    )
    theses = result.scalars().all()

    for thesis in theses:
        # supervisor_name フィールドに名前がある場合
        if thesis.supervisor_name and teacher_name in thesis.supervisor_name:
            thesis.lab_id = lab_id
            count += 1
            continue

        # raw_labels の evidence テキストに名前が含まれる場合
        raw = thesis.raw_labels or {}
        evidence = raw.get("evidence_method", "") + raw.get("evidence_data", "")
        if teacher_name in evidence:
            thesis.lab_id = lab_id
            count += 1

    return count


async def apply_teacher_labels(session, lab_id: int, teacher_data: dict) -> int:
    """専門分野・キーワードをラベルマスタに upsert して lab_labels / lab_evidence に追加"""
    terms = list(dict.fromkeys(
        (teacher_data.get("specialties") or []) +
        (teacher_data.get("keywords") or [])
    ))

    added = 0
    for term in terms:
        term = term.strip()
        if not term:
            continue

        result = await session.execute(
            select(Label).where(Label.name == term, Label.label_type == "theme")
        )
        label = result.scalar_one_or_none()
        if not label:
            label = Label(label_type="theme", name=term)
            session.add(label)
            await session.flush()

        existing = await session.execute(
            select(LabLabel).where(LabLabel.lab_id == lab_id, LabLabel.label_id == label.id)
        )
        if existing.scalar_one_or_none():
            continue

        session.add(LabLabel(lab_id=lab_id, label_id=label.id, confidence="high"))
        session.add(LabEvidence(
            lab_id=lab_id,
            label_id=label.id,
            evidence_text=term,
            evidence_url=teacher_data.get("profile_url"),
            source_type="official_site",
            confidence="high",
        ))
        added += 1

    await session.flush()
    return added


async def aggregate_lab_labels(session, lab_id: int):
    """lab_id に紐づく thesis_labels を lab_labels に集計"""
    # 対象論文のlabel_idを収集
    result = await session.execute(
        select(ThesisLabel)
        .join(Thesis, ThesisLabel.thesis_id == Thesis.id)
        .where(Thesis.lab_id == lab_id)
    )
    thesis_label_rows = result.scalars().all()

    # label_id ごとに confidence を集計（highが最多なら high）
    from collections import Counter
    label_conf: dict[int, list[str]] = {}
    for tl in thesis_label_rows:
        label_conf.setdefault(tl.label_id, []).append(tl.confidence or "medium")

    added = 0
    for label_id, confs in label_conf.items():
        # 既存チェック
        existing = await session.execute(
            select(LabLabel).where(LabLabel.lab_id == lab_id, LabLabel.label_id == label_id)
        )
        if existing.scalar_one_or_none():
            continue

        most_common = Counter(confs).most_common(1)[0][0]
        ll = LabLabel(lab_id=lab_id, label_id=label_id, confidence=most_common)
        session.add(ll)
        added += 1

    await session.flush()
    return added


async def main():
    if not os.path.exists(TEACHERS_JSON):
        print(f"{TEACHERS_JSON} が見つかりません。crawl_teachers.py を先に実行してください。")
        return

    with open(TEACHERS_JSON, encoding="utf-8") as f:
        teachers_data: list[dict] = json.load(f)

    print(f"教員数: {len(teachers_data)} 名")

    lab_created, teacher_created, total_labels = 0, 0, 0

    for teacher_data in teachers_data:
        name = teacher_data.get("name", "")
        if not name:
            continue

        print(f"\n--- {name} ---")
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    lab_id = await upsert_lab(session, teacher_data)
                    await upsert_teacher(session, lab_id, teacher_data)
                    matched = await match_theses_to_labs(session, name, lab_id)
                    teacher_label_count = await apply_teacher_labels(session, lab_id, teacher_data)
                    label_count = await aggregate_lab_labels(session, lab_id)
                    if matched:
                        print(f"  論文紐付け: {matched} 件")
                    print(f"  教員プロファイルラベル: {teacher_label_count} 件")
                    print(f"  論文ラベル集計: {label_count} 件")
                    total_labels += teacher_label_count + label_count

        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n=== 完了 ===")
    print(f"  {len(teachers_data)} 名処理")
    print(f"  lab_labels 追加: {total_labels} 件")
    print("\nDBを確認してください: http://localhost:8080")


if __name__ == "__main__":
    asyncio.run(main())
