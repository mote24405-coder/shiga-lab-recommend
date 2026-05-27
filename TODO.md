# TODO / チケット一覧

最終更新: 2026-05-26

## 凡例
- [ ] 未着手
- [x] 完了
- [~] 進行中

---

## Phase 0: 基盤構築 ✅
- [x] ディレクトリ構成・git init
- [x] Dockerfile (Python 3.12 + uv)
- [x] docker-compose.yml (PostgreSQL + web)
- [x] SQLAlchemy モデル設計 (16テーブル)
- [x] Alembic マイグレーション (0001_initial)
- [x] サンプルシードデータ (5研究室)
- [x] FastAPI アプリ起動確認
- [x] GitHub リポジトリ作成・push (mote24405-coder/laboratory-recommend)

---

## Phase 1: MVPウェブアプリ 🔄

### ルーター・テンプレート
- [x] トップページ (/)
- [x] 研究室一覧 (/labs) + HTMXラベル絞り込み
- [x] 研究室詳細 (/labs/:id)
- [x] 研究室比較 (/labs/compare)
- [x] キーワード検索 (/search) + 同義語展開
- [x] 推薦フォーム (/recommend)
- [x] 推薦結果 (/recommend/:run_id) + フィードバック
- [x] アンケート (/surveys)
- [x] 管理画面 (/admin)

### 未対応
- [x] 検索ログのDB保存にトランザクション修正 (search.py)
- [ ] /labs/partial の HX-Request ヘッダ対応確認
- [ ] 静的ファイル (app/static) 空ディレクトリ確認
- [ ] pytest 実行確認

---

## Phase 2: データ収集パイプライン 🔄

### スクレイピング
- [x] scripts/crawl_teachers.py (雛形)
- [x] scripts/crawl_repo_items.py (令和2〜6年度, WEKO3 JSON API)
- [x] PDF URL の取得ロジック (crawl_repo_items.py 内)
- [x] scripts/download_pdfs.py (レート制限・403スキップ対応)

### テキスト抽出・ラベル付け
- [x] scripts/extract_labels_rule_based.py
- [x] scripts/extract_pdf_text.py (pypdf, 先頭5ページ)
- [x] scripts/extract_labels_openai.py (gpt-4o-mini, raw+normalized)

### DB取り込み
- [x] scripts/import_to_db.py (upsert, 教員名マッチング, lab_evidence)
- [ ] **実際に import_to_db.py を実行してデータ投入** ← 次

---

## Phase 3: ラベル設計・精度向上

### ラベル設計
- [x] OpenAI抽出の raw_labels テーブル追加 (migration 0002)
- [x] ラベル正規化マッピング辞書 (raw → master) — openai_labels.json内
- [ ] 管理画面でラベル承認フロー

### 検索精度
- [ ] pg_trgm 拡張インストール (migration 0003)
- [ ] 類似文字列インデックス追加

### ラベル精度
- [x] フィルタパネルを「研究室に紐づくラベルのみ」表示に修正 (crud.get_labels used_only)
- [x] scripts/aggregate_thesis_labels.py — thesis_labels の出現頻度で lab_labels を補完
      実行: docker compose run --rm web python scripts/aggregate_thesis_labels.py
- [ ] **[TODO] 埋め込みベースのラベル付け（将来）**
      各論文の abstract/summary_ja を text-embedding-3-small でベクトル化し、
      ラベル定義文との cosine 類似度で lab_labels を自動更新する。
      研究室ベクトル = 所属論文ベクトルの平均（重み付け可）。
      実装コストが高いため import_to_db.py + aggregate_thesis_labels.py の精度が
      不十分になった段階で対応する。

### 推薦精度
- [ ] フィードバックデータを用いた重み調整
- [ ] 検索ログを用いた同義語辞書自動更新

---

## Phase 4: 自動化・デプロイ

### CI/CD
- [ ] .github/workflows/ci.yml (pytest)
- [ ] .github/workflows/scrape.yml (週次スクレイピング)

### デプロイ
- [ ] Supabase PostgreSQL 接続設定
- [ ] Render/Railway デプロイ設定
- [ ] 環境変数設定ガイド

### 認証
- [ ] /admin に HTTPBasicAuth 追加

---

## 現在の優先タスク (並列実行可)

| # | タスク | 担当 | 状態 |
|---|--------|------|------|
| 1 | `docker compose run --rm web alembic upgrade head` (migration 0002適用) | ops | [ ] |
| 2 | `docker compose run --rm web python scripts/crawl_repo_items.py` | scripts | [ ] |
| 3 | `docker compose run --rm web python scripts/download_pdfs.py` | scripts | [ ] |
| 4 | `docker compose run --rm web python scripts/extract_pdf_text.py` | scripts | [ ] |
| 5 | OPENAI_API_KEY を .env に設定してから `extract_labels_openai.py` 実行 | scripts | [ ] |
| 6 | `docker compose run --rm web python scripts/import_to_db.py` | scripts | [ ] |
| 7 | search.pyのトランザクション修正 | app | [x] |
| 8 | pytest 実行確認 | tests | [ ] |
