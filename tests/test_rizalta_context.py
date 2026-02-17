"""Тесты rizalta_context.py — проверка полноты данных."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rizalta_context import RIZALTA_CONTEXT, get_rizalta_context


def test_context_not_empty():
    ctx = get_rizalta_context()
    assert len(ctx) > 500, f"Context too short: {len(ctx)} chars"
    print(f"  PASS test_context_not_empty ({len(ctx)} chars)")


def test_corpuses():
    for corpus in ("Family", "Business", "Digital", "Legend", "Wellness"):
        assert corpus in RIZALTA_CONTEXT, f"Corpus {corpus} missing"
    print("  PASS test_corpuses")


def test_payment_types():
    assert "100% оплата" in RIZALTA_CONTEXT
    assert "Рассрочка 12 мес" in RIZALTA_CONTEXT
    assert "Рассрочка 24 мес" in RIZALTA_CONTEXT
    assert "Ипотека" in RIZALTA_CONTEXT
    assert "4.4%" in RIZALTA_CONTEXT
    print("  PASS test_payment_types")


def test_investment_data():
    assert "2 млн" in RIZALTA_CONTEXT
    assert "70%" in RIZALTA_CONTEXT
    assert "6 лет" in RIZALTA_CONTEXT
    assert "20%" in RIZALTA_CONTEXT
    assert "ZONT HOTEL GROUP" in RIZALTA_CONTEXT
    print("  PASS test_investment_data")


def test_protection():
    assert "214-ФЗ" in RIZALTA_CONTEXT
    assert "эскроу" in RIZALTA_CONTEXT
    assert "Жилищная инициатива" in RIZALTA_CONTEXT
    print("  PASS test_protection")


def test_location():
    assert "Белокуриха" in RIZALTA_CONTEXT
    assert "Алтайский край" in RIZALTA_CONTEXT
    assert "260 солнечных" in RIZALTA_CONTEXT
    assert "радоновые" in RIZALTA_CONTEXT
    print("  PASS test_location")


def test_contacts():
    assert "8 800 551 33 55" in RIZALTA_CONTEXT
    assert "rizaltaresort.ru" in RIZALTA_CONTEXT
    print("  PASS test_contacts")


def test_infrastructure():
    assert "ресторан" in RIZALTA_CONTEXT
    assert "бассейн" in RIZALTA_CONTEXT
    assert "SPA" in RIZALTA_CONTEXT
    assert "Горнолыжный" in RIZALTA_CONTEXT
    print("  PASS test_infrastructure")


def test_safety_disclaimers():
    assert "Не выдумывай" in RIZALTA_CONTEXT
    assert "прогнозируемый" in RIZALTA_CONTEXT
    print("  PASS test_safety_disclaimers")


if __name__ == "__main__":
    tests = [
        test_context_not_empty,
        test_corpuses,
        test_payment_types,
        test_investment_data,
        test_protection,
        test_location,
        test_contacts,
        test_infrastructure,
        test_safety_disclaimers,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
