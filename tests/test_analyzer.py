"""Тесты analyzer.py — импорт, структура, mock LLM."""

import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analyzer import analyze, ANALYZER_PROMPT, STAGES
from state_manager import ClientState


def test_prompt_contains_all_stages():
    for stage in STAGES:
        assert stage in ANALYZER_PROMPT, f"Stage {stage} missing from ANALYZER_PROMPT"
    print("  PASS test_prompt_contains_all_stages")


def test_stages_list():
    assert len(STAGES) == 6
    assert "GREETING" in STAGES
    assert "CLOSING" in STAGES
    print("  PASS test_stages_list")


async def test_analyze_with_mock():
    mock_response = MagicMock()
    mock_response.output_text = json.dumps({
        "client_intent": "хочет инвестировать",
        "stage": "QUALIFICATION",
        "rag_query": "инвестиция в курортную недвижимость бюджет",
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    with patch("analyzer.client", mock_client):
        result = await analyze(
            message="Хочу инвестировать до 10 млн",
            history=[
                {"role": "assistant", "content": "Здравствуйте! Чем могу помочь?"},
                {"role": "user", "content": "Хочу инвестировать до 10 млн"},
            ],
            client_state=ClientState(user_id=1),
        )

    assert result["stage"] == "QUALIFICATION"
    assert "rag_query" in result
    assert len(result["rag_query"]) > 0
    assert result["client_intent"] == "хочет инвестировать"
    print("  PASS test_analyze_with_mock")


async def test_analyze_fallback_on_bad_json():
    mock_response = MagicMock()
    mock_response.output_text = "некорректный ответ без json"

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    with patch("analyzer.client", mock_client):
        result = await analyze(
            message="Привет",
            history=[],
            client_state=ClientState(user_id=1),
        )

    # Fallback defaults
    assert result["stage"] == "QUALIFICATION"
    assert result["rag_query"] == "Привет"
    print("  PASS test_analyze_fallback_on_bad_json")


async def test_analyze_fallback_on_error():
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(side_effect=Exception("API error"))

    with patch("analyzer.client", mock_client):
        result = await analyze(
            message="Привет",
            history=[],
            client_state=ClientState(user_id=1),
        )

    assert result["stage"] == "QUALIFICATION"
    print("  PASS test_analyze_fallback_on_error")


async def test_analyze_invalid_stage():
    mock_response = MagicMock()
    mock_response.output_text = json.dumps({
        "client_intent": "test",
        "stage": "INVALID_STAGE",
        "rag_query": "test query",
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    with patch("analyzer.client", mock_client):
        result = await analyze(
            message="test",
            history=[],
            client_state=ClientState(user_id=1),
        )

    assert result["stage"] == "QUALIFICATION"  # fallback
    print("  PASS test_analyze_invalid_stage")


async def run_async_tests():
    await test_analyze_with_mock()
    await test_analyze_fallback_on_bad_json()
    await test_analyze_fallback_on_error()
    await test_analyze_invalid_stage()


if __name__ == "__main__":
    test_prompt_contains_all_stages()
    test_stages_list()
    asyncio.run(run_async_tests())
    print(f"\n6/6 tests passed")
