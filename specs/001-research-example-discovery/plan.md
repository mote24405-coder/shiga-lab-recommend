# Implementation Plan: トップページの研究例から研究室を探す

**Branch**: `001-research-example-discovery`（`main` から作成済み、[Q-01](#確定した方針)） | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-research-example-discovery/spec.md`（Status: Draft、2026-11-25）

**この計画の読み手**: このチャットの経緯を知らない実装エージェント（Codex）。この文書と、文中で示すリポジトリ内のファイルだけで実装できるように書いている。計画作成時の参照元は森さんのローカル作業ツリー（ブランチ `codex/lab-label-evidence` @ a7fdbe6 と未コミット変更）。

## この計画の構成

Spec Kitの標準では `research.md`、`data-model.md`、`contracts/`、`quickstart.md` を別ファイルにするが、この計画は単独で読めるよう `plan.md` 1ファイルにまとめた。対応は次のとおり。`$speckit-tasks` はこのファイルだけを入力にしてよい。

| 標準の成果物 | この計画での場所 |
| --- | --- |
| research.md（決定・理由・代替案） | [設計判断](#設計判断) |
| data-model.md | [用語と判定規則](#用語と判定規則)（DB変更なし） |
| contracts/ | [エンドポイントと画面の契約](#エンドポイントと画面の契約) |
| quickstart.md | [品質確認](#品質確認)、[ブラウザでの確認](#ブラウザでの確認) |

## Summary

トップページに、研究室と日本語要約が登録された実際の修士論文を「研究例」として6件まで表示する。「もっと見る」で全研究例の一覧に進み、研究テーマで絞り込める。研究例を選ぶと、そのときの論文と研究室の対応を見て研究室ページへ移動し、選んだ論文の位置へスクロールして強調表示する。

技術的な方針は次のとおり。

- DBスキーマは変更しない。既存の `theses`、`thesis_labels`、`labels`（`label_type='theme'`）、`labs` を読むだけ。
- 研究例の判定、6件の選定、テーマ絞り込み、テーマ別件数は、新しいサービス `app/services/research_examples.py` で行う。選定の乱数はテストから注入でき、DBなしで単体テストできる。
- 研究例のリンク先は `/research-examples/{thesis_id}` にする。クリックした時点の `theses.lab_id` を読み、`/labs/{lab_id}#thesis-{thesis_id}` へリダイレクトする。
- 画面はサーバー側のJinja2描画と通常のリンク（GETのクエリ）で作る。JavaScriptやHTMXは追加しない。

## Technical Context

| 項目 | 内容（確認元） |
| --- | --- |
| Language/Version | Python 3.12（`Dockerfile` の `python:3.12-slim`、`.github/workflows/ci.yml` の `python-version: "3.12"`） |
| Primary Dependencies | `requirements.txt` の固定版: fastapi==0.115.5、jinja2==3.1.4、sqlalchemy==2.0.36、asyncpg==0.30.0、pytest==8.3.3、pytest-asyncio==0.24.0、httpx==0.28.0。starletteは固定されておらず、fastapi 0.115.5 の依存として入る（2026-11-25にuvで同じ `requirements.txt` から入れた環境では 0.41.3） |
| Storage | PostgreSQL 16（`docker-compose.yml`）。Alembic head は `0004`（`migrations/versions/0004_lab_views.py`）。今回マイグレーションなし |
| Testing | pytest。既存テストはDBなしで動く単体テストと、`jinja2.Environment` でテンプレートを描画するテスト（`tests/test_label_evidence.py`） |
| Target Platform | Linuxコンテナ（Railway、`railway.toml`）。開発は森さんのWindows PC + Docker Compose |
| Project Type | サーバー描画のWebアプリ（FastAPI + Jinja2 + Tailwind CDN + HTMX CDN） |
| Performance Goals | 未設定。研究例の対象は開発用DBで114件（[日報](../../daily_reports/2026-11-25-ddd-reference-guide.md)）で、全件を読んでPythonで処理しても問題ない規模と見込む（推定、未測定） |
| Constraints | 依存の追加なし。DB変更なし。既存の未コミット作業を壊さない（`AGENTS.md`）。既存ファイルの改行コードはCRLFなので、そのまま保つ |
| Scale/Scope | 新規エンドポイント2本、トップページの変更、研究室ページへのアンカー追加 |

## Constitution Check

`.specify/memory/constitution.md`（1.0.0）の原則との照合。設計後に再確認済み（本文末の[レビュー記録](#レビュー記録)）。

| 原則 | 判定 | 根拠 |
| --- | --- | --- |
| I. 利用者の判断と出典を支える | 合格 | 研究例は実在の論文タイトルと登録済み要約だけを表示し、要約が論文PDFからAIで自動生成されたことをカードごとに示す（FR-004）。推薦スコアは使わない |
| II. 既存の利用経路とデータを守る | 合格 | 影響する画面: `/`、`/labs/{id}`、`/theses`（アンカーのみ）。新規公開経路: `/research-examples`、`/research-examples/{thesis_id}`。DB・保存形式は変更しない。既存の層分け（router → crud → services）に合わせる |
| III. AIの採用を比較結果で説明する | 対象外 | 抽出・検索・推薦方式は変えない。既存のAI要約を表示するだけ |
| IV. 実サービスの運用を再現できるようにする | 対象外 | クラウド機能・定期処理の追加なし |
| V. 小さな変更と確認可能な成果物 | 合格 | 単体テスト、ルートのテスト、ブラウザ確認手順、完了チェックリストを用意する |

違反はないため、Complexity Tracking は空。

## 用語と判定規則

[GLOSSARY.md](../../GLOSSARY.md) の用語をコード上の事実に対応づける。

| 用語 | コード上の定義 |
| --- | --- |
| 研究例 | `Thesis` のうち、`lab_id IS NOT NULL` かつ `summary_ja` が空白以外の文字を1文字以上含むもの。空白には全角スペース（U+3000）と改行を含む。Pythonの `str.strip()` で判定する |
| 研究テーマ | `Label` のうち `label_type == "theme"` のもの（マスタは12件、`migrations/versions/0003_new_label_master.py` の `NEW_THEME_LABELS`） |
| 研究例のテーマ | その論文の `thesis_labels` から辿れる `label_type == "theme"` のラベル。`thesis_labels.confidence` の値は問わない（[Q-04](#確定した方針)）。`thesis_labels` には `(thesis_id, label_id)` の一意制約がないため、ラベルIDで重複を除く |
| 研究室 | `Thesis.lab` で辿れる `Lab`。研究室の `lab_labels` は使わない |

要約の由来: `scripts/extract_labels_openai.py` が論文PDFを `gpt-4o-mini` に渡して `summary_ja`（「100字程度の日本語要約」）を作り、`scripts/import_to_db.py` の `upsert_thesis` が `theses.summary_ja` に入れる。

## 現状のコード（計画の前提、すべてローカルスナップショットで確認済み）

| 場所 | 現状 | 今回の関係 |
| --- | --- | --- |
| `app/main.py` 42–44行 | `index(request)` が `index.html` を描画。DBを使っていない | DBから研究例を読むように変える |
| `app/main.py` 10行・32–39行 | ルーターのimportと `include_router` | 新ルーターを追加する |
| `app/database.py` | `get_db()`（`AsyncSession` を `yield` する非同期ジェネレーター） | 依存として使う。テストで差し替える |
| `app/models.py` `Thesis` | `id`, `lab_id`, `title`, `year`, `summary_ja`, `lab`, `thesis_labels` | 読み取りのみ |
| `app/models.py` `ThesisLabel` / `Label` | `ThesisLabel.label` → `Label(id, label_type, name)` | 読み取りのみ |
| `app/crud.py` | DB操作の集約。`get_lab()` は `Lab.theses` を `selectinload` で読む。90行に `# ── Labels ─` の区切り | 新関数を2つ追加する |
| `app/routers/theses.py` | `/theses` は全論文を年度降順で表示 | 変更しない。FR-009の閲覧先 |
| `app/templates/index.html` | ヒーロー（5–27行）と「3ステップ」（29–42行） | 2つの間に研究例セクションを入れる |
| `app/templates/labs/detail.html` 181–224行 | 「関連する修士論文」。188行で `lab.theses` を年度降順に並べ、192行の `<div class="px-5 py-4">` が論文1件、213–215行で `summary_ja` を表示 | 論文ごとにアンカーと強調表示を加える |
| `app/templates/theses/index.html` 7行 | 論文1件の `<div>`。アンカーなし | アンカーを加える |
| `app/templates/base.html` | `request.url.path` でナビの現在地を判定。Tailwind Play CDNとHTMX 2.0.3をCDNから読む | 変更しない。テンプレートの単体描画では `request` を渡す必要がある |
| `app/static/css/style.css` | `.card`、`.badge`、`.badge-theme` などの共通クラス | 新しいクラスを末尾に追加する |
| `tests/test_label_evidence.py` | `SimpleNamespace` の偽データと `jinja2.Environment` でテンプレートを描画する例 | 同じ書き方を使う |

## 設計判断

| ID | 決定 | 理由 | 退けた案 |
| --- | --- | --- | --- |
| D-01 | DBを変えず、既存の列から研究例を判定する | 必要な情報（タイトル、要約、研究室、テーマ）はすべて既存の列にある。仕様もデータ追加を求めていない | 「研究例フラグ」列の追加: 判定規則が二重管理になり、マイグレーションが必要 |
| D-02 | 研究例の候補はSQLで `lab_id IS NOT NULL AND summary_ja IS NOT NULL` まで絞り、空白だけの要約の除外・重複除去・並べ替え・選定・絞り込みはPythonで行う | 対象は約100件。選定用の乱数をテストから注入すれば、DBなしで仕様のルールを確かめられる。全角スペースを含む空白判定はSQLより `str.strip()` が確実 | テーマ絞り込みをSQLの `IN` サブクエリで行う案: CIにテストデータがなく、DBを使うテストの土台（イベントループとエンジンの扱い）を新しく作る必要がある |
| D-03 | トップの候補をページ表示ごとにランダムに並べ替え、最初の1件は全候補から選ぶ。残りはその順で (1) まだ出ていないテーマを含み、かつまだ出ていない研究室の論文、(2) まだ出ていないテーマを含む論文、(3) 残り、の3段階で6件まで取る。乱数の種をテストから渡せるようにする | テーマ未登録の論文を含む全候補に、最初の1件として選ばれる機会がある。残りではテーマと研究室の偏りを減らせる。候補が6件以下なら全件を表示し、抽選によって同じ組合せが続くことはある | 多様性だけで6件を選ぶ: 特定の候補が常に除外される。無条件のランダム抽出: 同じテーマや研究室に偏りやすい |
| D-04 | 研究例のリンクは `/research-examples/{thesis_id}` で、クリック時に `theses.lab_id` を読んで `303 See Other` で `/labs/{lab_id}#thesis-{thesis_id}` へ送る。`lab_id` が空になっていたら `/theses#thesis-{thesis_id}`、論文が消えていたら404 | 仕様の境界条件「対応が更新された後も、表示中の研究例から別の研究室へ誤って案内しない」を、表示時ではなくクリック時の対応で満たす | 研究室ページへ直接リンク: 画面を開いた後に対応が変わると古い研究室へ案内する |
| D-05 | 選んだ論文の特定は、URLフラグメントとCSSの `:target` で行う。対象の論文を背景色と左線で強調し、「選んだ研究例」と表示する | JavaScript不要。リダイレクト先の `Location` にフラグメントを含めればブラウザがその要素までスクロールする | クエリ `?thesis=` とサーバー側の強調: 研究室ページの処理を変える必要があり、効果は同じ |
| D-06 | 一覧の絞り込みは `GET /research-examples?theme={label_id}` の通常リンクで行い、一度に選べるテーマは1つ | 仕様は「テーマを選ぶ・解除する」だけを求めている。URLで状態を共有でき、戻るボタンも自然に動く | HTMXでの部分更新: 必要性が低く、テストが増える。複数テーマの同時選択: 仕様にない |
| D-07 | 一覧は年度の新しい順（年度なしは最後、同年度はID昇順）に固定し、ページ分割はしない | 対象は約100件で、一覧の1ページに収まる。一覧では再訪時も論文の位置を見つけやすい | ページ分割: 現在の件数では不要 |
| D-08 | 要約は全文表示する（文数・文字数で切らない）。カードごとに「AI要約」バッジを付け、セクションの説明文で「論文PDFからAIで自動生成した要約」と明記する | FR-003（文数を制限しない）とFR-004。開発用DBの要約は63〜122文字で、全文でもカードが崩れない | 2行で省略: FR-003に反する |
| D-09 | テーマのチップは、研究例が1件以上あるテーマだけを件数の多い順（同数は名前順）に表示する。存在しないテーマIDや研究例0件のテーマIDがURLで来たら、0件の表示と解除リンクを出す | 0件のテーマを並べると、学生が結果のない選択をしやすい。URLの直接入力でも境界条件を満たす | 12テーマ全部を常に表示 |
| D-10 | トップページのルートは `app/main.py` に残し、一覧とリダイレクトは新ルーター `app/routers/research_examples.py` に置く | 既存の `/` の場所を変えず、差分を小さくする | `/` を新ルーターへ移す: 変更が広がる |

## エンドポイントと画面の契約

| メソッド・パス | 入力 | 出力 |
| --- | --- | --- |
| `GET /`（変更） | なし | `index.html`。研究例が1件以上あれば研究例セクションにカードを最大6件と「もっと見る」リンク。0件なら「表示できる研究例はまだありません」 |
| `GET /research-examples`（新規） | `theme`: 整数、任意。整数でない値はFastAPIの検証で422 | `research_examples/index.html`。テーマのチップ（「すべて」+研究例のあるテーマ）、件数、カード一覧、0件なら空の表示と解除リンク |
| `GET /research-examples/{thesis_id}`（新規） | `thesis_id`: 整数 | 303で `/labs/{lab_id}#thesis-{thesis_id}`。`lab_id` が `None` なら303で `/theses#thesis-{thesis_id}`。論文がなければ404 |

テストと確認で使うHTMLの目印（実装で必ず付ける）:

- 研究例カード: `<a href="/research-examples/{{ example.id }}" ... data-testid="research-example" data-thesis-id="{{ example.id }}">`
- AI要約バッジ: 文言「AI要約」、クラス `ai-summary-badge`
- 一覧の件数: `data-testid="result-count"`
- 0件表示: `data-testid="empty-state"`。中に `href="/research-examples"` の解除リンク
- 選択中のテーマのチップ: `aria-current="page"`
- 研究室ページと論文一覧の論文: `id="thesis-{{ thesis.id }}"`

## 変更ファイル

### 1. `app/services/research_examples.py`（新規）

ファイル全体（このまま使ってよい）。引数の型は `Thesis` だが、テストでは同じ属性を持つ `SimpleNamespace` を渡す。

```python
"""研究例（研究室と日本語要約が登録された修士論文）の選定と絞り込み。"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable, Sequence

from app.models import Label, Thesis

FEATURED_EXAMPLE_LIMIT = 6
THEME_LABEL_TYPE = "theme"


@dataclass(frozen=True)
class ResearchTheme:
    id: int
    name: str
    example_count: int


def is_research_example(thesis: Thesis) -> bool:
    return thesis.lab_id is not None and bool((thesis.summary_ja or "").strip())


def collect_theme_labels(thesis: Thesis) -> list[Label]:
    themes: dict[int, Label] = {}
    for thesis_label in thesis.thesis_labels:
        label = thesis_label.label
        if label is not None and label.label_type == THEME_LABEL_TYPE:
            themes.setdefault(label.id, label)
    return sorted(themes.values(), key=lambda label: label.name)


def sort_research_examples(theses: Iterable[Thesis]) -> list[Thesis]:
    unique: dict[int, Thesis] = {}
    for thesis in theses:
        if is_research_example(thesis):
            unique.setdefault(thesis.id, thesis)
    return sorted(unique.values(), key=lambda t: (t.year is None, -(t.year or 0), t.id))


def select_featured_examples(
    examples: Sequence[Thesis], limit: int = FEATURED_EXAMPLE_LIMIT, rng: Random | None = None
) -> list[Thesis]:
    candidates = list(examples)
    (rng if rng is not None else Random()).shuffle(candidates)
    if limit <= 0 or not candidates:
        return []
    first = candidates[0]
    selected: list[Thesis] = [first]
    selected_ids: set[int] = {first.id}
    covered_theme_ids: set[int] = {label.id for label in collect_theme_labels(first)}
    used_lab_ids: set[int] = {first.lab_id}

    def theme_ids_of(thesis: Thesis) -> set[int]:
        return {label.id for label in collect_theme_labels(thesis)}

    def adds_new_theme(thesis: Thesis) -> bool:
        return bool(theme_ids_of(thesis) - covered_theme_ids)

    stages = (
        lambda thesis: adds_new_theme(thesis) and thesis.lab_id not in used_lab_ids,
        adds_new_theme,
        lambda thesis: True,
    )
    for accepts in stages:
        for thesis in candidates:
            if len(selected) >= limit:
                return selected
            if thesis.id in selected_ids or not accepts(thesis):
                continue
            selected.append(thesis)
            selected_ids.add(thesis.id)
            covered_theme_ids.update(theme_ids_of(thesis))
            used_lab_ids.add(thesis.lab_id)
    return selected


def filter_examples_by_theme(examples: Sequence[Thesis], theme_id: int | None) -> list[Thesis]:
    if theme_id is None:
        return list(examples)
    return [t for t in examples if any(label.id == theme_id for label in collect_theme_labels(t))]


def count_examples_by_theme(examples: Sequence[Thesis]) -> list[ResearchTheme]:
    names: dict[int, str] = {}
    counts: dict[int, int] = {}
    for thesis in examples:
        for label in collect_theme_labels(thesis):
            names[label.id] = label.name
            counts[label.id] = counts.get(label.id, 0) + 1
    themes = [ResearchTheme(id=i, name=names[i], example_count=c) for i, c in counts.items()]
    return sorted(themes, key=lambda theme: (-theme.example_count, theme.name))
```

| 関数 | 振る舞い（テストで確かめる点） |
| --- | --- |
| `is_research_example(thesis)` | `lab_id` があり、`summary_ja` が空白（全角スペース・改行を含む）以外の文字を含むときだけ True |
| `collect_theme_labels(thesis)` | `thesis_labels` のうち `label_type == "theme"` のラベルを、`label.id` で重複を除き名前順で返す。`label` が `None` の行は無視 |
| `sort_research_examples(theses)` | 研究例だけを残し、`id` で重複を除き、年度の新しい順（年度なしは最後、同年度は `id` 昇順）に並べる |
| `select_featured_examples(examples, limit=6, rng=None)` | 候補のコピーを呼び出しごとにランダムに並べ替え、最初の1件を無条件に選ぶ。残りはD-03の3段階で最大 `limit` 件まで選ぶ。渡された候補の順序は変えない。テストは `Random(seed)` を渡して再現可能にする。テーマのない論文も最初の1件か(3)の補充で入る |
| `filter_examples_by_theme(examples, theme_id)` | `None` なら全件。それ以外はそのテーマを持つ研究例だけを元の順で返す。1件は1回しか現れない |
| `count_examples_by_theme(examples)` | 研究例が1件以上あるテーマだけを、件数の多い順（同数は名前順）で返す。1論文は1テーマにつき1回だけ数える |

### 2. `app/crud.py`（変更）

90行の `# ── Labels ─...` の直前に、区切りコメント `# ── Research examples ─...` と次の2関数（新規）を追加する。importは既存の `select`、`selectinload`、`Thesis`、`ThesisLabel` で足りる。

```python
async def list_research_example_candidates(db: AsyncSession) -> list[Thesis]:
    stmt = (
        select(Thesis)
        .options(
            selectinload(Thesis.lab),
            selectinload(Thesis.thesis_labels).selectinload(ThesisLabel.label),
        )
        .where(Thesis.lab_id.isnot(None))
        .where(Thesis.summary_ja.isnot(None))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def find_thesis(db: AsyncSession, thesis_id: int) -> Thesis | None:
    return await db.get(Thesis, thesis_id)
```

- 非同期セッションでは未ロードのリレーションに触れると遅延ロードが起きずエラーになる。テンプレートで使う `lab` と `thesis_labels.label` は必ず `selectinload` で読む。
- 既存関数の命名は `get_*` だが、新規関数はプロジェクトの `code-naming` スキルに従い `list_` / `find_` にする。

### 3. `app/routers/research_examples.py`（新規）

```python
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.services.research_examples import (
    count_examples_by_theme,
    filter_examples_by_theme,
    sort_research_examples,
)

router = APIRouter(prefix="/research-examples", tags=["research-examples"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def research_examples_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    theme: int | None = Query(default=None),
):
    examples = sort_research_examples(await crud.list_research_example_candidates(db))
    themes = count_examples_by_theme(examples)
    return templates.TemplateResponse("research_examples/index.html", {
        "request": request,
        "examples": filter_examples_by_theme(examples, theme),
        "themes": themes,
        "selected_theme_id": theme,
        "selected_theme": next((t for t in themes if t.id == theme), None),
        "total_count": len(examples),
    })


@router.get("/{thesis_id}")
async def open_research_example(thesis_id: int, db: AsyncSession = Depends(get_db)):
    thesis = await crud.find_thesis(db, thesis_id)
    if thesis is None:
        raise HTTPException(status_code=404, detail="論文が見つかりません")
    if thesis.lab_id is None:
        return RedirectResponse(url=f"/theses#thesis-{thesis.id}", status_code=303)
    return RedirectResponse(url=f"/labs/{thesis.lab_id}#thesis-{thesis.id}", status_code=303)
```

- `crud` は `from app import crud` で読み込み、`crud.関数名(...)` で呼ぶ。テストで `monkeypatch.setattr(crud, ...)` が効くようにするため。`from app.crud import ...` にしない。
- `TemplateResponse(name, {"request": request, ...})` は既存ルーターと同じ書き方。starlette 0.41.3 では非推奨警告が出るが、既存コードとそろえる（書き方の統一は今回の範囲外）。

### 4. `app/main.py`（変更）

- 10行のimportに `research_examples` を加える: `from app.routers import labs, teachers, theses, recommend, search, surveys, admin, explore, research_examples`
- 3行の `from fastapi import FastAPI, Request` を `from fastapi import Depends, FastAPI, Request` に変える。
- 7行（`from starlette.middleware.base import BaseHTTPMiddleware`）の後に `from sqlalchemy.ext.asyncio import AsyncSession` を追加する。
- 9行（`from app.config import get_settings`）の前に `from app import crud` を、後に `from app.database import get_db` を追加し、10行の後に `from app.services.research_examples import select_featured_examples, sort_research_examples` を追加する。
- 39行の後に `app.include_router(research_examples.router)` を追加する。
- 42–44行の `index` を次に置き換える。

```python
@app.get("/")
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    examples = sort_research_examples(await crud.list_research_example_candidates(db))
    return templates.TemplateResponse("index.html", {
        "request": request,
        "featured_examples": select_featured_examples(examples),
        "research_example_count": len(examples),
    })
```

注意: これで `/` がDBに依存する。DBが止まっていると `/` は500になる（現状の `/labs` と同じ）。`/health` はDBを使わないまま。

### 5. `app/templates/research_examples/_card.html`（新規）

カード1件のマクロ。トップと一覧の両方で使う。

```jinja
{% macro research_example_card(example) %}
<a href="/research-examples/{{ example.id }}" class="card block p-4 group"
   data-testid="research-example" data-thesis-id="{{ example.id }}">
  <h3 class="text-sm font-semibold text-slate-800 leading-snug group-hover:text-teal-700">{{ example.title }}</h3>
  <p class="text-xs text-slate-400 mt-1">{% if example.year %}{{ example.year }}年 · {% endif %}{{ example.lab.name }}</p>
  <p class="text-xs text-slate-600 leading-relaxed mt-2">
    <span class="ai-summary-badge" title="論文PDFからAIで自動生成した要約">AI要約</span>{{ example.summary_ja }}
  </p>
  {% set themes = example.thesis_labels | map(attribute='label') | selectattr('label_type', 'eq', 'theme') | unique(attribute='id') | sort(attribute='name') | list %}
  {% if themes %}
  <div class="flex flex-wrap gap-1 mt-2">
    {% for label in themes %}<span class="badge badge-theme">{{ label.name }}</span>{% endfor %}
  </div>
  {% endif %}
</a>
{% endmacro %}
```

- タイトルと要約は自動エスケープされる（`Jinja2Templates` は `.html` で自動エスケープが有効）。`| safe` を使わない。
- カード全体が1つのリンク。カードの中に別のリンクを入れない。

### 6. `app/templates/research_examples/index.html`（新規）

構成（上から順に）:

1. `{% extends "base.html" %}`、`{% from "research_examples/_card.html" import research_example_card %}`、`{% block title %}研究例一覧{% endblock %}`
2. 「← トップへ戻る」リンク（`href="/"`）
3. 見出し `研究例一覧` と説明「実際の修士論文から、研究室と日本語要約が登録されたものを表示しています。要約は論文PDFからAIで自動生成したもので、内容は論文本文で確認してください。」
4. テーマのチップ。マークアップは次のとおり（選択中だけ `badge-theme` と `aria-current="page"` を付ける）。

   ```jinja
   <nav aria-label="研究テーマで絞り込む" class="flex flex-wrap gap-2 mb-4">
     <a href="/research-examples" class="badge {% if selected_theme_id is none %}badge-theme{% else %}chip-idle{% endif %}" {% if selected_theme_id is none %}aria-current="page"{% endif %}>すべて（{{ total_count }}）</a>
     {% for theme in themes %}
     <a href="/research-examples?theme={{ theme.id }}" class="badge {% if theme.id == selected_theme_id %}badge-theme{% else %}chip-idle{% endif %}" {% if theme.id == selected_theme_id %}aria-current="page"{% endif %}>{{ theme.name }}（{{ theme.example_count }}）</a>
     {% endfor %}
   </nav>
   ```
5. 選択中のテーマがあれば「「{{ selected_theme.name }}」の研究例」と「絞り込みを解除」リンク（`href="/research-examples"`）
6. `<p data-testid="result-count">{{ examples | length }}件</p>`
7. `examples` があればカードのグリッド（`grid grid-cols-1 md:grid-cols-2 gap-3`）。なければ `<div data-testid="empty-state">` に「このテーマの研究例はありません。」と解除リンク
8. 最下部に「要約や研究室の対応が未登録の論文は[修士論文一覧](/theses)で見られます。」（FR-009）

### 7. `app/templates/index.html`（変更）

- 1行目の直後に `{% from "research_examples/_card.html" import research_example_card %}` を追加する。
- 27行（ヒーローの閉じタグ）と29行（`<!-- 3ステップ -->`）の間に、次のセクションを追加する。ヒーローと3ステップの内容は変えない（[Q-03](#確定した方針)）。

```jinja
<section class="mb-10" aria-labelledby="research-examples-heading">
  <div class="flex items-end justify-between flex-wrap gap-2 mb-3">
    <div>
      <h2 id="research-examples-heading" class="text-lg font-bold text-slate-800 tracking-tight">研究例から探す</h2>
      <p class="text-xs text-slate-500 mt-1">実際の修士論文から、研究テーマの異なる例を選んでいます。要約は論文PDFからAIで自動生成したものです。</p>
    </div>
    {% if featured_examples %}
    <a href="/research-examples" class="text-sm text-teal-700 hover:underline">もっと見る（{{ research_example_count }}件）→</a>
    {% endif %}
  </div>
  {% if featured_examples %}
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
    {% for example in featured_examples %}{{ research_example_card(example) }}{% endfor %}
  </div>
  {% else %}
  <p class="text-sm text-slate-500">表示できる研究例はまだありません。</p>
  {% endif %}
</section>
```

### 8. `app/templates/labs/detail.html`（変更）

- 192行 `<div class="px-5 py-4">` を `<div id="thesis-{{ thesis.id }}" class="thesis-item px-5 py-4">` に変える。
- その直後（193行の論文タイトル `<p>` の前）に `<span class="selected-example-note">選んだ研究例</span>` を追加する。CSSで `:target` のときだけ表示する。
- 213–215行の要約の `<p>` の先頭に `<span class="ai-summary-badge" title="論文PDFからAIで自動生成した要約">AI要約</span>` を入れる（研究例から来た学生が同じ要約を見たとき、自動生成と分かるように。[Q-05](#確定した方針)）。

### 9. `app/templates/theses/index.html`（変更）

- 7行の `<div class="bg-white border border-gray-200 rounded-xl p-4 text-sm">` に `id="thesis-{{ thesis.id }}"` と `thesis-item` クラスを加える。D-04で研究室が外れた論文の移動先にする。

### 10. `app/static/css/style.css`（変更）

末尾に追加する。

```css
/* ── 研究例 ── */
.ai-summary-badge {
  display: inline-block;
  margin-right: 6px;
  padding: 0 6px;
  border-radius: 3px;
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--c-muted);
  background: #f1f5f9;
  border: 1px solid var(--c-border);
  vertical-align: 1px;
}
.chip-idle {
  background: var(--c-surface);
  color: var(--c-muted);
  border-color: var(--c-border);
}
.chip-idle:hover { border-color: var(--c-primary); color: var(--c-primary); }
.thesis-item { scroll-margin-top: 4rem; }
.thesis-item:target {
  background: var(--c-primary-lt);
  box-shadow: inset 3px 0 0 var(--c-primary);
}
.selected-example-note { display: none; }
.thesis-item:target .selected-example-note {
  display: inline-block;
  margin-bottom: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--c-primary);
}
```

`scroll-margin-top: 4rem` は、`base.html` の固定ナビ（`sticky`、高さ `h-12` = 3rem）に論文の見出しが隠れないようにするため。

### 11. `tests/test_research_examples.py`（新規）

[テスト方針](#テスト方針)の表のとおり。

### 変更しないもの

- `app/models.py`、`migrations/`: DB変更なし
- `app/templates/base.html`: ナビに「研究例」を足さない（仕様の範囲外。必要なら別途）
- `app/routers/theses.py`、`app/routers/labs.py`、`app/crud.py` の既存関数
- 推薦機能（仕様で後続課題とされている）

## ライブラリの使い方（固定版と一次情報）

| 使うもの | 版 | 使い方 | 一次情報 |
| --- | --- | --- | --- |
| `RedirectResponse(url, status_code=303)` | starlette 0.41.3（fastapi 0.115.5経由） | 既定は307。今回は「別の場所を見よ」の意味で303を明示する。`Location` に `#` を含めてよい（starletteは `#` をエスケープしない） | https://starlette.dev/responses/ 、https://fastapi.tiangolo.com/advanced/custom-response/#redirectresponse 、303とフラグメントの扱い: https://www.rfc-editor.org/rfc/rfc9110#section-15.4.4 、https://www.rfc-editor.org/rfc/rfc9110#section-10.2.2 |
| 任意の整数クエリ `theme: int \| None = Query(default=None)` | fastapi 0.115.5 | 整数に変換できない値は422 | https://fastapi.tiangolo.com/tutorial/query-params/ |
| `AsyncSession.get(Model, pk)` | sqlalchemy 2.0.36 | 主キーで1件読む。なければ `None` | https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncSession.get |
| `selectinload(...).selectinload(...)` | sqlalchemy 2.0.36 | 関連を先に読む。非同期では暗黙の遅延ロードが使えない | https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#selectin-eager-loading 、https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession |
| `TestClient`、`app.dependency_overrides` | fastapi 0.115.5、httpx 0.28.0 | `get_db` を差し替えてDBなしでルートを呼ぶ。`client.get(url, follow_redirects=False)` でリダイレクトを追わずに確認する | https://fastapi.tiangolo.com/tutorial/testing/ 、https://fastapi.tiangolo.com/advanced/testing-dependencies/ |
| `monkeypatch.setattr` | pytest 8.3.3 | `app.crud` の関数を偽物に替える | https://docs.pytest.org/en/8.3.x/how-to/monkeypatch.html |
| `{% from ... import ... %}`、`{% macro %}`、`unique(attribute=...)` | jinja2 3.1.4 | マクロは引数だけを使うので、文脈なしのimport（既定）でよい | https://jinja.palletsprojects.com/en/3.1.x/templates/#import 、https://jinja.palletsprojects.com/en/3.1.x/templates/#jinja-filters.unique |
| CSS `:target`、`scroll-margin-top` | ブラウザ標準 | フラグメントで指された要素の強調と、固定ナビ分のずらし | https://developer.mozilla.org/en-US/docs/Web/CSS/:target 、https://developer.mozilla.org/en-US/docs/Web/CSS/scroll-margin-top |

## テスト方針

- 置き場所: `tests/test_research_examples.py`（新規）1ファイル。既存テストと同じく、DBなしで動かす。CIのPostgreSQLには研究例のデータがないため、DBに依存するテストは書かない。
- 偽データ: `types.SimpleNamespace` で `Thesis`（`id`、`lab_id`、`lab`、`title`、`year`、`summary_ja`、`thesis_labels`、`raw_labels`、`author_name`、`repo_url`）と `Label`（`id`、`label_type`、`name`）を作るヘルパー `make_thesis(...)` を置く。
- ルートのテスト: `app.dependency_overrides[get_db]` に `async def` の空ジェネレーター（`yield None`）を入れ、`monkeypatch.setattr(crud, "list_research_example_candidates", ...)` と `monkeypatch.setattr(crud, "find_thesis", ...)` で偽の結果を返す。テスト後に `app.dependency_overrides.clear()` する（fixtureで）。
- テスト名は「何が正しいか」が読める名前にする（例: `test_blank_summary_is_not_research_example`）。プロジェクトの `code-comments` スキルの「テストコードにはWhat」に従う。
- HTMLの属性の並びに依存した文字列比較は避け、`re.search(r'href="/research-examples"[^>]*aria-current="page"', html)` のように目印の組み合わせで確かめる。
- 研究室ページのテンプレートは `tests/test_label_evidence.py` と同じく `jinja2.Environment(loader=FileSystemLoader(...), autoescape=select_autoescape(["html"]))` で描画する。`base.html` が `request.url.path` を読むので、`request=SimpleNamespace(url=SimpleNamespace(path="/labs/1"))` を渡す。

| ID | 対象 | 観点（入力 → 期待） |
| --- | --- | --- |
| T-01 | `is_research_example` | 要約 `None`、`""`、`"   "`、`"\u3000\n"` → False（parametrize） |
| T-02 | `is_research_example` | `lab_id=None` で要約あり → False。研究室と要約あり → True |
| T-03 | `sort_research_examples` | 年度2022・2024・`None`、同じ論文の重複、研究室なしの論文を混ぜる → 研究例だけが年度の新しい順・年度なしは最後・重複なし |
| T-04 | `collect_theme_labels` | テーマ2つ+同じテーマの重複+手法ラベル → テーマ2つだけ、名前順 |
| T-05 | `select_featured_examples` | 研究室1にテーマ1の論文が4件、別々の研究室にテーマ2〜7の論文が1件ずつ。`Random(1)` を渡す → 6件、ID重複なし、6件のテーマがすべて異なる |
| T-06 | `select_featured_examples` | 研究例が2件（うち1件はテーマなし） → 2件だけ返す（6件に満たない場合） |
| T-07 | `select_featured_examples` | 同じテーマの論文3件+テーマなし1件 → 4件すべて返す（テーマなしも補充で入る） |
| T-08 | `select_featured_examples` | テーマと研究室がそれぞれ異なる6件＋テーマ未登録1件で種を0〜99に変えて選ぶ → テーマ未登録の論文も結果に現れ、複数の6件の組合せが得られる。同じ種なら同じ結果を再現でき、入力リストの順序は変わらない |
| T-09 | `filter_examples_by_theme` | テーマ1・2を持つ論文A（テーマ1の行が重複）、テーマ2の論文B、テーマなしの論文C → テーマ1でA、テーマ2でA・B（Aは1回）、`None` でA・B・C、存在しないIDで空 |
| T-10 | `count_examples_by_theme` | T-09の入力 → テーマ1が1件、テーマ2が2件。並びは件数の多い順 |
| T-11 | `GET /` | 偽の候補（研究例2件+空白要約1件） → 200、`data-testid="research-example"` が2個、「AI要約」、`href="/research-examples/1"`、`href="/research-examples"`（もっと見る） |
| T-12 | `GET /` | 候補0件 → 200、「表示できる研究例はまだありません」 |
| T-13 | `GET /research-examples` | テーマなし → 全研究例、「すべて」に `aria-current="page"`、`data-testid="result-count"` が件数 |
| T-14 | `GET /research-examples?theme=X` | 複数テーマの論文がXでも別テーマYでも出る。同じ一覧に同じ `data-thesis-id` が2回出ない |
| T-15 | `GET /research-examples?theme=99999` | `data-testid="empty-state"` と `href="/research-examples"` |
| T-16 | `GET /research-examples/{id}` | `lab_id=5` → 303、`location` が `/labs/5#thesis-1`。`lab_id=None` → `/theses#thesis-2`。存在しない → 404（すべて `follow_redirects=False`） |
| T-17 | `labs/detail.html` の描画 | 論文ID 7 を含む研究室 → `id="thesis-7"`、`selected-example-note`、要約ありなら `ai-summary-badge` |
| T-18 | `GET /` | 別々の研究室・別々のテーマの研究例8件 → カードは6個、「もっと見る（8件）」 |
| T-19 | `GET /research-examples` | タイトルが `<script>alert(1)</script>` の研究例 → 生のタグは出ず、`&lt;script&gt;` と表示される（自動エスケープ） |
| T-20 | `select_featured_examples` | A（研究室1・テーマ1）、B（研究室1・テーマ2）、C（研究室2・テーマ3）、`limit=2` と固定した乱数の種を渡す → 2件の研究室IDが異なる（新しいテーマでも、同じ研究室は後回し） |

## 品質確認

`AGENTS.md` の指定（uv、CIの依存定義は `requirements.txt`）と `.github/workflows/ci.yml` に合わせる。リポジトリにリンターやフォーマッターの設定はないため、追加しない。

Windows（PowerShell、リポジトリ直下）:

```powershell
uv venv .venv --python 3.12
uv pip install -r requirements.txt
.venv\Scripts\python -m pytest tests -v
```

`uv pip install` は、カレントディレクトリの `.venv` を自動で使う（https://docs.astral.sh/uv/pip/environments/ ）。

Docker Compose を使う場合:

```powershell
docker compose run --rm web pytest tests -v
```

期待結果: 既存18件と新規テストがすべて成功する。`DeprecationWarning`（starletteの `TemplateResponse` の引数順、anyio）は既存と同じ種類なら問題としない。

あわせて確認する:

1. `git diff --stat` で、[変更ファイル](#変更ファイル)の一覧以外に差分がないこと。計画作成時点の未コミット変更（`.gitignore`、`Dockerfile`、`README.md`、`app/routers/search.py`、`scripts/crawl_repo_items.py`、`scripts/import_to_db.py`）を書き換えていないこと。
2. 既存ファイルの改行コードがCRLFのままであること（`git diff` に全行の差分が出ていないこと）。
3. CIと同じく `alembic upgrade head` が成功すること（マイグレーションを追加していないので変化しないはず）。

## ブラウザでの確認

前提: `docker compose up --build` でアプリとDBを起動し、開発用DBに実データ（117件、[日報](../../daily_reports/2026-11-25-ddd-reference-guide.md)）が入っている。確認に使う論文IDを、先に次のSQLで調べる（Adminer http://localhost:8080 、または `docker compose exec db psql -U postgres -d lab_recommend`）。

```sql
-- A: 研究例になる論文（複数テーマ）
SELECT t.id, t.lab_id, t.title, string_agg(DISTINCT l.name, ' / ') AS themes
FROM theses t
JOIN thesis_labels tl ON tl.thesis_id = t.id
JOIN labels l ON l.id = tl.label_id AND l.label_type = 'theme'
WHERE t.lab_id IS NOT NULL AND COALESCE(t.summary_ja, '') ~ '[^[:space:]　]'
GROUP BY t.id HAVING COUNT(DISTINCT l.id) >= 2 ORDER BY t.id LIMIT 3;

-- B: 研究例になるがテーマがない論文（日報では4件）
SELECT t.id, t.title FROM theses t
WHERE t.lab_id IS NOT NULL AND COALESCE(t.summary_ja, '') ~ '[^[:space:]　]'
  AND NOT EXISTS (SELECT 1 FROM thesis_labels tl JOIN labels l ON l.id = tl.label_id
                  WHERE tl.thesis_id = t.id AND l.label_type = 'theme');

-- C: 研究例にならない論文（研究室なし、または要約なし）
SELECT id, lab_id, title, summary_ja IS NULL AS no_summary FROM theses
WHERE lab_id IS NULL OR COALESCE(summary_ja, '') !~ '[^[:space:]　]';

-- D: 研究例の総数（日報では114件）と、年度のない論文の数（研究室ページの並べ替えの前提確認。0件のはず）
SELECT COUNT(*) FROM theses WHERE lab_id IS NOT NULL AND COALESCE(summary_ja, '') ~ '[^[:space:]　]';
SELECT COUNT(*) FROM theses WHERE year IS NULL;
```

| # | 操作 | 期待結果 |
| --- | --- | --- |
| B-01 | http://localhost:8000/ を開く | ヒーローの下に「研究例から探す」があり、カードが6件。入力やテーマ選択をしなくても見える。6件のテーマ（オレンジのバッジ）は1種類に偏らない |
| B-02 | B-01の各カードを見る | 正式な論文タイトル、年度・研究室名、「AI要約」バッジと要約の全文（途中で切れない）。説明文に「AIで自動生成」とある |
| B-03 | 掲載可能な研究例が6件を超えるDBでトップページを数回再読み込みする | 少なくとも2種類の論文の組合せが現れ、毎回6件以内・重複なし・テーマが1種類に偏らない。抽選で同じ結果が続いた場合はさらに再読み込みする |
| B-04 | カードを1つクリックする | URLが `/labs/{研究室ID}#thesis-{論文ID}` になり、研究室ページの「関連する修士論文」で、その論文までスクロールされる。その論文だけ背景が薄い緑で左線があり、「選んだ研究例」と表示される。同じ研究室のほかの論文も下に並ぶ |
| B-05 | トップの「もっと見る（N件）」をクリックする | `/research-examples` が開き、Nとクエリ D の件数が一致する。「すべて」が選択中で、複数テーマのカードが並ぶ |
| B-06 | テーマのチップを1つ選ぶ | URLが `?theme=...` になり、カードのテーマバッジにすべてそのテーマが含まれる。件数がチップの括弧内の数と一致する |
| B-07 | クエリAの論文の2つのテーマを順に選ぶ | どちらでもその論文が1回だけ出る |
| B-08 | 「すべて」または「絞り込みを解除」を選ぶ | B-05と同じ件数に戻る |
| B-09 | 「すべて」でクエリBの論文を探す（ブラウザのページ内検索でタイトルを検索） | 見つかる。テーマのチップではどれを選んでも出ない |
| B-10 | クエリCの論文のタイトルをトップと一覧で探す | どちらにも出ない。`/theses` では見つかる |
| B-11 | `/research-examples?theme=99999` を開く | 「このテーマの研究例はありません。」と解除リンク。解除で全件に戻る |
| B-12 | （任意。T-16で自動確認済みのため、開発用DBを触ってよいときだけ）研究例の論文の対応を変えてから、古い画面のカードを押す。終わったら必ず戻す: トップを開いたまま `UPDATE theses SET lab_id = <別の研究室ID> WHERE id = <B-04の論文ID>;` を実行し、カードを押す | 変更後の研究室ページへ移動し、その論文が強調される。確認後に元の `lab_id` に戻す |
| B-13 | 画面幅を狭くする（開発者ツールで幅375px） | カードが1列になり、要約が横にはみ出さない |

## トレーサビリティ

| 仕様 | 計画での対応 | テスト・確認 |
| --- | --- | --- |
| US1 受入1（6件程度、異なるテーマ、入力不要） | D-03、変更7（`index.html`）、変更4（`main.py`） | T-05〜T-08、T-11、T-18、T-20、B-01、B-03 |
| US1 受入2（正式タイトル、要約、自動生成と分かる） | D-08、変更5（カード） | T-11、B-02 |
| US1 受入3（研究室ページで論文を見つけ、ほかの研究も見られる） | D-04、D-05、変更3・8・10 | T-16、T-17、B-04 |
| US2 受入1（「もっと見る」で一覧へ） | 変更6・7 | T-11、T-13、B-05 |
| US2 受入2（最初はテーマ選択なしで複数テーマ） | D-06、変更6 | T-13、B-05 |
| US2 受入3（テーマで絞る・解除で全件） | D-06、D-09、`filter_examples_by_theme` | T-09、T-14、B-06、B-08 |
| US2 受入4（複数テーマはどのテーマでも出る、重複なし） | `collect_theme_labels`、`filter_examples_by_theme` | T-04、T-09、T-14、B-07 |
| 境界: 要約なし・研究室なしは掲載しない、論文一覧で見られる | `is_research_example`、変更6の8、変更9 | T-01、T-02、T-03、B-10 |
| 境界: テーマなしでも絞り込み前に出る | `sort_research_examples`、`filter_examples_by_theme(None)` | T-07、T-09、B-09 |
| 境界: 該当なしは結果なしと解除 | D-09、変更6の7 | T-15、B-11 |
| 境界: 6件未満ならある分だけ | `select_featured_examples` | T-06、T-12 |
| 境界: 対応更新後も誤った研究室へ案内しない | D-04 | T-16、B-12 |
| FR-001 | `is_research_example`、変更4・7 | T-01、T-02、T-11 |
| FR-002 | D-03 | T-05〜T-08、T-18、T-20、B-01、B-03 |
| FR-003 | D-08、変更5 | T-11、T-19、B-02 |
| FR-004 | D-08、変更5・6・7・8 | T-11、T-17、B-02 |
| FR-005 | D-04、D-05 | T-16、T-17、B-04 |
| FR-006 | 変更6・7 | T-11、T-18、B-05 |
| FR-007 | D-06、`filter_examples_by_theme` | T-09、T-14、B-06〜B-08 |
| FR-008 | `filter_examples_by_theme(None)` | T-09、B-09 |
| FR-009 | 変更6の8、変更9、D-04 | T-16、B-10 |
| SC-001 | D-04、D-05 | T-16、T-17、B-04 |
| SC-002 | D-03 | T-05、T-08、T-18、T-20、B-01、B-03 |
| SC-003 | D-06 | T-14、T-15、B-06、B-08 |
| SC-004 | 判定規則、各関数 | T-01〜T-03、T-09、B-07、B-09、B-10 |
| SC-005 | D-08 | T-11、B-02 |

## 互換性・リスク・戻し方

- 互換性: 既存のURLと画面の動きは変わらない。`/labs/{id}` と `/theses` には `id` 属性とクラスが増えるだけ。
- `/` がDBに依存するようになる。Railwayの本番でDBに接続できないときは `/` も500になる（ほかの画面と同じ）。
- 既存の不具合の可能性: `labs/detail.html` 188行の `sort(attribute='year', reverse=True)` は、同じ研究室に年度ありと年度 `None` の論文が混ざるとPythonの比較エラーになる。今回は変更しないが、ブラウザ確認のクエリDで年度なしが0件であることを確かめる。0件でなければ実装を止めて報告する。
- 戻し方: 変更はコードとテンプレートだけなので、該当コミットを戻せばよい。DBの戻しは不要。

## 完了チェックリスト

- [ ] `app/services/research_examples.py` を新規作成し、6関数と `ResearchTheme`、定数2つがある
- [ ] `app/crud.py` に `list_research_example_candidates` と `find_thesis` を追加した。既存関数は変えていない
- [ ] `app/routers/research_examples.py` を新規作成し、`app/main.py` で `include_router` した
- [ ] `app/main.py` の `index` が `featured_examples` と `research_example_count` を渡す
- [ ] `app/templates/research_examples/_card.html` と `index.html` を新規作成した
- [ ] `app/templates/index.html` に研究例セクションを追加した。ヒーローと3ステップは変えていない
- [ ] `labs/detail.html` と `theses/index.html` の論文に `id="thesis-{id}"` がある
- [ ] `style.css` に研究例用のクラスを追加した
- [ ] `tests/test_research_examples.py` にT-01〜T-20があり、`pytest tests -v` が既存18件を含めて全件成功する
- [ ] 品質確認の1〜3を満たす（変更範囲、改行コード、マイグレーション）
- [ ] ブラウザ確認B-01〜B-13（B-12は任意）の結果を記録した（実施日時、環境、確認できなかった項目）
- [ ] [確定した方針](#確定した方針) のQ-01〜Q-05を実装に反映した
- [ ] 仕様と実装の差を記録した（`$speckit-converge` で拾う）

## 確定した方針

| ID | 質問 | 決定 | 理由・影響 |
| --- | --- | --- | --- |
| Q-01 | 実装はどのブランチで行うか。計画作成時のPCは `codex/lab-label-evidence` で、未コミット変更がある | **回答済み（2026-11-26）**: `main` から `001-research-example-discovery` を作成済み。既存の未コミット変更は保持する | 研究例の変更と別件の変更が1つのPRに混ざらないよう、コミット前に差分とステージ対象を確認する |
| Q-02 | トップの6件は毎回同じでよいか、訪問ごとに変えるか | **回答済み（2026-11-26）**: ページ表示ごとにランダムに選び直す（D-03） | 候補の並びを乱数で変え、テーマと研究室の多様性を優先して6件まで選ぶ。テストでは乱数の種を固定する |
| Q-03 | 研究例セクションの位置 | **回答済み（2026-11-26）**: ヒーロー（検索欄・推薦ボタン）のすぐ下。ヒーローと3ステップは変えない | 仕様は「最初に文章入力やテーマ選択を求めない」。検索欄は任意なので残してよいと判断した。研究例をヒーローより上にする、ヒーローを小さくする場合は見た目の変更が大きくなる |
| Q-04 | 研究例のテーマに、確信度の低い（`thesis_labels.confidence` が `low` など）テーマも含めるか | **回答済み（2026-11-26）**: 確信度を問わず含める | 仕様は「そのテーマに登録された論文」。確信度で絞ると、仕様の「テーマ未登録」とは別の理由で絞り込みから漏れる論文が出る |
| Q-05 | 研究室ページの論文の要約にも「AI要約」バッジを付けるか | **回答済み（2026-11-26）**: 付ける | 研究例から研究室ページへ来た学生が同じ要約を見るので、そこでも自動生成と分かるほうが原則Iに合う。変更は1か所 |

## レビュー記録

（実装者の視点で3回レビューし、各回で (a) 名前の実在、(b) 追加調査なしで実装できるか、(c) 仕様の網羅、(d) テストの十分さ を確認した。）

### 1回目

- (a) 計画中のファイルパスをスクリプトで抜き出して照合した。存在しないのは新規と明記した5ファイル（サービス、ルーター、2テンプレート、テスト）だけ。`Thesis`、`ThesisLabel`、`Label` の列、`get_db`、`crud.get_lab`、CSS変数（`--c-primary-lt` など）、引用した行番号（`main.py` 42–44行、`detail.html` 188・192・213–215行、`index.html` 27・29行、`crud.py` 90行）も実物と一致した。
- (b) `uv pip install --python .venv` という不確かな書き方を、カレントの `.venv` を自動で使う書き方に直し、uvの一次情報を添えた。`main.py` のimport追加を「どの行の前後に何を足すか」まで具体化した。
- (b) Spec Kit標準の `research.md` などを別ファイルにしていない理由と、計画内の対応箇所を冒頭に追記した（`$speckit-tasks` の実行者が別ファイルを探さないように）。
- (c)(d) この段階では大きな漏れなし。

### 2回目

- (b) 計画どおりにスナップショットの別コピー（`/workspace/proto-002`、リポジトリ外）へ実装し、T-01〜T-17を書いて既存テストとあわせて実行した（全件成功）。その過程で、サービスの関数が表の説明だけだと実装者の解釈が分かれると判断し、ファイル全体のコードを載せた。
- (b) 一覧のテーマのチップのマークアップを具体的に書いた（選択中の判定と `aria-current` の付け方）。
- (d) テストの書き方の注意を追加した。T-05の入力は `sort_research_examples` を通すこと、HTML属性の並びに依存しない確かめ方、What が読めるテスト名。

### 3回目

- (c) トレーサビリティ表を仕様の全項目（受入条件7、境界5、FR 9、SC 5）と照合した。漏れはなかったが、「6件を超えるときに6件に絞る」と「研究室の偏りを避ける」を直接確かめるテストがなかった。
- (d) T-18（8件 → 6件と「もっと見る（8件）」）、T-19（タイトルの自動エスケープ）、T-20（同じ研究室を後回しにする）を追加し、表と完了チェックリストを更新した。試作コピーで既存18件+新規23件（T-01は4パターン）の計41件が成功した。
- (b) ブラウザ確認のSQL（A〜D）を、開発用DBのコピーに境界ケース（全角スペースだけの要約、研究室なし、テーマなし、同じテーマの重複行）を入れて実行し、構文と判定がPython側の規則と一致することを確かめた。試作をheadless Chromeで開き、トップの6件表示、テーマ絞り込み、研究室ページでの `:target` 強調を目で確認した。未選択のチップに枠がなく押せると分かりにくかったため、`chip-idle` クラスを追加した。
- B-12は開発用DBを書き換えるため任意とし、T-16で同じ点を自動確認することを明記した。

試作はこの計画の実現性を確かめるためのもので、森さんのリポジトリには入れていない。実データ（117件）での表示と森さんのWindows環境での実行は未確認。

### 2026-11-26の方針変更

- 森さんの回答により、トップの6件を固定せず、ページ表示ごとに候補をランダムに並べ替えて選ぶ方式に変更した。D-03、サービスのコード例、T-05〜T-08・T-20、B-03、Q-02を更新した。
- 上記の試作結果と41件成功は変更前の固定選定方式についての記録。ランダム選定方式は、実装時のテストとブラウザ確認で検証する。
- 再レビューで、テーマ未登録の掲載可能な論文が多様性優先の選定から常に漏れる例が見つかった。全候補から最初の1件を選び、残りに多様性を適用するようD-03とT-08を修正した。
