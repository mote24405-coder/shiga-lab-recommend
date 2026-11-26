import re
from html.parser import HTMLParser
from pathlib import Path
from random import Random
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import crud
from app.database import get_db
from app.main import app
from app.services.research_examples import (
    collect_theme_labels,
    count_examples_by_theme,
    filter_examples_by_theme,
    is_research_example,
    select_featured_examples,
    sort_research_examples,
)


def make_label(label_id, name, *, label_type="theme"):
    return SimpleNamespace(id=label_id, label_type=label_type, name=name)


def make_thesis(thesis_id, *, lab_id=1, year=2024, title=None, summary="登録済みの日本語要約", labels=()):
    return SimpleNamespace(
        id=thesis_id,
        lab_id=lab_id,
        lab=SimpleNamespace(id=lab_id, name=f"研究室{lab_id}") if lab_id is not None else None,
        title=title if title is not None else f"論文タイトル{thesis_id}",
        year=year,
        summary_ja=summary,
        thesis_labels=[
            SimpleNamespace(label_id=label.id if label else None, label=label, confidence="low")
            for label in labels
        ],
        raw_labels={},
        author_name=None,
        repo_url=None,
    )


@pytest.fixture
def theses_with_overlapping_themes():
    theme_one = make_label(1, "テーマA")
    theme_two = make_label(2, "テーマB")
    return [
        make_thesis(1, labels=[theme_one, theme_one, theme_two]),
        make_thesis(2, labels=[theme_two]),
        make_thesis(3),
    ]


@pytest.fixture
def client(monkeypatch):
    async def override_db():
        yield None

    monkeypatch.setitem(app.dependency_overrides, get_db, override_db)
    with TestClient(app) as test_client:
        yield test_client


def stub_candidates(monkeypatch, theses):
    async def list_candidates(db):
        return theses

    monkeypatch.setattr(crud, "list_research_example_candidates", list_candidates)


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def attributes_of(self, tag=None, **attrs):
        return [
            attributes
            for element, attributes in self.elements
            if (tag is None or element == tag)
            and all(attributes.get(name) == value for name, value in attrs.items())
        ]


def research_cards(markup):
    return markup.attributes_of("a", **{"data-testid": "research-example"})


@pytest.mark.parametrize("summary", [None, "", "   ", "\u3000\n"])
def test_blank_summary_is_not_a_research_example(summary):
    assert not is_research_example(make_thesis(1, summary=summary))


def test_research_example_requires_a_lab_and_a_summary():
    assert not is_research_example(make_thesis(1, lab_id=None))
    assert is_research_example(make_thesis(2, summary="\u3000要約\n"))


def test_examples_sort_by_newest_year_then_id_and_exclude_ineligible_and_duplicate_theses():
    theses = [
        make_thesis(1, year=2022),
        make_thesis(3, year=None),
        make_thesis(5, year=2024),
        make_thesis(2, year=2024),
        make_thesis(2, year=2024),
        make_thesis(4, lab_id=None),
        make_thesis(6, summary="　"),
    ]

    assert [thesis.id for thesis in sort_research_examples(theses)] == [2, 5, 1, 3]


def test_research_themes_are_unique_theme_labels_in_name_order():
    theme_one = make_label(1, "テーマB")
    theme_two = make_label(2, "テーマA")
    method = make_label(3, "手法", label_type="method")
    thesis = make_thesis(1, labels=[theme_one, theme_two, theme_one, method, None])

    assert collect_theme_labels(thesis) == [theme_two, theme_one]


def test_featured_examples_cover_six_distinct_themes_when_available():
    theses = [make_thesis(thesis_id, labels=[make_label(1, "テーマ1")]) for thesis_id in range(1, 5)]
    theses.extend(
        make_thesis(theme_id + 3, lab_id=theme_id, labels=[make_label(theme_id, f"テーマ{theme_id}")])
        for theme_id in range(2, 8)
    )

    featured = select_featured_examples(sort_research_examples(theses), rng=Random(1))

    assert len(featured) == 6
    assert len({thesis.id for thesis in featured}) == 6
    assert len({thesis.thesis_labels[0].label.id for thesis in featured}) == 6


def test_featured_examples_return_both_candidates_when_only_two_are_eligible():
    theses = [make_thesis(1, labels=[make_label(1, "テーマA")]), make_thesis(2)]

    featured = select_featured_examples(theses, rng=Random(1))

    assert sorted(thesis.id for thesis in featured) == [1, 2]


