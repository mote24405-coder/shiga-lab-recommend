---
description: "研究例から研究室を探す機能の実装タスク"
---

# Tasks: トップページの研究例から研究室を探す

**Input**: [spec.md](spec.md) と [plan.md](plan.md)。設計判断・データ定義・画面契約・確認手順は `plan.md` にまとめてある。
**Prerequisites**: 作業ブランチ `001-research-example-discovery` は `main` から作成済み。既存の未コミット変更を保持し、研究例以外の差分をコミット対象に混ぜない。
**Tests**: 仕様の Independent Test と憲章の原則Vに従い、`plan.md` の T-01〜T-20 を `tests/test_research_examples.py` で自動確認する。DBを使わない偽データと依存の差し替えを使う。
**Organization**: 共通の判定・取得処理を先に用意し、US1（トップから研究室へ）、US2（一覧とテーマ絞り込み）の順に実装する。各ストーリーは単独の受入操作で確認する。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 依存する先行タスクの完了後、同時に進められる別ファイルの作業。
- **[US1] / [US2]**: `spec.md` のユーザーストーリー。
- すべてのタスクに、編集または結果を記録するファイルのパスを示す。

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 既存のpytest構成を使い、研究例のサービス・ルート・テンプレートをDBなしで検証できる土台を作る。新しい依存、DBスキーマ、マイグレーションは追加しない。

- [X] T001 `tests/test_research_examples.py` に `SimpleNamespace` の `make_thesis(...)` とラベル生成ヘルパー、`get_db` の空ジェネレーターによる依存差し替え、`app.dependency_overrides` の後片付けを行うfixtureを用意する。ルートテストでは `app.crud` の関数を `monkeypatch` できるようにする

**Checkpoint**: 偽の論文、研究室、テーマを作れ、DBを起動せずに `TestClient` を使える。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: US1とUS2で共有する研究例の判定、テーマ取得、並べ替え、DB読み取りを実装する。

- [X] T002 `tests/test_research_examples.py` に計画T-01〜T-04のテストを先に追加する。要約の `None`・空文字・半角／全角空白、研究室なし、テーマの重複・非theme除外、年度なしを末尾とする年度降順とID重複除去を確認する
- [X] T003 [P] `app/services/research_examples.py` に `ResearchTheme`、定数、`is_research_example`、`collect_theme_labels`、`sort_research_examples` を実装する。`thesis_labels.confidence` では絞らず、`label_type == "theme"` をIDで重複除去する
- [X] T004 [P] `app/crud.py` に `list_research_example_candidates` と `find_thesis` を追加する。候補は `lab_id` と `summary_ja` がNULLでないものに絞り、`Thesis.lab` と `Thesis.thesis_labels -> ThesisLabel.label` を `selectinload` で読み込む。既存CRUDは変更しない

**Checkpoint**: T-01〜T-04が成功し、US1・US2が同じ判定規則と取得処理を使える。

---

## Phase 3: User Story 1 — トップページで研究例に出会う (Priority: P1) 🎯 MVP

**Goal**: トップで最大6件の実在する研究例を見比べ、選んだ論文を現在の研究室ページで特定できる。
**Independent Test**: トップを開き、異なる研究テーマのカードを確認する。再読み込みで候補の組合せが変わり、カードを押すとその時点の研究室の論文がスクロール・強調される。研究室の対応が外れた場合は論文一覧へ進む。

### Tests for User Story 1

- [X] T005 [US1] `tests/test_research_examples.py` に計画T-05〜T-08とT-20を追加する。固定した `Random(seed)` で6件以内・重複なし・テーマ／研究室の多様性を確認し、候補7件の中のテーマ未登録論文にも選択機会があり、種を変えると組合せが変わり、入力順が変わらないことを確かめる
- [X] T006 [US1] `tests/test_research_examples.py` に計画T-11・T-12・T-16〜T-18を追加する。トップの件数・空表示・AI要約表示、クリック時の303と最新の `lab_id`・研究室なし・404、研究室テンプレートのアンカーとバッジを確認する

### Implementation for User Story 1

- [X] T007 [P] [US1] `app/services/research_examples.py` に `select_featured_examples(examples, limit=6, rng=None)` を追加する。候補のコピーをシャッフルし、最初の1件を全候補から選んだ後、未表示のテーマと研究室を優先する計画D-03の3段階で残りを埋める
- [X] T008 [P] [US1] `app/templates/research_examples/_card.html` にトップ・一覧共通のカードマクロを作る。タイトル・年度・研究室・要約全文・AI要約バッジ・themeラベルを表示し、カード全体を `/research-examples/{id}` へのリンクにして `data-testid` と `data-thesis-id` を付ける
- [X] T009 [P] [US1] `app/routers/research_examples.py` にルーターと `GET /research-examples/{thesis_id}` を作る。クリック時に `crud.find_thesis` で読み直し、現在の研究室または `/theses#thesis-{id}` へ303で送り、論文がなければ404を返す
- [X] T010 [US1] `app/main.py` に研究例ルーターの登録とDB依存を追加し、`GET /` で候補を判定・並べ替え・抽選して `featured_examples` と `research_example_count` を `index.html` に渡す
- [X] T011 [US1] `app/templates/index.html` のヒーローと3ステップの間に共通カードマクロを使う研究例セクションを追加する。最大6件、「もっと見る（全件数）」、AI生成の説明、0件時の表示を含める
- [X] T012 [P] [US1] `app/templates/labs/detail.html` の各論文に `id="thesis-{{ thesis.id }}"` と `thesis-item` を付け、対象だけに見える「選んだ研究例」表示と、要約がある論文への「AI要約」バッジを追加する
- [X] T013 [P] [US1] `app/templates/theses/index.html` の各論文に `id="thesis-{{ thesis.id }}"` と `thesis-item` を付け、研究室の対応が外れた論文へのリダイレクト先を作る
- [X] T014 [P] [US1] `app/static/css/style.css` に `ai-summary-badge`、`chip-idle`、`thesis-item:target`、`selected-example-note` のスタイルを追加し、アンカー先の論文をナビの下にスクロール・強調表示できるようにする

