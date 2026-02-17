"""Тесты generator.py — [END] detection, extract phone/telegram, mock generate."""

import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generator import (
    _detect_end,
    extract_phone_from_history,
    extract_telegram_from_history,
    generate,
    generate_stream,
)


# === _detect_end ===

def test_detect_end_no_marker():
    ended, ft = _detect_end("Здравствуйте! Чем могу помочь?")
    assert ended is False
    assert ft is None
    print("  PASS test_detect_end_no_marker")


def test_detect_end_meeting():
    ended, ft = _detect_end("Отлично, запишу вас на онлайн-показ! [END]")
    assert ended is True
    assert ft == "meeting"
    print("  PASS test_detect_end_meeting")


def test_detect_end_materials():
    ended, ft = _detect_end("Отправлю вам презентацию! [END]")
    assert ended is True
    assert ft == "materials"
    print("  PASS test_detect_end_materials")


def test_detect_end_contact():
    ended, ft = _detect_end("Спасибо! Передам специалисту. [END]")
    assert ended is True
    assert ft == "contact"
    print("  PASS test_detect_end_contact")


def test_detect_end_lowercase():
    ended, ft = _detect_end("До связи! [end]")
    assert ended is True
    print("  PASS test_detect_end_lowercase")


# === extract_phone ===

def test_extract_phone_standard():
    history = [
        {"role": "assistant", "content": "Какой номер?"},
        {"role": "user", "content": "+7 999 123-45-67"},
    ]
    assert extract_phone_from_history(history) == "79991234567"
    print("  PASS test_extract_phone_standard")


def test_extract_phone_eight():
    history = [{"role": "user", "content": "8(913)456-78-90"}]
    assert extract_phone_from_history(history) == "79134567890"
    print("  PASS test_extract_phone_eight")


def test_extract_phone_digits():
    history = [{"role": "user", "content": "9991234567"}]
    assert extract_phone_from_history(history) == "79991234567"
    print("  PASS test_extract_phone_digits")


def test_extract_phone_none():
    history = [{"role": "user", "content": "Не хочу давать телефон"}]
    assert extract_phone_from_history(history) is None
    print("  PASS test_extract_phone_none")


def test_extract_phone_skips_assistant():
    history = [
        {"role": "assistant", "content": "Мой номер +7 999 000-00-00"},
        {"role": "user", "content": "Окей"},
    ]
    assert extract_phone_from_history(history) is None
    print("  PASS test_extract_phone_skips_assistant")


# === extract_telegram ===

def test_extract_telegram():
    history = [{"role": "user", "content": "Вот мой телеграм @Ivan_Test123"}]
    assert extract_telegram_from_history(history) == "@Ivan_Test123"
    print("  PASS test_extract_telegram")


def test_extract_telegram_none():
    history = [{"role": "user", "content": "Не использую телеграм"}]
    assert extract_telegram_from_history(history) is None
    print("  PASS test_extract_telegram_none")


# === generate (mock) ===

async def test_generate_mock():
    mock_response = MagicMock()
    mock_response.output_text = "Здравствуйте! RIZALTA — премиальный курорт на Алтае."
    mock_response.output = [MagicMock(stop_reason="end_turn")]
    mock_response.usage = MagicMock(output_tokens=20)

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    with patch("generator.client", mock_client):
        result = await generate(
            system_prompt="Ты — Маргарита",
            history=[],
            message="Привет",
        )

    assert "RIZALTA" in result["answer"]
    assert result["ended"] is False
    assert result["finish_type"] is None
    print("  PASS test_generate_mock")


async def test_generate_with_end():
    mock_response = MagicMock()
    mock_response.output_text = "Спасибо! Запишу на показ. [END]"
    mock_response.output = [MagicMock(stop_reason="end_turn")]
    mock_response.usage = MagicMock(output_tokens=15)

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    with patch("generator.client", mock_client):
        result = await generate(
            system_prompt="Ты — Маргарита",
            history=[],
            message="Давайте созвонимся",
        )

    assert "[END]" not in result["answer"]
    assert result["ended"] is True
    assert result["finish_type"] == "meeting"
    print("  PASS test_generate_with_end")


async def test_generate_error():
    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(side_effect=Exception("API down"))

    with patch("generator.client", mock_client):
        result = await generate(
            system_prompt="Ты — Маргарита",
            history=[],
            message="Привет",
        )

    assert "связь подвисла" in result["answer"]
    assert result["ended"] is False
    print("  PASS test_generate_error")


async def test_generate_empty_response():
    mock_response = MagicMock()
    mock_response.output_text = ""
    mock_response.output = []
    mock_response.usage = MagicMock(output_tokens=0)

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(return_value=mock_response)

    with patch("generator.client", mock_client):
        result = await generate(
            system_prompt="Ты — Маргарита",
            history=[],
            message="...",
        )

    assert len(result["answer"]) > 0  # fallback message
    print("  PASS test_generate_empty_response")


async def run_async():
    await test_generate_mock()
    await test_generate_with_end()
    await test_generate_error()
    await test_generate_empty_response()


if __name__ == "__main__":
    # Sync tests
    sync_tests = [
        test_detect_end_no_marker,
        test_detect_end_meeting,
        test_detect_end_materials,
        test_detect_end_contact,
        test_detect_end_lowercase,
        test_extract_phone_standard,
        test_extract_phone_eight,
        test_extract_phone_digits,
        test_extract_phone_none,
        test_extract_phone_skips_assistant,
        test_extract_telegram,
        test_extract_telegram_none,
    ]
    passed = 0
    for t in sync_tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")

    # Async tests
    asyncio.run(run_async())
    passed += 4

    print(f"\n{passed}/{len(sync_tests) + 4} tests passed")
