"""
thesis_labels を研究室ごとに集計して lab_labels を補完する。
2段階で処理する:
  Step 1 - タイトルパターンマッチ: thesis.title を MASTER_LABELS のパターンで照合し
           thesis_labels に追加（重複スキップ）
  Step 2 - 頻度集計: thesis_labels を研究室単位で集計し lab_labels に反映

confidence の基準:
  high   : 研究室の全論文の 50% 以上で出現
  medium : 1件以上で出現

実行: docker compose run --rm web python scripts/aggregate_thesis_labels.py
"""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from collections import Counter
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Lab, Thesis, ThesisLabel, LabLabel, Label

MASTER_LABELS = {
    "method": [
        {"name": "機械学習・深層学習",  "patterns": ["機械学習", "深層学習", "強化学習", "転移学習", "弱教師", "ニューラル", "知能情報", "スパースモデリング", "表現学習", "ディープ", "CNN", "RNN", "LSTM", "Transformer", "GAN", "BERT", "GPT"]},
        # "分類" は画像分類・文書分類など他手法と重複するため除外
        {"name": "統計的モデリング",    "patterns": ["統計", "数理統計", "ベイズ", "因果推論", "多変量", "計算代数", "確率", "回帰", "クラスタリング"]},
        {"name": "自然言語処理",        "patterns": ["自然言語", "テキスト", "言語処理", "情報検索", "文書", "文章", "感情分析", "固有表現", "要約", "翻訳", "NLP"]},
        {"name": "画像処理・CV",        "patterns": ["画像", "映像", "コンピュータビジョン", "ビジョン", "三次元", "仮想", "複合現実", "物体検出", "セグメンテーション", "顔認識", "医用画像"]},
        {"name": "最適化",              "patterns": ["最適化", "オペレーションズ", "在庫管理", "実験計画", "組合せ", "スケジューリング", "配送", "ルーティング"]},
        {"name": "時系列解析",          "patterns": ["時系列", "非線形時系列", "変化点", "信号処理", "異常検知", "状態空間", "ARIMA", "需要予測", "電力予測", "売上予測"]},
        {"name": "シミュレーション",    "patterns": ["シミュレーション", "数値計算", "力学系", "非線形力学", "パターン形成", "データ同化", "数値天気予報", "エージェント"]},
    ],
    "data": [
        {"name": "テキスト・言語データ",      "patterns": ["テキスト", "自然言語", "言語", "音声言語", "文書", "コーパス"]},
        {"name": "画像・映像データ",          "patterns": ["画像", "映像", "医用画像", "衛星画像", "動画"]},
        {"name": "時系列・センサーデータ",    "patterns": ["時系列", "センサ", "IoT", "サイバーフィジカル", "加速度", "振動", "心拍", "脳波", "ECG"]},
        {"name": "音声データ",                "patterns": ["音声", "音楽", "楽曲", "アコースティック", "メル"]},
        # "神経"・"脳" はニューラルネットワーク文脈で誤検知するため除外
        {"name": "医療・生体データ",          "patterns": ["医療", "医学", "疫学", "ゲノム", "臨床", "バイオ", "遺伝子", "タンパク質", "細胞", "患者", "診断"]},
        # "空間"→"地理空間"（状態空間モデルとの混同防止）、"地域"除外（広義すぎる）
        {"name": "地理空間データ",            "patterns": ["地理空間", "地理情報", "気象", "交通量", "都市計画", "GIS", "GPS", "位置情報", "地図", "地形"]},
        {"name": "数値・表形式データ",        "patterns": ["数値", "統計調査", "公的統計", "経済統計", "アンケート", "標本", "社会調査", "マイクロデータ"]},
    ],
    "theme": [
        {"name": "機械学習",              "patterns": ["機械学習", "深層学習", "強化学習", "転移学習", "弱教師", "ニューラル", "データサイエンス", "データ科学", "データ駆動", "ビッグデータ"]},
        # "非線形" は非線形力学(シミュレーション)・非線形時系列(時系列解析)と重複するため除外
        {"name": "統計・数理",            "patterns": ["統計", "数理", "確率", "ベイズ", "因果推論", "多変量", "計算代数", "力学系", "数値計算"]},
        {"name": "テキスト・言語処理",    "patterns": ["テキスト", "自然言語", "音声", "情報検索", "言語処理"]},
        {"name": "画像・映像",            "patterns": ["画像", "映像", "コンピュータビジョン", "ビジョン", "AR", "VR", "仮想", "複合現実", "三次元"]},
        {"name": "最適化",                "patterns": ["最適化", "オペレーションズ", "在庫管理", "実験計画", "組合せ"]},
        # "神経"・"脳" はニューラルネットワーク文脈で誤検知するため除外
        {"name": "医療・ヘルスケア",      "patterns": ["医療", "医学", "疫学", "臨床", "バイオ", "ゲノム", "健康", "QOL", "患者", "診断", "医薬"]},
        # "調査" は広義すぎる（統計調査・アンケート調査など）ため除外
        {"name": "社会・政策",            "patterns": ["社会", "政策", "犯罪", "教育", "EBPM", "心理", "障がい", "ナッジ", "公共", "福祉"]},
        {"name": "経済・ビジネス",        "patterns": ["経済", "金融", "マーケティング", "消費者", "ビジネス", "財政", "株価", "為替"]},
        # "ネットワーク" はニューラルネットワークと混同するため除外
        {"name": "IoT・センサー・時系列", "patterns": ["IoT", "センサ", "時系列", "サイバーフィジカル", "ユビキタス", "プライバシー", "スマートメーター"]},
        # "空間"→"地理空間"（状態空間モデルとの混同防止）、"地域"除外
        {"name": "空間・交通",            "patterns": ["地理空間", "地理情報", "交通流", "交通量", "都市計画", "気象予測", "災害", "データ同化", "環境評価", "脱炭素", "GIS"]},
        {"name": "製造・農業・環境",      "patterns": ["製造", "農業", "品質管理", "ライフサイクル", "作物", "収量", "土壌"]},
        {"name": "音楽・メディア・デザイン", "patterns": ["音楽", "メディア", "デザイン", "ロボット", "作曲", "演奏", "コミュニケーション"]},
    ],
}


