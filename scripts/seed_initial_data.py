"""
サンプルデータをDBに投入するスクリプト。
実行: docker compose run --rm web python scripts/seed_initial_data.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Lab, Teacher, Label, LabLabel, Thesis, ThesisLabel, LabEvidence, SurveyQuestion, SearchSynonym
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.sync_database_url)

# テーブル作成（alembicを使う場合は不要だが、単独実行時のため）
Base.metadata.create_all(engine)


def seed():
    with Session(engine) as session:
        # すでにデータがある場合はスキップ
        if session.query(Lab).count() > 0:
            print("データが既に存在します。スキップします。")
            return

        # ── ラベルマスタ ─────────────────────────────────
        label_defs = {
            "method": [
                "機械学習", "深層学習", "統計モデリング", "因果推論", "時系列解析",
                "画像処理", "自然言語処理", "最適化", "ネットワーク分析", "ベイズ統計", "データ同化",
            ],
            "data": [
                "医療データ", "画像データ", "テキストデータ", "音声データ", "交通データ",
                "金融データ", "マーケティングデータ", "教育データ", "犯罪・社会調査データ",
                "気象データ", "公的統計", "企業データ",
            ],
            "theme": [
                "医療AI", "マーケティング", "都市・交通", "防災", "教育",
                "心理", "犯罪", "経済", "スポーツ", "音楽情報処理", "社会課題解決",
            ],
        }
        labels: dict[str, Label] = {}
        for ltype, names in label_defs.items():
            for name in names:
                lb = Label(label_type=ltype, name=name)
                session.add(lb)
                labels[name] = lb
        session.flush()

        # ── サンプル研究室 ────────────────────────────────
        labs_data = [
            {
                "name": "田中研究室",
                "description": "医療データを用いた機械学習・深層学習の研究。電子カルテや医用画像から疾患予測モデルを構築する。",
                "official_url": "https://www.ds.shiga-u.ac.jp/member/",
                "method": ["機械学習", "深層学習", "統計モデリング"],
                "data": ["医療データ", "画像データ"],
                "theme": ["医療AI"],
                "teacher": {"name": "田中 太郎", "specialties": ["機械学習", "医療情報学"]},
                "theses": [
                    {"title": "電子カルテを用いた入院期間予測モデルの構築", "year": 2023, "author_name": "山田 花子"},
                    {"title": "医用画像に基づく疾患スクリーニング手法の開発", "year": 2022, "author_name": "鈴木 一郎"},
                ],
                "evidence": [
                    {"label": "機械学習", "text": "公式ページに「機械学習を用いた医療データ分析」と記載。", "source_type": "official_site", "confidence": "high"},
                ],
            },
            {
                "name": "鈴木研究室",
                "description": "自然言語処理とテキストマイニングの研究。SNSやニュース記事から社会動向を分析する。LLMの応用研究も行う。",
                "official_url": "https://www.ds.shiga-u.ac.jp/member/",
                "method": ["自然言語処理", "機械学習"],
                "data": ["テキストデータ", "公的統計"],
                "theme": ["社会課題解決", "マーケティング"],
                "teacher": {"name": "鈴木 次郎", "specialties": ["自然言語処理", "情報検索"]},
                "theses": [
                    {"title": "BERTを用いたSNSの感情分析と社会動向の予測", "year": 2023, "author_name": "佐藤 三郎"},
                    {"title": "企業レビューテキストからの消費者満足度推定", "year": 2022, "author_name": "高橋 四郎"},
                ],
                "evidence": [
                    {"label": "自然言語処理", "text": "研究室サイトに「NLP・テキストマイニング」とある。", "source_type": "lab_site", "confidence": "high"},
                ],
            },
            {
                "name": "中村研究室",
                "description": "因果推論と統計モデリングを専門とする。医療・政策・教育分野での介入効果推定に取り組む。",
                "official_url": "https://www.ds.shiga-u.ac.jp/member/",
                "method": ["因果推論", "統計モデリング", "ベイズ統計"],
                "data": ["医療データ", "公的統計", "教育データ"],
                "theme": ["医療AI", "教育", "経済"],
                "teacher": {"name": "中村 五郎", "specialties": ["因果推論", "統計学"]},
                "theses": [
                    {"title": "傾向スコアを用いた医療介入効果の推定", "year": 2023, "author_name": "伊藤 六花"},
                    {"title": "差の差分析による教育政策評価", "year": 2022, "author_name": "渡辺 七海"},
                ],
                "evidence": [
                    {"label": "因果推論", "text": "論文タイトルに「傾向スコア」「介入効果」が多数含まれる。", "source_type": "thesis_title", "confidence": "high"},
                ],
            },
            {
                "name": "小林研究室",
                "description": "交通・都市データを活用したモビリティ解析。GPS・位置情報データを用いた移動行動分析と需要予測。",
                "official_url": "https://www.ds.shiga-u.ac.jp/member/",
                "method": ["機械学習", "最適化", "時系列解析"],
                "data": ["交通データ", "公的統計"],
                "theme": ["都市・交通", "社会課題解決"],
                "teacher": {"name": "小林 八重", "specialties": ["交通工学", "空間統計"]},
                "theses": [
                    {"title": "GPSデータを用いた通勤行動パターンの分析", "year": 2023, "author_name": "加藤 九郎"},
                    {"title": "公共交通需要の時系列予測モデル", "year": 2022, "author_name": "松本 十子"},
                ],
                "evidence": [
                    {"label": "交通データ", "text": "論文に「GPSデータ」「交通需要」が頻出。", "source_type": "thesis_title", "confidence": "high"},
                ],
            },
            {
                "name": "吉田研究室",
                "description": "スポーツデータサイエンス。選手のパフォーマンス分析、戦術データ分析、音楽情報処理も研究対象。",
                "official_url": "https://www.ds.shiga-u.ac.jp/member/",
                "method": ["機械学習", "統計モデリング", "画像処理"],
                "data": ["企業データ", "音声データ"],
                "theme": ["スポーツ", "音楽情報処理"],
                "teacher": {"name": "吉田 十一", "specialties": ["スポーツ科学", "データ分析"]},
                "theses": [
                    {"title": "野球の打撃データを用いたパフォーマンス予測モデル", "year": 2023, "author_name": "山口 十二"},
                    {"title": "音楽特徴量によるジャンル分類の深層学習アプローチ", "year": 2022, "author_name": "井上 十三"},
                ],
                "evidence": [
                    {"label": "スポーツ", "text": "公式ページに「スポーツデータ分析」と記載。", "source_type": "official_site", "confidence": "high"},
                ],
            },
        ]

        for ld in labs_data:
            lab = Lab(
                name=ld["name"],
                slug=ld["name"].replace(" ", "_"),
                description=ld["description"],
                official_url=ld.get("official_url"),
            )
            session.add(lab)
            session.flush()

            teacher_data = ld["teacher"]
            teacher = Teacher(
                lab_id=lab.id,
                name=teacher_data["name"],
                specialties=teacher_data.get("specialties", []),
                profile_url=ld.get("official_url"),
            )
            session.add(teacher)

            for label_name in ld.get("method", []):
                if label_name in labels:
                    session.add(LabLabel(lab_id=lab.id, label_id=labels[label_name].id, confidence="high"))
            for label_name in ld.get("data", []):
                if label_name in labels:
                    session.add(LabLabel(lab_id=lab.id, label_id=labels[label_name].id, confidence="high"))
            for label_name in ld.get("theme", []):
                if label_name in labels:
                    session.add(LabLabel(lab_id=lab.id, label_id=labels[label_name].id, confidence="medium"))

            for td in ld.get("theses", []):
                thesis = Thesis(
                    lab_id=lab.id,
                    title=td["title"],
                    year=td.get("year"),
                    author_name=td.get("author_name"),
                    supervisor_name=teacher_data["name"],
                    repo_url="https://shiga-u.repo.nii.ac.jp/search?page=1&size=20&sort=controlnumber&search_type=2&q=1873",
                )
                session.add(thesis)

            for ev in ld.get("evidence", []):
                label_obj = labels.get(ev["label"])
                session.add(LabEvidence(
                    lab_id=lab.id,
                    label_id=label_obj.id if label_obj else None,
                    evidence_text=ev["text"],
                    source_type=ev["source_type"],
                    confidence=ev["confidence"],
                    evidence_url=ld.get("official_url"),
                ))

        # ── アンケート質問 ───────────────────────────────
        survey_questions = [
            # 推薦結果フィードバック
            {"survey_type": "recommendation", "question_text": "この推薦結果は役に立ちましたか？", "question_format": "scale", "display_order": 1},
            {"survey_type": "recommendation", "question_text": "自分の興味に合っていると感じましたか？", "question_format": "scale", "display_order": 2},
            {"survey_type": "recommendation", "question_text": "不適切だと思うラベルや推薦理由があれば教えてください。", "question_format": "text", "display_order": 3},
            # 利用後アンケート
            {"survey_type": "post_use", "question_text": "このアプリは研究室選びの参考になりましたか？", "question_format": "scale", "display_order": 1},
            {"survey_type": "post_use", "question_text": "研究室ごとの違いを理解しやすくなりましたか？", "question_format": "scale", "display_order": 2},
            {"survey_type": "post_use", "question_text": "手法・データ・テーマのラベルは分かりやすかったですか？", "question_format": "scale", "display_order": 3},
            {"survey_type": "post_use", "question_text": "根拠情報は役に立ちましたか？", "question_format": "scale", "display_order": 4},
            {"survey_type": "post_use", "question_text": "改善してほしい点や追加してほしい機能はありますか？", "question_format": "text", "display_order": 5},
        ]
        for sq in survey_questions:
            session.add(SurveyQuestion(**sq))

        # ── 同義語辞書 ───────────────────────────────────
        from app.services.search_synonyms import DEFAULT_SYNONYMS
        for term, synonyms in DEFAULT_SYNONYMS.items():
            session.add(SearchSynonym(term=term, synonyms=synonyms))

        session.commit()
        print(f"シードデータを投入しました。研究室 {len(labs_data)} 件。")


if __name__ == "__main__":
    seed()
