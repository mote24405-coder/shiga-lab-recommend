"""
OpenAI抽出ラベルをDBにインポート。
実行: docker compose run --rm web python scripts/import_to_db.py

入力:
  data/raw/theses.json              -- クロール済みメタデータ
  data/processed/openai_labels.json -- OpenAI抽出ラベル（v2: supervisor_name含む）

処理:
  1. labels テーブルの確認（migration 0003 で投入済みを前提）
  2. theses を repo_item_id で upsert
  3. supervisor_name → Teacher.name マッチングで lab_id を設定
  4. thesis_labels を作成
  5. lab_labels に集計
"""
import json, os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Lab, Teacher, Label, Thesis, ThesisLabel, LabLabel

THESES_JSON = "data/raw/theses.json"
LABELS_JSON = "data/processed/openai_labels.json"

METHOD_LABELS = [
    "深層学習", "統計モデリング", "時系列解析",
    "自然言語処理", "コンピュータビジョン", "ベイズ手法",
    "強化学習", "因果推論", "最適化", "ネットワーク分析", "データ同化",
]
DATA_LABELS = [
    "画像・映像", "音声", "テキスト", "時系列・センサー",
    "数値・表形式", "地理空間", "IoT",
]
THEME_LABELS = [
    "製造・ものづくり", "医療・ヘルスケア", "農業・自然科学",
    "教育", "経済・金融", "社会・政策", "スポーツ",
    "マーケティング・消費", "交通・インフラ", "音楽・メディア",
]
LABEL_TYPE_MAP = {"method": METHOD_LABELS, "data": DATA_LABELS, "theme": THEME_LABELS}


async def load_label_id_map(session) -> dict[tuple[str, str], int]:
    """DBから {(type, name): id} マップを構築"""
    result = await session.execute(select(Label))
    return {(l.label_type, l.name): l.id for l in result.scalars().all()}


async def build_teacher_lab_map(session) -> dict[str, int]:
    """教員名 → lab_id（完全一致 + スペース除去一致）"""
    result = await session.execute(select(Teacher).where(Teacher.lab_id.isnot(None)))
    mapping: dict[str, int] = {}
    for t in result.scalars().all():
        mapping[t.name] = t.lab_id
        mapping[t.name.replace(" ", "")] = t.lab_id  # スペースなし版も登録
    return mapping


def resolve_lab_id(supervisor_name: str, teacher_lab_map: dict[str, int]) -> int | None:
    if not supervisor_name:
        return None
    # 完全一致
    if supervisor_name in teacher_lab_map:
        return teacher_lab_map[supervisor_name]
    # スペース除去一致
    compact = supervisor_name.replace(" ", "").replace("　", "")
    if compact in teacher_lab_map:
        return teacher_lab_map[compact]
    # 部分一致（姓のみ等のケース）
    for teacher_name, lab_id in teacher_lab_map.items():
        if len(supervisor_name) >= 2 and supervisor_name in teacher_name:
            return lab_id
    return None


async def upsert_thesis(session, item: dict, label_id_map: dict, teacher_lab_map: dict) -> tuple[int, bool]:
    repo_item_id = item.get("repo_id")
    title = item.get("title", "")
    authors = item.get("authors", [])
    year = item.get("year")
    supervisor_name = item.get("supervisor_name", "") or ""
    programming_language = item.get("programming_language", []) or []

    raw_labels = {k: item.get(k, []) for k in [
        "method_raw", "data_raw", "method", "data", "theme",
        "programming_language", "confidence",
    ]}
    author_name = ", ".join(authors) if authors else None
    lab_id = resolve_lab_id(supervisor_name, teacher_lab_map)

    result = await session.execute(select(Thesis).where(Thesis.repo_item_id == repo_item_id))
    thesis = result.scalar_one_or_none()
    created = thesis is None

    if thesis is None:
        thesis = Thesis(
            repo_item_id=repo_item_id,
            title=title,
            author_name=author_name,
            year=year,
            repo_url=item.get("repo_url", ""),
            pdf_url=item.get("pdf_url", ""),
            summary_ja=item.get("summary_ja", ""),
            supervisor_name=supervisor_name or None,
            raw_labels=raw_labels,
            lab_id=lab_id,
        )
        session.add(thesis)
    else:
        thesis.title = title
        thesis.author_name = author_name
        thesis.year = year
        thesis.summary_ja = item.get("summary_ja", "") or thesis.summary_ja
        thesis.raw_labels = raw_labels
        if supervisor_name:
            thesis.supervisor_name = supervisor_name
        if lab_id:
            thesis.lab_id = lab_id

    await session.flush()
    return thesis.id, created


