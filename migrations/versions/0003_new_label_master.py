"""new label master: modality-based data, add IoT, supervisor_name on theses

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# remap_labels.py / aggregate_thesis_labels.py の MASTER_LABELS と同じ名前を使う
NEW_METHOD_LABELS = [
    "機械学習・深層学習", "統計的モデリング", "自然言語処理",
    "画像処理・CV", "最適化", "時系列解析", "シミュレーション",
]
NEW_DATA_LABELS = [
    "テキスト・言語データ", "画像・映像データ", "時系列・センサーデータ",
    "音声データ", "医療・生体データ", "地理空間データ", "数値・表形式データ",
]
NEW_THEME_LABELS = [
    "機械学習", "統計・数理", "テキスト・言語処理", "画像・映像",
    "最適化", "医療・ヘルスケア", "社会・政策", "経済・ビジネス",
    "IoT・センサー・時系列", "空間・交通", "製造・農業・環境", "音楽・メディア・デザイン",
]


def upgrade():
    # supervisor_name カラムを theses に追加（既存カラムと重複しないよう確認）
    # すでに supervisor_name が存在する場合はスキップ
    conn = op.get_bind()
    cols = [r[0] for r in conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='theses'")
    )]
    if "supervisor_name" not in cols:
        op.add_column("theses", sa.Column("supervisor_name", sa.String(200), nullable=True))

    # programming_language を theses に追加
    if "programming_language" not in cols:
        op.add_column("theses", sa.Column("programming_language", sa.ARRAY(sa.Text()), nullable=True))

    # ラベル関連テーブルをリセット（依存順に）
    conn.execute(sa.text("TRUNCATE TABLE lab_evidence RESTART IDENTITY CASCADE"))
    conn.execute(sa.text("TRUNCATE TABLE lab_labels RESTART IDENTITY CASCADE"))
    conn.execute(sa.text("TRUNCATE TABLE thesis_labels RESTART IDENTITY CASCADE"))
    conn.execute(sa.text("TRUNCATE TABLE labels RESTART IDENTITY CASCADE"))

    # 新ラベルマスタを挿入
    for name in NEW_METHOD_LABELS:
        conn.execute(sa.text("INSERT INTO labels (label_type, name) VALUES ('method', :n)"), {"n": name})
    for name in NEW_DATA_LABELS:
        conn.execute(sa.text("INSERT INTO labels (label_type, name) VALUES ('data', :n)"), {"n": name})
    for name in NEW_THEME_LABELS:
        conn.execute(sa.text("INSERT INTO labels (label_type, name) VALUES ('theme', :n)"), {"n": name})


def downgrade():
    pass
