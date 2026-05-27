"""同義語展開のユニットテスト。DBなしで動く。"""
from app.services.search_synonyms import expand_query


def test_expand_nlp():
    result = expand_query("nlp")
    assert "自然言語処理" in result
    assert "BERT" in result


def test_expand_keeps_original():
    result = expand_query("機械学習")
    assert "機械学習" in result


def test_expand_unknown_term():
    result = expand_query("謎のキーワード")
    assert "謎のキーワード" in result
    assert len(result) == 1