async def upsert_thesis_labels(session, thesis_id: int, item: dict, label_id_map: dict):
    """thesis_labels を再作成"""
    existing = await session.execute(select(ThesisLabel).where(ThesisLabel.thesis_id == thesis_id))
    for tl in existing.scalars().all():
        await session.delete(tl)

    confidence = item.get("confidence", "medium")
    for label_type, names in LABEL_TYPE_MAP.items():
        for name in (item.get(label_type) or []):
            label_id = label_id_map.get((label_type, name))
            if not label_id:
                continue
            session.add(ThesisLabel(thesis_id=thesis_id, label_id=label_id, confidence=confidence))

    await session.flush()


async def upsert_lab_labels(session, lab_id: int, item: dict, label_id_map: dict):
    """研究室ラベルに集計（既存はスキップ）"""
    confidence = item.get("confidence", "medium")
    for label_type in LABEL_TYPE_MAP:
        for name in (item.get(label_type) or []):
            label_id = label_id_map.get((label_type, name))
            if not label_id:
                continue
            existing = await session.execute(
                select(LabLabel).where(LabLabel.lab_id == lab_id, LabLabel.label_id == label_id)
            )
            if not existing.scalar_one_or_none():
                session.add(LabLabel(lab_id=lab_id, label_id=label_id, confidence=confidence))

    await session.flush()


async def main():
    if not os.path.exists(LABELS_JSON):
        print(f"{LABELS_JSON} が見つかりません。extract_labels_openai.py を先に実行してください。")
        return

    with open(THESES_JSON, encoding="utf-8") as f:
        theses_raw = {str(t["repo_id"]): t for t in json.load(f)}
    with open(LABELS_JSON, encoding="utf-8") as f:
        labels_data: dict[str, dict] = json.load(f)

    print(f"論文数: {len(labels_data)} 件")

    async with AsyncSessionLocal() as session:
        label_id_map = await load_label_id_map(session)
        teacher_lab_map = await build_teacher_lab_map(session)
        print(f"ラベル数: {len(label_id_map)} / 教員数: {len(teacher_lab_map) // 2}")

    created_count, updated_count, linked_count, errors = 0, 0, 0, 0

    for repo_id_str, item in labels_data.items():
        merged = {**theses_raw.get(repo_id_str, {}), **item}
        supervisor = merged.get("supervisor_name", "")

        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    thesis_id, created = await upsert_thesis(session, merged, label_id_map, teacher_lab_map)
                    await upsert_thesis_labels(session, thesis_id, merged, label_id_map)

                    # lab_id が設定できた場合は lab_labels も集計
                    t_result = await session.execute(select(Thesis).where(Thesis.id == thesis_id))
                    thesis = t_result.scalar_one_or_none()
                    lab_id = thesis.lab_id if thesis else None
                    if lab_id:
                        await upsert_lab_labels(session, lab_id, merged, label_id_map)
                        linked_count += 1

            action = "NEW" if created else "UPD"
            lab_info = f"→ {supervisor}" if supervisor else "（指導教員不明）"
            print(f"[{action}] {repo_id_str}: {merged.get('title','')[:40]} {lab_info}")

            if created:
                created_count += 1
            else:
                updated_count += 1

        except Exception as e:
            errors += 1
            print(f"[ERR] {repo_id_str}: {e}")

    print(f"\n=== 結果 ===")
    print(f"  新規: {created_count} / 更新: {updated_count} / 研究室紐付き: {linked_count} / エラー: {errors}")


if __name__ == "__main__":
    asyncio.run(main())