**Checkpoint**: T-05〜T-08・T-11・T-12・T-16〜T-18・T-20が成功し、US1の操作だけでトップから研究室の該当論文へ到達できる。

---

## Phase 4: User Story 2 — さらに研究例を探す (Priority: P2)

**Goal**: 全研究例の一覧から、研究例が1件以上あるテーマを選び、絞り込みと解除ができる。
**Independent Test**: `/research-examples` を直接開き、複数テーマの論文がどちらの結果にも1回ずつ現れること、テーマなし論文が「すべて」に現れること、0件のテーマは選択肢に出ず直接URLで指定したときは解除できることを確認する。

### Tests for User Story 2

- [X] T015 [US2] `tests/test_research_examples.py` に計画T-09・T-10・T-13〜T-15・T-19を追加する。複数テーマ・テーマなし・テーマ重複、テーマ別件数、選択・解除・存在しないテーマの空表示、0件テーマをチップに出さないこと、HTML自動エスケープ、整数でない `theme` の422を確認する

### Implementation for User Story 2

- [X] T016 [US2] `app/services/research_examples.py` に `filter_examples_by_theme` と `count_examples_by_theme` を追加する。未指定では全件を元の順で返し、複数テーマの論文を重複させず、件数1件以上のテーマを件数降順・同数は名前順で返す
- [X] T017 [US2] `app/routers/research_examples.py` に `GET /research-examples?theme={id}` を追加する。候補を年度降順に固定し、テーマ別件数・選択中のテーマ・結果件数・絞り込み結果をテンプレートへ渡す。整数でない指定はFastAPIの422に任せる
- [X] T018 [P] [US2] `app/templates/research_examples/index.html` に全件一覧を作る。「すべて」と1件以上あるテーマだけのチップ、選択中の `aria-current="page"`、結果件数、共通カード、空表示と解除リンク、AI要約の説明、既存 `/theses` への案内を含める

**Checkpoint**: T-09・T-10・T-13〜T-15・T-19が成功し、一覧を直接開いてテーマ選択から解除まで操作できる。

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: 既存機能との互換性、実データでの見え方、記録を確認する。

- [X] T019 `tests/test_research_examples.py` と `tests/` の全テストを、`requirements.txt` を入れたuv管理の `.venv` で実行し、新規T-01〜T-20と既存テストの結果を `specs/001-research-example-discovery/verification.md` に記録する
- [X] T020 `specs/001-research-example-discovery/verification.md` に、`plan.md` のブラウザ確認B-01〜B-13（B-12は専用開発DBで実施可能な場合のみ、変更後は元の研究室IDへ戻す）の日時・環境・結果を記録する。トップの再読み込み、複数テーマ、0件、375px幅、クリック後の強調表示を確認する
- [X] T021 `specs/001-research-example-discovery/verification.md` に、`app/`・`tests/`・`specs/001-research-example-discovery/` の変更範囲とCRLF維持、`alembic upgrade head` の結果、未コミットの別件ファイルをコミット対象に含めていないことを記録する。実行できない確認は理由を明記する

**Checkpoint**: 仕様のSC-001〜SC-005と計画の完了チェックリストを照合できる記録がある。

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 → Phase 2 → Phase 3（US1）→ Phase 4（US2）→ Phase 5。
- T002・T005・T006・T015のテストを対応する実装より先に書く。T003・T004はT002の後、T007〜T014はT005・T006の後に着手する。
- T009はT004、T010はT009、T011はT008とT010、T017はT016、T019〜T021は両ストーリーの完成に依存する。

### User Story Dependencies

- **US1 (P1)**: Phase 2の判定・取得処理に依存し、単独でトップから研究室への経路を完成できる。
- **US2 (P2)**: Phase 2に加え、US1で作る共通カード `app/templates/research_examples/_card.html` とルーター `app/routers/research_examples.py` を使う。受入確認は一覧のURLから単独で行える。

### Parallel Opportunities

- T003（サービス）とT004（CRUD）はT002の後に別ファイルで進められる。
- T007（抽選）、T008（カード）、T009（リダイレクト）、T012（研究室）、T013（論文一覧）、T014（CSS）は先行テストの後に別ファイルで進められる。
- T018（一覧テンプレート）はT015の後、T016（絞り込みサービス）と別ファイルで進められる。

## Parallel Example: User Story 1

```text
T005・T006のテストを用意した後:
  T007 app/services/research_examples.py で抽選を実装
  T008 app/templates/research_examples/_card.html で共通カードを作成
  T009 app/routers/research_examples.py でリダイレクトを実装
  T012 app/templates/labs/detail.html で論文の強調表示を追加
```

## Parallel Example: User Story 2

```text
T015のテストを用意した後:
  T016 app/services/research_examples.py でテーマ絞り込み・件数を実装
  T018 app/templates/research_examples/index.html で一覧画面を作成
T016完了後にT017 app/routers/research_examples.py で一覧ルートを接続
```

## Implementation Strategy

1. Phase 1・2で共通処理を用意する。
2. Phase 3のUS1を完成させ、トップから研究室の該当論文までをMVPとして独立確認する。
3. Phase 4のUS2を追加し、一覧の直接アクセスとテーマ選択を独立確認する。
4. Phase 5で全テストとブラウザ確認を行い、`verification.md` に実測結果と未確認項目を残す。
