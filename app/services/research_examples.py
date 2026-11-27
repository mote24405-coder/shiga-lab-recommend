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
    return sorted(unique.values(), key=lambda thesis: (thesis.year is None, -(thesis.year or 0), thesis.id))


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
    return [
        thesis for thesis in examples
        if any(label.id == theme_id for label in collect_theme_labels(thesis))
    ]


def count_examples_by_theme(examples: Sequence[Thesis]) -> list[ResearchTheme]:
    names: dict[int, str] = {}
    counts: dict[int, int] = {}
    for thesis in examples:
        for label in collect_theme_labels(thesis):
            names[label.id] = label.name
            counts[label.id] = counts.get(label.id, 0) + 1
    themes = [
        ResearchTheme(id=theme_id, name=names[theme_id], example_count=example_count)
        for theme_id, example_count in counts.items()
    ]
    return sorted(themes, key=lambda theme: (-theme.example_count, theme.name))