def test_featured_examples_fill_open_slots_with_repeated_themes_and_untagged_theses():
    theme = make_label(1, "テーマA")
    theses = [make_thesis(thesis_id, labels=[theme]) for thesis_id in range(1, 4)]
    theses.append(make_thesis(4))

    featured = select_featured_examples(theses, rng=Random(5))

    assert sorted(thesis.id for thesis in featured) == [1, 2, 3, 4]


def test_featured_selection_varies_with_seed_and_can_include_an_untagged_thesis():
    theses = [
        make_thesis(thesis_id, lab_id=thesis_id, labels=[make_label(thesis_id, f"テーマ{thesis_id}")])
        for thesis_id in range(1, 7)
    ]
    theses.append(make_thesis(7, lab_id=7))
    input_order = theses.copy()

    selections = [
        select_featured_examples(theses, rng=Random(seed))
        for seed in range(100)
    ]
    combinations = {frozenset(thesis.id for thesis in selection) for selection in selections}

    assert all(len(selection) == 6 for selection in combinations)
    assert len(combinations) > 1
    assert any(7 in selection for selection in combinations)
    assert select_featured_examples(theses, rng=Random(0)) == selections[0]
    assert theses == input_order


@pytest.mark.parametrize(
    ("theme_id", "expected_ids"),
    [(1, [1]), (2, [1, 2]), (None, [1, 2, 3]), (99999, [])],
)
def test_theme_filter_includes_each_matching_thesis_once(
    theses_with_overlapping_themes, theme_id, expected_ids
):
    examples = filter_examples_by_theme(theses_with_overlapping_themes, theme_id)

    assert [thesis.id for thesis in examples] == expected_ids


def test_theme_counts_consider_each_thesis_once_and_rank_more_common_themes_first(
    theses_with_overlapping_themes,
):
    themes = count_examples_by_theme(theses_with_overlapping_themes)

    assert [(theme.id, theme.name, theme.example_count) for theme in themes] == [
        (2, "テーマB", 2),
        (1, "テーマA", 1),
    ]


def test_home_shows_only_eligible_theses_with_titles_summaries_and_links(client, monkeypatch):
    stub_candidates(monkeypatch, [
        make_thesis(1, summary="登録済みの要約A。二文目。"),
        make_thesis(2, summary="登録済みの要約B。"),
        make_thesis(3, summary="　"),
    ])

    response = client.get("/")
    markup = Markup(response.text)

    assert response.status_code == 200
    assert sorted(card["href"] for card in research_cards(markup)) == [
        "/research-examples/1",
        "/research-examples/2",
    ]
    assert markup.attributes_of("a", href="/research-examples")
    assert "論文タイトル1" in response.text
    assert "論文タイトル2" in response.text
    assert "登録済みの要約A。二文目。" in response.text
    assert "登録済みの要約B。" in response.text
    assert response.text.count(">AI要約<") == 2


def test_home_with_no_candidates_explains_that_no_examples_are_available(client, monkeypatch):
    stub_candidates(monkeypatch, [])

    response = client.get("/")

    assert response.status_code == 200
    assert "表示できる研究例はまだありません" in response.text
    assert not research_cards(Markup(response.text))


def test_unfiltered_list_shows_every_eligible_thesis_and_selects_all(
    client, monkeypatch, theses_with_overlapping_themes,
):
    ineligible = make_thesis(4, summary="　", labels=[make_label(99, "掲載可能な研究例がないテーマ")])
    stub_candidates(monkeypatch, [*theses_with_overlapping_themes, ineligible])

    response = client.get("/research-examples")
    markup = Markup(response.text)

    assert response.status_code == 200
    assert [card["data-thesis-id"] for card in research_cards(markup)] == ["1", "2", "3"]
    assert markup.attributes_of("a", href="/research-examples", **{"aria-current": "page"})
    assert "すべて（3件）" in response.text
    assert re.search(r'<[^>]+data-testid="result-count"[^>]*>\s*3件\s*<', response.text)
    assert not markup.attributes_of("a", href="/research-examples?theme=99")


@pytest.mark.parametrize(("theme_id", "expected_ids"), [(1, ["1"]), (2, ["1", "2"])])
def test_list_filters_by_either_theme_of_a_thesis_and_can_reset(
    client, monkeypatch, theses_with_overlapping_themes, theme_id, expected_ids,
):
    stub_candidates(monkeypatch, theses_with_overlapping_themes)
    theme_url = f"/research-examples?theme={theme_id}"

    response = client.get(theme_url)
    markup = Markup(response.text)

    assert response.status_code == 200
    assert [card["data-thesis-id"] for card in research_cards(markup)] == expected_ids
    assert markup.attributes_of("a", href=theme_url, **{"aria-current": "page"})
    reset_links = markup.attributes_of("a", href="/research-examples")
    assert reset_links

    unfiltered = client.get(reset_links[0]["href"])

    assert unfiltered.status_code == 200
    assert len(research_cards(Markup(unfiltered.text))) == 3


