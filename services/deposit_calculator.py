#!/usr/bin/env python3
"""
Калькулятор доходности депозита с учётом налогов.
Версия 2.0 — на основе официальной статистики ЦБ РФ.

Источники:
- Ключевая ставка: https://www.cbr.ru/hd_base/keyrate/
- Ставки вкладов топ-10: https://www.cbr.ru/statistics/avgprocstav/
- Прогноз ЦБ на 2026: 13-15% (базовый сценарий)

Дата актуализации: 18.12.2025

Налог на вклады:
- Необлагаемый минимум = 1 000 000 ₽ × макс. ключевая ставка в году
- Ставка налога: 13% (доход до 2,4 млн ₽), 15% (свыше)
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class DepositYearResult:
    """Результат за один год."""
    year: int
    start_balance: float
    deposit_rate: float
    key_rate: float
    gross_interest: float
    tax_free_limit: float
    taxable_income: float
    tax_amount: float
    net_interest: float
    end_balance: float


@dataclass
class DepositResult:
    """Полный результат расчёта депозита."""
    initial_amount: float
    years: int
    scenario_name: str
    yearly_results: List[DepositYearResult]
    total_gross_interest: float
    total_tax: float
    total_net_interest: float
    final_balance: float
    effective_rate: float
    total_roi_pct: float


# =============================================================================
# ОФИЦИАЛЬНЫЕ ДАННЫЕ ЦБ РФ
# =============================================================================

# Исторические данные ключевой ставки (факт)
KEY_RATE_HISTORY = {
    2024: 21.0,  # Пик в октябре-декабре 2024
    2025: 16.5,  # Снижена в октябре 2025
}

# Исторические ставки вкладов топ-10 банков (факт, данные ЦБ)
DEPOSIT_RATE_HISTORY = {
    2024: 22.28,  # Пик II декада декабря 2024
    2025: 15.63,  # I декада декабря 2025
}

# Прогноз ЦБ: средняя ключевая ставка 13-15% в 2026
# Источник: пресс-релиз ЦБ от 24.10.2025

# =============================================================================
# СЦЕНАРИИ ПРОГНОЗА (на основе данных ЦБ)
# =============================================================================

KEY_RATE_SCENARIOS = {
    # Базовый сценарий: прогноз ЦБ 13-15% в 2026, далее постепенное снижение
    "base": {
        2025: 16.5,   # Факт (октябрь 2025)
        2026: 14.0,   # Прогноз ЦБ: 13-15%, берём середину
        2027: 11.0,   # Прогноз: продолжение снижения
        2028: 9.0,
        2029: 8.0,
        2030: 7.5,
        2031: 7.0,
        2032: 7.0,
        2033: 7.0,
        2034: 7.0,
        2035: 7.0,
    },
    # Оптимистичный: быстрое снижение инфляции
    "optimistic": {
        2025: 16.5,
        2026: 12.0,
        2027: 9.0,
        2028: 7.0,
        2029: 6.0,
        2030: 5.5,
        2031: 5.0,
        2032: 5.0,
        2033: 5.0,
        2034: 5.0,
        2035: 5.0,
    },
    # Пессимистичный: инфляция сохраняется
    "pessimistic": {
        2025: 16.5,
        2026: 16.0,
        2027: 14.0,
        2028: 12.0,
        2029: 11.0,
        2030: 10.0,
        2031: 9.0,
        2032: 9.0,
        2033: 8.0,
        2034: 8.0,
        2035: 8.0,
    },
}

# Спред депозита относительно ключевой ставки
# Факт декабрь 2025: 15.63% при ключевой 16.5% = спред -0.87%
# Факт декабрь 2024: 22.28% при ключевой 21% = спред +1.28%
# Среднее: около 0% (депозит ≈ ключевая)
DEPOSIT_SPREAD = {
    "base": -0.5,        # Консервативно: депозит чуть ниже ключевой
    "optimistic": -1.0,  # Банки будут снижать активнее
    "pessimistic": 0.5,  # Конкуренция за вклады
}


def get_deposit_rate(year: int, scenario: str) -> Tuple[float, float]:
    """
    Возвращает (ключевая_ставка, ставка_депозита) для года и сценария.
    """
    key_rates = KEY_RATE_SCENARIOS.get(scenario, KEY_RATE_SCENARIOS["base"])
    spread = DEPOSIT_SPREAD.get(scenario, 0)
    
    key_rate = key_rates.get(year, 7.0)  # fallback
    deposit_rate = max(key_rate + spread, 4.0)  # минимум 4%
    
    return key_rate, deposit_rate


def calculate_tax(
    gross_interest: float,
    max_key_rate: float,
    cumulative_income: float = 0,
) -> Tuple[float, float, float]:
    """
    Рассчитывает налог на доход от вклада.
    
    Правила (2024+):
    - Необлагаемый лимит = 1 млн × макс. ключевая ставка за год
    - 13% с дохода до 2,4 млн ₽
    - 15% с дохода свыше 2,4 млн ₽
    """
    tax_free_limit = 1_000_000 * (max_key_rate / 100)
    taxable_income = max(0, gross_interest - tax_free_limit)
    
    if taxable_income <= 0:
        return tax_free_limit, 0, 0
    
    # Порог для 15% — 2,4 млн (с 2025 года)
    threshold_15pct = 2_400_000
    
    total_income = cumulative_income + taxable_income
    
    if total_income <= threshold_15pct:
        tax_amount = taxable_income * 0.13
    else:
        if cumulative_income >= threshold_15pct:
            tax_amount = taxable_income * 0.15
        else:
            income_at_13 = threshold_15pct - cumulative_income
            income_at_15 = taxable_income - income_at_13
            tax_amount = income_at_13 * 0.13 + max(0, income_at_15) * 0.15
    
    return tax_free_limit, taxable_income, round(tax_amount, 2)


def calculate_deposit(
    amount: float,
    years: int,
    scenario: str = "base",
    reinvest: bool = True,
) -> DepositResult:
    """
    Рассчитывает доходность депозита с учётом налогов.
    
    Args:
        amount: Начальная сумма вклада
        years: Срок в годах (1, 3, 5, 11)
        scenario: "base", "optimistic", "pessimistic"
        reinvest: Капитализация процентов
    """
    yearly_results = []
    balance = float(amount)
    total_gross = 0
    total_tax = 0
    cumulative_taxable = 0
    start_year = 2026  # Текущий год
    
    for i in range(years):
        year = start_year + i
        
        key_rate, deposit_rate = get_deposit_rate(year, scenario)
        
        # Начисленные проценты
        gross_interest = balance * (deposit_rate / 100)
        
        # Налог (макс. ключевая за год ≈ ключевая на начало года)
        tax_free, taxable, tax = calculate_tax(
            gross_interest, key_rate, cumulative_taxable
        )
        cumulative_taxable += taxable
        
        # Чистый доход
        net_interest = gross_interest - tax
        
        # Баланс на конец года
        if reinvest:
            end_balance = balance + net_interest
        else:
            end_balance = balance
        
        yearly_results.append(DepositYearResult(
            year=year,
            start_balance=round(balance, 2),
            deposit_rate=round(deposit_rate, 2),
            key_rate=key_rate,
            gross_interest=round(gross_interest, 2),
            tax_free_limit=round(tax_free, 2),
            taxable_income=round(taxable, 2),
            tax_amount=round(tax, 2),
            net_interest=round(net_interest, 2),
            end_balance=round(end_balance, 2),
        ))
        
        total_gross += gross_interest
        total_tax += tax
        balance = end_balance
    
    total_net = total_gross - total_tax
    effective_rate = (total_net / amount / years) * 100 if years > 0 else 0
    total_roi = (total_net / amount) * 100
    
    scenario_names = {
        "base": "Базовый (прогноз ЦБ)",
        "optimistic": "Оптимистичный",
        "pessimistic": "Пессимистичный",
    }
    
    return DepositResult(
        initial_amount=amount,
        years=years,
        scenario_name=scenario_names.get(scenario, scenario),
        yearly_results=yearly_results,
        total_gross_interest=round(total_gross, 2),
        total_tax=round(total_tax, 2),
        total_net_interest=round(total_net, 2),
        final_balance=round(balance, 2),
        effective_rate=round(effective_rate, 2),
        total_roi_pct=round(total_roi, 2),
    )


def calculate_all_scenarios(amount: float, years: int) -> Dict[str, DepositResult]:
    """Рассчитывает для всех трёх сценариев."""
    return {
        "pessimistic": calculate_deposit(amount, years, "pessimistic"),
        "base": calculate_deposit(amount, years, "base"),
        "optimistic": calculate_deposit(amount, years, "optimistic"),
    }


def fmt(value: float) -> str:
    """Форматирует число с пробелами."""
    return f"{int(round(value)):,}".replace(",", " ")


def format_deposit_result(result: DepositResult, detailed: bool = False) -> str:
    """Форматирует результат для Telegram."""
    lines = []
    
    lines.append(f"🏦 <b>Депозит: {result.scenario_name}</b>")
    lines.append(f"💰 Сумма: {fmt(result.initial_amount)} ₽")
    lines.append(f"📅 Срок: {result.years} лет (2025-{2024 + result.years})")
    lines.append("")
    
    if detailed:
        lines.append("<b>По годам:</b>")
        for yr in result.yearly_results:
            tax_info = f", налог {fmt(yr.tax_amount)} ₽" if yr.tax_amount > 0 else ""
            lines.append(
                f"• {yr.year}: ставка {yr.deposit_rate:.1f}% (ключ. {yr.key_rate:.0f}%), "
                f"+{fmt(yr.gross_interest)} ₽{tax_info}"
            )
        lines.append("")
    
    lines.append("<b>Итого:</b>")
    lines.append(f"• Начислено процентов: {fmt(result.total_gross_interest)} ₽")
    lines.append(f"• Налог (13-15%): -{fmt(result.total_tax)} ₽")
    lines.append(f"• <b>Чистый доход: {fmt(result.total_net_interest)} ₽</b>")
    lines.append("")
    lines.append(f"💵 Итоговый капитал: <b>{fmt(result.final_balance)} ₽</b>")
    lines.append(f"📊 ROI: <b>{result.total_roi_pct:.1f}%</b> за {result.years} лет")
    lines.append(f"📊 Эффективная ставка: <b>{result.effective_rate:.1f}%</b>/год")
    
    return "\n".join(lines)


def format_scenarios_comparison(amount: float, years: int) -> str:
    """Сравнение всех сценариев."""
    scenarios = calculate_all_scenarios(amount, years)
    
    lines = []
    lines.append(f"🏦 <b>Депозит: сравнение сценариев</b>")
    lines.append(f"💰 Сумма: {fmt(amount)} ₽ │ Срок: {years} лет")
    lines.append("")
    
    labels = [
        ("pessimistic", "📈 Пессимистичный (высокие ставки)"),
        ("base", "📊 Базовый (прогноз ЦБ: 13-15% в 2026)"),
        ("optimistic", "📉 Оптимистичный (быстрое снижение)"),
    ]
    
    for key, label in labels:
        r = scenarios[key]
        lines.append(f"<b>{label}</b>")
        lines.append(f"  Капитал: {fmt(r.final_balance)} ₽")
        lines.append(f"  Чистый доход: +{fmt(r.total_net_interest)} ₽ (ROI {r.total_roi_pct:.0f}%)")
        lines.append(f"  Налог: -{fmt(r.total_tax)} ₽")
        lines.append("")
    
    lines.append("<i>Источник: ЦБ РФ (cbr.ru), прогноз на 2026+</i>")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 60)
    print("КАЛЬКУЛЯТОР ДЕПОЗИТА v2.0 (данные ЦБ РФ)")
    print("Дата: 18.12.2025")
    print("=" * 60)
    
    test_amount = 15_000_000
    
    for years in [1, 3, 5, 11]:
        print(f"\n{'─' * 60}")
        print(f"СРОК: {years} лет")
        print("─" * 60)
        print(format_scenarios_comparison(test_amount, years))
        
        # Детальный вывод для базового сценария
        if years == 11:
            print("\n" + "─" * 60)
            print("ДЕТАЛИЗАЦИЯ (базовый сценарий):")
            print("─" * 60)
            result = calculate_deposit(test_amount, years, "base")
            print(format_deposit_result(result, detailed=True))
