# Claude並列作業ガイド

このドキュメントは複数のClaudeインスタンスが並列で作業するための引き継ぎ情報です。

## 作業開始前に必ず読むファイル

1. `docs/STATUS.md` — 現在のDB状態・実装済み機能
2. `docs/TASKS.md` — タスク一覧と優先度
3. このファイル — 環境・コマンド・ルール

## 環境

```bash
# アプリ起動確認
docker compose ps

# コード変更後の反映（テンプレートはホットリロード）
docker compose restart web

# マイグレーション実行
docker compose run --rm web alembic upgrade head

# スクリプト実行例
docker compose run --rm web python scripts/<script>.py

# DB確認（ブラウザ）
http://localhost:8080  # Adminer (user: ds_user / pass: ds_pass / db: ds_db)

# アプリ確認
http://localhost:8000
```

## 重要ファイル構成

```
app/
  models.py          # SQLAlchemyモデル（触る前に必ず確認）
  crud.py            # DB操作（複数タスクから参照、同時編集注意）
  routers/           # FastAPIルーター
  services/
    recommendation.py  # 推薦スコアリング
  templates/         # Jinja2テンプレート（HTMXあり）
scripts/
  crawl_repo_items.py     # 論文メタデータ取得
  crawl_teachers.py       # 教員情報取得
  download_pdfs.py        # PDF取得
  extract_labels_openai.py # OpenAI APIでラベル抽出（PDF直接渡し）
  import_to_db.py         # 論文・ラベルDB投入
  import_teachers_to_db.py # 教員・研究室DB投入
migrations/versions/  # Alembicマイグレーション
docs/                 # このディレクトリ
```

## 注意事項

- `OPENAI_API_KEY` は `.env` にのみ記載。コードに書かない
- `data/raw/pdfs/` はgitignore済み（117件のPDF）
- `data/processed/openai_labels.json` もgitignore済み
- DB変更はAlembicマイグレーション経由で行う
- `app/crud.py` の同時編集は避ける（競合リスク）

## タスク着手時のフロー

1. `docs/TASKS.md` で担当タスクを `[~]` に更新
2. 作業完了後に `[x]` に更新 + `docs/STATUS.md` の該当箇所を更新
3. git commit して develop ブランチにpush
