# プロジェクト現状 (最終更新: 2026-05-27)

## システム概要
滋賀大学データサイエンス研究科の研究室探索・推薦Webアプリ  
FastAPI + HTMX + Jinja2 + Tailwind CSS / PostgreSQL / Docker + uv

## DB現状
| テーブル | 件数 | 備考 |
|---------|------|------|
| labs | 59件 | うち論文あり27件（一覧・推薦に表示） |
| teachers | 59名 | 専任・特任・特別招聘を含む |
| theses | 117件 | 令和2〜6年度（2021〜2025） |
| theses(lab紐付き) | 116件 | 残り1件はPDF容量超過でsupervisor_name null |
| lab_labels | 57研究室 | thesis_labelsから集計 |

## データパイプライン（完了済み）
```
crawl_repo_items.py   # WEKO3 APIから論文メタデータ取得（117件）
        ↓
download_pdfs.py      # PDF取得（117件, data/raw/pdfs/）
        ↓
extract_labels_openai.py  # PDF直接渡し → gpt-4o-mini でラベル抽出
                           # supervisor_name / method / data / theme / data_raw / method_raw
        ↓
import_to_db.py       # theses / thesis_labels / lab_labels をupsert
        ↓
crawl_teachers.py → import_teachers_to_db.py  # 教員・研究室をupsert
```

## ラベルマスタ（v2）
- method: 深層学習 / 統計モデリング / 時系列解析 / 自然言語処理 / コンピュータビジョン / ベイズ手法 / 強化学習 / 因果推論 / 最適化 / ネットワーク分析 / データ同化
- data: 画像・映像 / 音声 / テキスト / 時系列・センサー / 数値・表形式 / 地理空間 / IoT
- theme: 製造・ものづくり / 医療・ヘルスケア / 農業・自然科学 / 教育 / 経済・金融 / 社会・政策 / スポーツ / マーケティング・消費 / 交通・インフラ / 音楽・メディア

## 実装済み機能
- [x] 研究室一覧 `/labs` — ラベル絞り込み(OR/AND)、グループ表示、「修士論文あり」トグル
- [x] 研究室詳細 `/labs/:id` — ラベル / 実際のデータ・手法(data_raw/method_raw) / 論文一覧+要約
- [x] 推薦フォーム `/recommend` — method/data/theme選択
- [x] 推薦結果 `/recommend/:id` — Jaccardスコアリング、マッチ理由付き
- [x] キーワード検索 `/search` — 同義語展開
- [x] 管理画面 `/admin`
- [x] Adminer `/8080` — DB確認用

## ブランチ
- `develop` — 開発中（現在）
- `main` — リリース用（未使用）
