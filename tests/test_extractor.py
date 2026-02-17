"""Тесты extractor.py — merge-логика и парсинг (без API)."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractor import merge_extraction_to_state, _normalize_signals, _parse_llm_json


def test_merge_confirmed_overwrites_mentioned():
    state = {
        "goal": "personal", "goal_confidence": "mentioned",
        "budget": None, "budget_confidence": None,
        "payment_type": None, "payment_type_confidence": None,
    }
    extraction = {
        "goal": "investment", "goal_confidence": "confirmed",
        "budget": 10_000_000, "budget_confidence": "confirmed",
    }
    result = merge_extraction_to_state(state, extraction)
    assert result["goal"] == "investment", "confirmed должен перезаписать mentioned"
    assert result["goal_confidence"] == "confirmed"
    assert result["budget"] == 10_000_000
    assert result["budget_confidence"] == "confirmed"


def test_merge_mentioned_does_not_overwrite_confirmed():
    state = {
        "goal": "investment", "goal_confidence": "confirmed",
        "budget": 10_000_000, "budget_confidence": "confirmed",
        "payment_type": None, "payment_type_confidence": None,
    }
    extraction = {
        "goal": "personal", "goal_confidence": "mentioned",
        "budget": 5_000_000, "budget_confidence": "mentioned",
    }
    result = merge_extraction_to_state(state, extraction)
    assert result["goal"] == "investment", "mentioned НЕ должен перезаписать confirmed"
    assert result["goal_confidence"] == "confirmed"
    assert result["budget"] == 10_000_000


def test_merge_simple_fields():
    state = {"preferred_corpus": None, "objection": None}
    extraction = {"preferred_corpus": "family", "objection": "expensive", "sentiment": "negative"}
    result = merge_extraction_to_state(state, extraction)
    assert result["preferred_corpus"] == "family"
    assert result["objection"] == "expensive"
    assert result["sentiment"] == "negative"


def test_merge_special_flags():
    state = {}
    extraction = {"objection": "no_call", "contact_given": True}
    result = merge_extraction_to_state(state, extraction)
    assert result.get("call_refused") is True
    assert result.get("contact_collected") is True


def test_merge_none_skipped():
    state = {"goal": "investment", "goal_confidence": "confirmed"}
    extraction = {"goal": None, "goal_confidence": None}
    result = merge_extraction_to_state(state, extraction)
    assert result["goal"] == "investment", "None не должен перезаписывать"


def test_normalize_signals_missing():
    result = {"goal": "investment"}
    normalized = _normalize_signals(result)
    assert normalized["signals"]["friction"] == 0.3
    assert normalized["signals"]["engagement"] == "medium"


def test_normalize_signals_partial():
    result = {"signals": {"friction": 0.8}}
    normalized = _normalize_signals(result)
    assert normalized["signals"]["friction"] == 0.8
    assert normalized["signals"]["call_readiness"] == 0.5


def test_parse_llm_json_clean():
    raw = '{"goal": "investment"}'
    assert _parse_llm_json(raw) == {"goal": "investment"}


def test_parse_llm_json_markdown():
    raw = '```json\n{"goal": "personal"}\n```'
    assert _parse_llm_json(raw) == {"goal": "personal"}


def test_parse_llm_json_markdown_no_lang():
    raw = '```\n{"budget": 10000000}\n```'
    assert _parse_llm_json(raw) == {"budget": 10000000}


if __name__ == "__main__":
    tests = [
        test_merge_confirmed_overwrites_mentioned,
        test_merge_mentioned_does_not_overwrite_confirmed,
        test_merge_simple_fields,
        test_merge_special_flags,
        test_merge_none_skipped,
        test_normalize_signals_missing,
        test_normalize_signals_partial,
        test_parse_llm_json_clean,
        test_parse_llm_json_markdown,
        test_parse_llm_json_markdown_no_lang,
    ]
    passed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"  PASS {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
        except Exception as e:
            print(f"  ERROR {name}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