@pytest.mark.parametrize("theme_id", [99, 99999])
def test_list_for_a_theme_without_eligible_examples_offers_a_reset(client, monkeypatch, theme_id):
    stub_candidates(monkeypatch, [
        make_thesis(1, labels=[make_label(1, "掲載対象のテーマ")]),
        make_thesis(2, summary="　", labels=[make_label(99, "掲載可能な研究例がないテーマ")]),
    ])

    response = client.get(f"/research-examples?theme={theme_id}")
    markup = Markup(response.text)

    assert response.status_code == 200
    assert markup.attributes_of(**{"data-testid": "empty-state"})
    assert markup.attributes_of("a", href="/research-examples")
    assert not research_cards(markup)


def test_list_rejects_a_non_integer_theme(client):
    response = client.get("/research-examples?theme=invalid")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "theme"]


def test_opening_a_previously_shown_example_uses_the_current_lab_assignment(client, monkeypatch):
    stub_candidates(monkeypatch, [make_thesis(1, lab_id=1), make_thesis(2, lab_id=2)])
    current_theses = {1: make_thesis(1, lab_id=5), 2: make_thesis(2, lab_id=None)}

    async def find_current_thesis(db, thesis_id):
        return current_theses.get(thesis_id)

    monkeypatch.setattr(crud, "find_thesis", find_current_thesis)
    home = client.get("/")
    displayed_links = sorted(card["href"] for card in research_cards(Markup(home.text)))

    assert home.status_code == 200
    assert displayed_links == ["/research-examples/1", "/research-examples/2"]

    with_lab = client.get(displayed_links[0], follow_redirects=False)
    without_lab = client.get(displayed_links[1], follow_redirects=False)
    missing = client.get("/research-examples/99999", follow_redirects=False)

    assert with_lab.status_code == 303
    assert with_lab.headers["location"] == "/labs/5#thesis-1"
    assert without_lab.status_code == 303
    assert without_lab.headers["location"] == "/theses#thesis-2"
    assert missing.status_code == 404


def test_lab_detail_anchors_theses_and_labels_the_ai_summary():
    lab = SimpleNamespace(
        id=1,
        name="研究室1",
        teachers=[],
        lab_labels=[],
        theses=[make_thesis(7)],
    )
    template_dir = Path(__file__).resolve().parents[1] / "app" / "templates"
    environment = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
    )
    html = environment.get_template("labs/detail.html").render(
        lab=lab,
        request=SimpleNamespace(url=SimpleNamespace(path="/labs/1")),
    )
    markup = Markup(html)
    classes = {
        name
        for _, attributes in markup.elements
        for name in attributes.get("class", "").split()
    }

    assert markup.attributes_of(id="thesis-7")
    assert "selected-example-note" in classes
    assert "ai-summary-badge" in classes
    assert "AI要約" in html


def test_home_shows_six_examples_and_links_to_the_full_count(client, monkeypatch):
    stub_candidates(monkeypatch, [
        make_thesis(thesis_id, lab_id=thesis_id, labels=[make_label(thesis_id, f"テーマ{thesis_id}")])
        for thesis_id in range(1, 9)
    ])

    response = client.get("/")
    markup = Markup(response.text)
    cards = research_cards(markup)

    assert response.status_code == 200
    assert len(cards) == 6
    assert len({card["data-thesis-id"] for card in cards}) == 6
    assert markup.attributes_of("a", href="/research-examples")
    assert "もっと見る（8件）" in response.text


def test_list_displays_html_in_a_thesis_title_as_text(client, monkeypatch):
    title = "<script>alert(1)</script>"
    stub_candidates(monkeypatch, [make_thesis(1, title=title)])

    response = client.get("/research-examples")

    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert title not in response.text


def test_featured_examples_prioritize_a_different_lab_when_adding_a_new_theme():
    theses = [
        make_thesis(1, lab_id=1, labels=[make_label(1, "テーマA")]),
        make_thesis(2, lab_id=1, labels=[make_label(2, "テーマB")]),
        make_thesis(3, lab_id=2, labels=[make_label(3, "テーマC")]),
    ]

    featured = select_featured_examples(theses, limit=2, rng=Random(5))

    assert len(featured) == 2
    assert {thesis.lab_id for thesis in featured} == {1, 2}
