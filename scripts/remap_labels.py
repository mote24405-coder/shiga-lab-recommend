"""
ラベルを手法・データ・テーマの3カテゴリで再構築する。
  手法: 7種  データ: 7種  テーマ: 12種
実行: docker compose run --rm web python scripts/remap_labels.py
"""
import json, os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import delete, select
from app.database import AsyncSessionLocal
from app.models import Lab, Label, LabLabel, LabEvidence, ThesisLabel
from sqlalchemy import union

TEACHERS_JSON = "data/raw/teachers.json"

MASTER_LABELS = {
    "method": [
        {"name": "機械学習・深層学習",  "patterns": ["機械学習", "深層学習", "強化学習", "転移学習", "弱教師", "ニューラル", "知能情報", "スパースモデリング", "表現学習"]},
        {"name": "統計的モデリング",    "patterns": ["統計", "数理統計", "ベイズ", "因果推論", "多変量", "計算代数", "確率"]},
        {"name": "自然言語処理",        "patterns": ["自然言語", "テキスト", "言語処理", "情報検索"]},
        {"name": "画像処理・CV",        "patterns": ["画像", "映像", "コンピュータビジョン", "ビジョン", "三次元", "仮想", "複合現実"]},
        {"name": "最適化",              "patterns": ["最適化", "オペレーションズ", "在庫管理", "実験計画", "組合せ"]},
        {"name": "時系列解析",          "patterns": ["時系列", "非線形時系列", "変化点", "信号処理"]},
        {"name": "シミュレーション",    "patterns": ["シミュレーション", "数値計算", "力学系", "非線形力学", "パターン形成", "データ同化", "数値天気予報"]},
    ],
    "data": [
        {"name": "テキスト・言語データ",      "patterns": ["テキスト", "自然言語", "言語", "音声言語"]},
        {"name": "画像・映像データ",          "patterns": ["画像", "映像", "医用画像"]},
        {"name": "時系列・センサーデータ",    "patterns": ["時系列", "センサ", "IoT", "サイバーフィジカル"]},
        {"name": "音声データ",                "patterns": ["音声", "音楽"]},
        {"name": "医療・生体データ",          "patterns": ["医療", "医学", "疫学", "ゲノム", "神経", "脳", "臨床", "バイオ"]},
        {"name": "地理空間データ",            "patterns": ["地理", "空間", "気象", "交通", "地域", "都市"]},
        {"name": "数値・表形式データ",        "patterns": ["数値", "統計調査", "公的統計", "経済統計", "アンケート", "標本", "社会調査"]},
    ],
    "theme": [
        {"name": "機械学習",              "patterns": ["機械学習", "深層学習", "強化学習", "転移学習", "弱教師", "ニューラル", "データサイエンス", "データ科学", "データ駆動", "ビッグデータ", "知能情報", "スパースモデリング", "表現学習", "コンティニュアル"]},
        {"name": "統計・数理",            "patterns": ["統計", "数理", "確率", "ベイズ", "因果推論", "多変量", "計算代数", "力学系", "非線形", "数値計算", "離散", "符号", "情報科学", "理論計算機", "物理学", "宇宙"]},
        {"name": "テキスト・言語処理",    "patterns": ["テキスト", "自然言語", "音声", "情報検索", "言語処理"]},
        {"name": "画像・映像",            "patterns": ["画像", "映像", "コンピュータビジョン", "ビジョン", "AR", "VR", "仮想", "複合現実", "三次元"]},
        {"name": "最適化",                "patterns": ["最適化", "オペレーションズ", "在庫管理", "実験計画", "組合せ"]},
        {"name": "医療・ヘルスケア",      "patterns": ["医療", "医学", "疫学", "臨床", "バイオ", "ゲノム", "神経", "脳", "健康", "QOL", "テスト理論", "項目反応", "構造生物"]},
        {"name": "社会・政策",            "patterns": ["社会", "政策", "犯罪", "教育", "EBPM", "調査", "心理", "障がい", "ナッジ", "公共"]},
        {"name": "経済・ビジネス",        "patterns": ["経済", "金融", "マーケティング", "消費者", "ビジネス", "財政"]},
        {"name": "IoT・センサー・時系列", "patterns": ["IoT", "センサ", "時系列", "サイバーフィジカル", "ユビキタス", "ネットワーク", "プライバシー"]},
        {"name": "空間・交通",            "patterns": ["空間", "交通", "地理", "都市", "地域", "気象", "災害", "データ同化", "環境評価", "脱炭素"]},
        {"name": "製造・農業・環境",      "patterns": ["製造", "農業", "品質管理", "ライフサイクル"]},
        {"name": "音楽・メディア・デザイン", "patterns": ["音楽", "メディア", "デザイン", "ロボット", "作曲", "演奏", "コミュニケーション"]},
    ],
}


