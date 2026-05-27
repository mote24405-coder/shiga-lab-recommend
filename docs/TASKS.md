# タスク管理 (最終更新: 2026-05-27)

## ステータス凡例
- `[ ]` 未着手
- `[~]` 進行中
- `[x]` 完了
- `[-]` 保留・スキップ

---

## 🔴 高優先（UIの核心）

### T-01: Webアプリ ブラウザ動作確認
**担当Claude可**: UI確認・バグ修正
- [ ] `/labs` 一覧ページ — 絞り込み・グループ・トグル動作確認
- [ ] `/labs/:id` 詳細ページ — data_raw / method_raw / 論文一覧表示確認
- [ ] `/recommend` 推薦フォーム → 結果ページ — スコアリング確認
- [ ] `/search` キーワード検索 — 結果表示確認
- [ ] モバイル表示確認

### T-02: 推薦ロジックのチューニング
**担当Claude可**: recommendation.py 修正
- [ ] 実際にアンケート入力して適切な研究室が上位に来るか確認
- [ ] 「深層学習 + 画像・映像 + 医療」→ 飯山・市川・村松研究室が上位か検証
- [ ] スコア0の研究室が多すぎる場合は部分一致ボーナス追加を検討

---

## 🟡 中優先（データ品質）

### T-03: 竹村・椎名研究室の lab_labels 集計
**担当Claude可**: スクリプト or SQL
- [ ] thesis_labels → lab_labels への集計漏れを修正
- [ ] `scripts/import_teachers_to_db.py` の `aggregate_lab_labels` を手動実行

### T-04: 論文14544 の再処理（supervisor_name null）
**担当Claude可**: scripts/extract_labels_openai.py
- [ ] 大容量PDF（ゼロ過剰の非負値データに対する統計モデルの構築）
- [ ] 先頭30ページのみ抽出してテキスト渡しで再試行
- [ ] supervisor_name を手動で設定してもよい（杉本 知之 or 椎名 洋？）

### T-05: 新年度論文の追加クロール体制
**担当Claude可**: crawl_repo_items.py 改修
- [ ] 令和7年度(2026-03修了)が公開されたら自動or手動で追加できる体制を確認
- [ ] GitHub Actions での定期クロール設定（任意）

---

## 🟢 低優先（デプロイ・運用）

### T-06: 管理画面の認証追加
**担当Claude可**: routers/admin.py
- [ ] `/admin` に HTTPBasicAuth を追加
- [ ] 環境変数 `ADMIN_PASSWORD` で設定

### T-07: デプロイ設定
**担当Claude可**: インフラ設定
- [ ] Supabase PostgreSQL 接続設定（DATABASE_URL 切り替え）
- [ ] Render または Railway へのデプロイ設定
- [ ] 環境変数ガイドの整備

### T-08: CI/CD
**担当Claude可**: .github/workflows/
- [ ] pytest 実行確認（tests/ディレクトリに空ファイルあり）
- [ ] GitHub Actions CI 設定

### T-09: pg_trgm による検索精度改善
**担当Claude可**: migrations/ + crud.py
- [ ] migration 追加で pg_trgm 拡張インストール
- [ ] theses.title / labs.name に GIN インデックス追加
- [ ] 現在の LIKE 検索を類似度検索に置き換え

---

## 並列実行ガイド

複数のClaudeが同時に作業する場合のルール：

| 担当 | 触るファイル | 競合しないか |
|------|-------------|------------|
| UI担当 | `app/templates/`, `app/routers/` | ✅ T-01 |
| 推薦担当 | `app/services/recommendation.py` | ✅ T-02 |
| データ担当 | `scripts/`, `migrations/` | ✅ T-03, T-04 |
| インフラ担当 | `docker-compose.yml`, `.github/` | ✅ T-06, T-07, T-08 |

**競合注意**: `app/crud.py` は複数タスクから参照されるため、同時編集は避ける。

---

## 完了済みタスク

- [x] Phase 0: 基盤構築（Docker / DB / FastAPI）
- [x] Phase 1: MVPウェブアプリ全ページ実装
- [x] Phase 2: データパイプライン（クロール→PDF→ラベル抽出→DB投入）
- [x] 令和2〜6年度 117件 投入（PDF直接渡し方式、¥104）
- [x] 教員57名 スクレイピング・DB投入（特別招聘含む）
- [x] ラベルマスタv2（method×11, data×7, theme×10）
- [x] 研究室詳細に data_raw / method_raw / summary_ja 表示
- [x] 論文あり研究室のみ表示トグル実装
- [x] 仮データ削除（田中・鈴木・中村・小林・吉田研究室）
