import pytest

from aiblox_orchestrator.retriever.tsquery import build_tsquery


def test_build_tsquery_web_default():
    expr = build_tsquery("foo bar")
    assert "websearch_to_tsquery" in str(expr)


def test_build_tsquery_phrase():
    expr = build_tsquery("foo bar", mode="phrase")
    assert "phraseto_tsquery" in str(expr)


def test_build_tsquery_strict_guard():
    with pytest.raises(ValueError):
        build_tsquery("foo", mode="strict")