def match_title(title: str) -> dict[str, list[str]]:
    """タイトルに含まれるパターンをマスターラベルに対応させる。"""
    matched: dict[str, list[str]] = {"method": [], "data": [], "theme": []}
    for ltype, masters in MASTER_LABELS.items():
        for master in masters:
            for pattern in master["patterns"]:
                if pattern in title:
                    if master["name"] not in matched[ltype]:
                        matched[ltype].append(master["name"])
                    break
    return matched


async def step1_title_match(session) -> int:
    """タイトルパターンマッチで thesis_labels を補完する。"""
    label_map = {
        (l.label_type, l.name): l.id
        for l in (await session.execute(select(Label))).scalars().all()
    }

    theses = (await session.execute(select(Thesis))).scalars().all()
    added = 0

    existing_tl = set(
        (r.thesis_id, r.label_id)
        for r in (await session.execute(select(ThesisLabel))).scalars().all()
    )

    for thesis in theses:
        if not thesis.title:
            continue
        matches = match_title(thesis.title)

        raw = thesis.raw_labels or {}
        for raw_term in (raw.get("method_raw") or []) + (raw.get("data_raw") or []):
            for ltype in ["method", "data", "theme"]:
                for master in MASTER_LABELS[ltype]:
                    for pattern in master["patterns"]:
                        if pattern in raw_term and master["name"] not in matches[ltype]:
                            matches[ltype].append(master["name"])

        for ltype, names in matches.items():
            for name in names:
                label_id = label_map.get((ltype, name))
                if not label_id:
                    continue
                if (thesis.id, label_id) not in existing_tl:
                    session.add(ThesisLabel(
                        thesis_id=thesis.id,
                        label_id=label_id,
                        confidence="medium",
                    ))
                    existing_tl.add((thesis.id, label_id))
                    added += 1

    await session.flush()
    print(f"Step1: thesis_labels に {added} 件追加（タイトル・raw_labelsマッチ）")
    return added


async def step2_aggregate(session) -> tuple[int, int]:
    """thesis_labels を研究室単位で集計して lab_labels を更新する。"""
    labs = (await session.execute(select(Lab))).scalars().all()
    total_added = 0
    total_updated = 0
    rank = {"high": 2, "medium": 1, "low": 0}

    for lab in labs:
        theses = (await session.execute(
            select(Thesis).where(Thesis.lab_id == lab.id)
        )).scalars().all()

        if not theses:
            continue

        thesis_count = len(theses)
        thesis_ids = [t.id for t in theses]

        rows = (await session.execute(
            select(ThesisLabel.label_id)
            .where(ThesisLabel.thesis_id.in_(thesis_ids))
        )).all()

        if not rows:
            continue

        freq: Counter = Counter(r.label_id for r in rows)

        for label_id, count in freq.items():
            confidence = "high" if count / thesis_count >= 0.5 else "medium"

            existing = (await session.execute(
                select(LabLabel).where(
                    LabLabel.lab_id == lab.id,
                    LabLabel.label_id == label_id,
                )
            )).scalar_one_or_none()

            if existing is None:
                session.add(LabLabel(
                    lab_id=lab.id,
                    label_id=label_id,
                    confidence=confidence,
                ))
                total_added += 1
            elif existing.confidence != confidence:
                # 双方向更新（旧閾値のhighをmediumに格下げする場合も含む）
                existing.confidence = confidence
                total_updated += 1

        label_ids_sorted = sorted(freq, key=lambda x: freq[x], reverse=True)[:5]
        label_names = []
        for lid in label_ids_sorted:
            label = (await session.execute(
                select(Label).where(Label.id == lid)
            )).scalar_one_or_none()
            if label:
                label_names.append(f"{label.name}({freq[lid]})")
        print(f"  [{lab.name}] 論文{thesis_count}件 → {', '.join(label_names)}")

    await session.flush()
    return total_added, total_updated


async def main():
    async with AsyncSessionLocal() as session:
        print("=== Step 1: タイトル・raw_labels パターンマッチ ===")
        await step1_title_match(session)

        print("\n=== Step 2: thesis_labels → lab_labels 頻度集計 ===")
        added, updated = await step2_aggregate(session)

        await session.commit()
        print(f"\n=== 完了 ===")
        print(f"  lab_labels 追加: {added} 件 / 更新: {updated} 件")


if __name__ == "__main__":
    asyncio.run(main())