def match_to_masters(term: str, label_type: str) -> list[str]:
    matched = []
    for master in MASTER_LABELS[label_type]:
        for pattern in master["patterns"]:
            if pattern in term:
                matched.append(master["name"])
                break
    return matched


async def main():
    if not os.path.exists(TEACHERS_JSON):
        print(f"{TEACHERS_JSON} が見つかりません")
        return

    with open(TEACHERS_JSON, encoding="utf-8") as f:
        teachers_data = json.load(f)

    # Step1: 全ラベル関連をクリアして再投入
    master_map: dict[tuple[str, str], int] = {}  # (type, name) -> id
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # official_site 由来のみ削除（論文由来データは保持）
            await session.execute(
                delete(LabEvidence).where(LabEvidence.source_type == "official_site")
            )
            # official_site 由来の lab_labels を特定して削除
            from sqlalchemy import text
            await session.execute(text("""
                DELETE FROM lab_labels
                WHERE id IN (
                    SELECT DISTINCT ll.id FROM lab_labels ll
                    JOIN lab_evidence le ON le.lab_id = ll.lab_id AND le.label_id = ll.label_id
                    WHERE le.source_type = 'official_site'
                )
            """))
            # thesis_labels・lab_labels どちらにも参照されていないラベルのみ削除
            referenced = union(
                select(ThesisLabel.label_id),
                select(LabLabel.label_id),
            )
            await session.execute(
                delete(Label).where(~Label.id.in_(referenced))
            )
            print("official_site 由来のラベル・lab_labels・lab_evidenceをクリア（論文データは保持）")

            # MASTER_LABELS にまだ存在しないラベルのみ追加
            existing_labels = {
                (l.label_type, l.name): l.id
                for l in (await session.execute(select(Label))).scalars().all()
            }
            total_inserted = 0
            for label_type, masters in MASTER_LABELS.items():
                for m in masters:
                    key = (label_type, m["name"])
                    if key in existing_labels:
                        master_map[key] = existing_labels[key]
                    else:
                        label = Label(label_type=label_type, name=m["name"])
                        session.add(label)
                        await session.flush()
                        master_map[key] = label.id
                        total_inserted += 1

            print(f"ラベル新規挿入: {total_inserted} 件 / 既存利用: {len(master_map) - total_inserted} 件")

    # Step2: 教員ごとにlab_labelsを付与
    total = 0
    no_match = []

    for teacher_data in teachers_data:
        name = teacher_data.get("name", "")
        if not name:
            continue

        terms = list(dict.fromkeys(
            (teacher_data.get("specialties") or []) +
            (teacher_data.get("keywords") or [])
        ))

        matched: dict[str, set[str]] = {"method": set(), "data": set(), "theme": set()}
        for term in terms:
            for ltype in ["method", "data", "theme"]:
                for master_name in match_to_masters(term, ltype):
                    matched[ltype].add(master_name)

        all_matched = matched["method"] | matched["data"] | matched["theme"]
        if not all_matched:
            no_match.append(name)
            continue

        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(Lab).where(Lab.name == f"{name}研究室")
                )
                lab = result.scalar_one_or_none()
                if not lab:
                    continue

                for ltype, names in matched.items():
                    for master_name in sorted(names):
                        label_id = master_map[(ltype, master_name)]
                        # 既存の lab_labels はスキップ（import_to_db.py が作成済みの場合）
                        exists = (await session.execute(
                            select(LabLabel).where(
                                LabLabel.lab_id == lab.id,
                                LabLabel.label_id == label_id,
                            )
                        )).scalar_one_or_none()
                        if not exists:
                            session.add(LabLabel(lab_id=lab.id, label_id=label_id, confidence="high"))
                        session.add(LabEvidence(
                            lab_id=lab.id,
                            label_id=label_id,
                            evidence_text=", ".join(terms[:5]),
                            evidence_url=teacher_data.get("profile_url"),
                            source_type="official_site",
                            confidence="high",
                        ))
                        total += 1

        summary = []
        for ltype, lname in [("method", "手法"), ("data", "データ"), ("theme", "テーマ")]:
            if matched[ltype]:
                summary.append(f"{lname}:{','.join(sorted(matched[ltype]))}")
        print(f"  [{name}] {' / '.join(summary)}")

    print(f"\n=== 完了 ===")
    print(f"  lab_labels 追加: {total} 件")
    if no_match:
        print(f"  マッチなし ({len(no_match)} 名): {', '.join(no_match)}")


if __name__ == "__main__":
    asyncio.run(main())
