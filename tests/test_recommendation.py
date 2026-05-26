"""推薦スコアロジックのユニットテスト。DBなしで動く。"""
import pytest
from app.services.recommendation import _jaccard, _build_explanation


def test_jaccard_full_match():
    assert _jaccard({1, 2}, {1, 2, 3}) == 1.0


def test_jaccard_partial():
    result = _jaccard({1, 2}, {2, 3})
    assert result == 0.5


def test_jaccard_no_match():
    assert _jaccard({1}, {2, 3}) == 0.0


def test_jaccard_empty_user():
    assert _jaccard(set(), {1, 2}) == 0.0


def test_build_explanation():
    exp = _build_explanation("田中研究室", ["機械学習"], ["医療データ"], [])
    assert "田中研究室" in exp
    assert "機械学習" in exp
    assert "医療データ" in exp
