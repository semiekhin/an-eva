"""Тесты rizalta_prompt_v2.py — промпт, state_summary."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rizalta_prompt_v2 import get_system_prompt, format_state_summary, BOT_NAME
from state_manager import ClientState


def test_bot_name():
    assert BOT_NAME == "Маргарита"
    print("  PASS test_bot_name")


def test_prompt_structure():
    prompt = get_system_prompt("Цель: не известна", "RIZALTA контекст", "RAG примеры")
    assert "Маргарита" in prompt
    assert "RIZALTA" in prompt
    assert "RIZALTA контекст" in prompt
    assert "RAG примеры" in prompt
    assert "[END]" in prompt
    assert "ФОРМАТ ОТВЕТА" in prompt
    print("  PASS test_prompt_structure")


def test_prompt_contains_key_sections():
    prompt = get_system_prompt("", "", "")
    sections = [
        "ТВОЯ ЛИЧНОСТЬ",
        "ТВОЯ ЦЕЛЬ",
        "ЧТО ИЗВЕСТНО О КЛИЕНТЕ",
        "ЧЕКЛИСТ КВАЛИФИКАЦИИ",
        "СТРАТЕГИЯ СБОРА КОНТАКТА",
        "ЭКСПЕРТ, А НЕ ОБСЛУГА",
        "ФИНАНСОВАЯ ЭКСПЕРТИЗА",
        "ТЕХНИКИ ПРОДАЖ",
        "ОСОБЫЕ СЛУЧАИ",
        "ОБЪЕКТНЫЙ КОНТЕКСТ",
        "ФОРМАТ ОТВЕТА",
    ]
    for section in sections:
        assert section in prompt, f"Section '{section}' missing"
    print("  PASS test_prompt_contains_key_sections")


def test_prompt_rizalta_objections():
    prompt = get_system_prompt("", "", "")
    objections = ["Белокуриха далеко", "Дорого", "Стройка", "управлять", "пирамида", "депозит"]
    for obj in objections:
        assert obj in prompt, f"Objection '{obj}' missing"
    print("  PASS test_prompt_rizalta_objections")


def test_prompt_web_strategy():
    prompt = get_system_prompt("", "", "")
    assert "Макс 3 квалификационных вопроса" in prompt
    assert "@telegram" in prompt
    assert "номер телефона" in prompt
    assert "ВЫБОР" in prompt
    print("  PASS test_prompt_web_strategy")


def test_prompt_no_markdown_rule():
    prompt = get_system_prompt("", "", "")
    assert "БЕЗ markdown" in prompt
    assert "звёздочки" in prompt
    print("  PASS test_prompt_no_markdown_rule")


def test_prompt_two_attempts_rule():
    prompt = get_system_prompt("", "", "")
    assert "ПРАВИЛО ДВУХ ПОПЫТОК" in prompt
    print("  PASS test_prompt_two_attempts_rule")


def test_prompt_female_gender():
    prompt = get_system_prompt("", "", "")
    assert "Поняла" in prompt
    assert "Записала" in prompt
    assert "Подготовлю" in prompt
    print("  PASS test_prompt_female_gender")


# === format_state_summary ===

def test_summary_empty():
    state = ClientState(user_id=1)
    summary = format_state_summary(state)
    assert "Цель: не известна" in summary
    assert "Бюджет: не известен" in summary
    assert "Оплата: не известна" in summary
    print("  PASS test_summary_empty")


def test_summary_full():
    state = ClientState(
        user_id=1,
        goal="investment", goal_confidence="confirmed",
        budget=10_000_000, budget_confidence="confirmed",
        payment_type="mortgage", payment_type_confidence="mentioned",
        preferred_corpus="family",
        preferred_area="medium",
    )
    summary = format_state_summary(state)
    assert "инвестиция" in summary
    assert "10 млн" in summary
    assert "ипотека" in summary
    assert "family" in summary
    assert "30-60 м²" in summary
    print("  PASS test_summary_full")


def test_summary_materials_count():
    state = ClientState(user_id=1, materials_request_count=1)
    summary = format_state_summary(state)
    assert "1 ОТКАЗ" in summary

    state2 = ClientState(user_id=1, materials_request_count=2)
    summary2 = format_state_summary(state2)
    assert "2+ ОТКАЗА" in summary2
    print("  PASS test_summary_materials_count")


def test_summary_contact_collected():
    state = ClientState(user_id=1, contact_collected=True)
    summary = format_state_summary(state)
    assert "КОНТАКТ ПОЛУЧЕН" in summary
    print("  PASS test_summary_contact_collected")


def test_summary_meeting_agreed():
    state = ClientState(user_id=1, meeting_agreed=True)
    summary = format_state_summary(state)
    assert "СОГЛАСИЛСЯ НА ПОКАЗ" in summary
    print("  PASS test_summary_meeting_agreed")


if __name__ == "__main__":
    tests = [
        test_bot_name,
        test_prompt_structure,
        test_prompt_contains_key_sections,
        test_prompt_rizalta_objections,
        test_prompt_web_strategy,
        test_prompt_no_markdown_rule,
        test_prompt_two_attempts_rule,
        test_prompt_female_gender,
        test_summary_empty,
        test_summary_full,
        test_summary_materials_count,
        test_summary_contact_collected,
        test_summary_meeting_agreed,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
