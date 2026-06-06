# 滋賀大学 研究室探索アプリ

滋賀大学データサイエンス研究科の修士論文データをもとに、研究室の研究テーマ・手法・使用データを可視化し、興味に合った研究室を探せるWebアプリです。

**デモ:** https://shiga-lab-recommend-production.up.railway.app

---

## 背景・課題

- 大学の論文リポジトリと研究室が紐づいておらず、自分の興味に合う研究室を探すのに時間がかかる
- 各研究室がどんなデータや手法を扱っているかが外部からわかりにくい

これらの課題を解決するため、令和2〜6年度の修士論文117件を収集・整形し、研究室と紐づけてデータベース化しました。

---

## 主な機能

| 機能 | 説明 |
|---|---|
| **研究室一覧** | ラベル（手法・データ・テーマ）で絞り込み・グループ表示 |
| **探索ページ** | データ種別・手法・研究テーマ別に研究室をカテゴリ表示、ラベルチップで絞り込み |
| **キーワード検索** | 同義語展開付きの全文検索 |
| **レコメンド** | 興味のあるラベルを選ぶと適合スコア付きで研究室を推薦 |
| **管理画面** | 研究室・論文・ラベルのCRUD、検索ログ・フィードバックの確認 |

---

## 技術スタック

| カテゴリ | 使用技術 |
|---|---|
| Backend | Python 3.12 / FastAPI / SQLAlchemy (async) |
| Database | PostgreSQL (asyncpg) / Alembic |
| Frontend | Jinja2 / Tailwind CSS / HTMX |
| Infrastructure | Docker / Railway |
| Data収集 | OpenAI API（論文からのラベル抽出） |

---

## データ構成

```
修士論文 (117件)
 └─ 研究室 (59室) に紐づく
     └─ ラベルマスタ (26種) に紐づく
         ├─ 手法 (機械学習・深層学習、統計的モデリング 等)
         ├─ データ種別 (画像・映像データ、時系列・センサーデータ 等)
         └─ 研究テーマ (製造・農業・環境、医療・ヘルスケア 等)
```

---

## ローカル起動

```bash
docker compose up --build
```

| URL | 用途 |
|---|---|
| http://localhost:8000 | アプリ本体 |
| http://localhost:8080 | DB管理画面 (Adminer) |

### 環境変数

`.env.example` をコピーして `.env` を作成してください。

```bash
cp .env.example .env
```

---

## プロジェクト構成

```
.
├── app/
│   ├── main.py           # FastAPIアプリ本体
│   ├── models.py         # SQLAlchemyモデル
│   ├── crud.py           # DB操作
│   ├── config.py         # 設定管理
│   ├── routers/          # エンドポイント
│   ├── services/         # ビジネスロジック（検索・レコメンド）
│   ├── templates/        # Jinja2テンプレート
│   └── static/           # CSS・JS
├── migrations/           # Alembicマイグレーション
├── scripts/              # データ収集・整形スクリプト
├── tests/                # テスト
├── Dockerfile
├── docker-compose.yml
└── railway.toml
```

---

## 画面構成

- `/` — トップページ
- `/labs` — 研究室一覧（ラベル絞り込み）
- `/explore` — カテゴリ別探索・ラベルフィルター
- `/search` — キーワード検索
- `/recommend` — レコメンドフォーム・結果
- `/admin` — 管理画面（要認証）
