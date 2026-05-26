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

NEW_METHOD_LABELS = [
    "深層学習", "統計モデリング", "時系列解析",
    "自然言語処理", "コンピュータビジョン", "ベイズ手法",
    "強化学習", "因果推論", "最適化", "ネットワーク分析", "データ同化",
]
NEW_DATA_LABELS = [
    "画像・映像", "音声", "テキスト", "時系列・センサー",
    "数値・表形式", "地理空間", "IoT",
]
NEW_THEME_LABELS = [
    "製造・ものづくり", "医療・ヘルスケア", "農業・自然科学",
    "教育", "経済・金融", "社会・政策", "スポーツ",
    "マーケティング・消費", "交通・インフラ", "音楽・メディア",
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
