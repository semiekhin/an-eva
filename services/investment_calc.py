#!/usr/bin/env python3
"""
Инвестиционный калькулятор RIZALTA
Расчёт по формулам из таблицы застройщика
"""

import sqlite3
from pathlib import Path
from typing import Dict, Optional, List

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "properties.db"

EXPENSES_PCT = 0.50

RATE_PER_M2 = {
    2028: 664.18, 2029: 723.88, 2030: 787.31, 2031: 858.21,
    2032: 932.84, 2033: 1014.93, 2034: 1104.48, 2035: 1201.49,
}

OCCUPANCY = {
    2028: 40, 2029: 60, 2030: 70, 2031: 70,
    2032: 70, 2033: 70, 2034: 70, 2035: 70,
}

DAYS_IN_YEAR = {
    2028: 366, 2029: 365, 2030: 365, 2031: 365,
    2032: 366, 2033: 365, 2034: 365, 2035: 365,
}


def get_lot_from_db(code: str) -> Optional[Dict]:
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    code_upper = code.strip().upper()
    table = str.maketrans({"А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "S", "Т": "T"})
    code_latin = code_upper.translate(table)
    cursor.execute("SELECT code, area_m2, price_rub FROM units WHERE code = ? OR code = ? LIMIT 1", (code_upper, code_latin))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"code": row[0], "area": row[1], "price": row[2], "price_m2": int(row[2] / row[1])}
    return None


def calculate_investment(area: float, price_m2: int) -> Dict:
    D6 = area * price_m2
    
    H_values: List[float] = []
    years_data = []
    cumulative_profit = 0
    
    for year in range(2025, 2036):
        sum_prev_H = sum(H_values)
        
        if year == 2025:
            H = D6 * 0.18
        elif year == 2026:
            H = (D6 + sum_prev_H) * 0.20
        elif year == 2027:
            H = (D6 + sum_prev_H) * 0.20
        elif year == 2028:
            H = (D6 + sum_prev_H) * 0.10
        else:
            H = (D6 + sum_prev_H) * 0.088
        
        H_values.append(H)
        
        G = 0
        if year >= 2028:
            rate_m2 = RATE_PER_M2.get(year, 0)
            occupancy = OCCUPANCY.get(year, 0)
            days = DAYS_IN_YEAR.get(year, 365)
            gross_income = days * rate_m2 * area * occupancy / 100
            G = gross_income * (1 - EXPENSES_PCT)
        
        cumulative_profit = cumulative_profit + G + H
        
        K = (G / D6 * 100) if D6 > 0 else 0
        L = (H / D6 * 100) if D6 > 0 else 0
        M = K + L
        
        current_value = D6 + sum(H_values)
        
        years_data.append({
            "year": year,
            "rental_profit": int(G),
            "growth_profit": int(H),
            "cumulative_profit": int(cumulative_profit),
            "current_value": int(current_value),
            "rental_pct": K,
            "growth_pct": L,
            "total_pct": M,
        })
    
    total_rental = sum(y["rental_profit"] for y in years_data)
    total_growth = sum(y["growth_profit"] for y in years_data)
    avg_annual_pct = sum(y["total_pct"] for y in years_data) / len(years_data)
    final_value = D6 + sum(H_values)
    
    return {
        "cost": int(D6),
        "area": area,
        "price_m2": price_m2,
        "years": years_data,
        "total_rental": int(total_rental),
        "total_growth": int(total_growth),
        "total_profit": int(total_rental + total_growth),
        "final_value": int(final_value),
        "avg_annual_pct": avg_annual_pct,
        "roi_pct": (total_rental + total_growth) / D6 * 100 if D6 > 0 else 0,
    }


def fmt(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def format_investment_text(lot_code: str, calc: Dict) -> str:
    """Краткий формат для Telegram."""
    return f"""📊 <b>Инвестиционный расчёт: {lot_code}</b>

📐 Площадь: {calc['area']} м²
💵 Цена за м²: {fmt(calc['price_m2'])} ₽
💰 Стоимость: {fmt(calc['cost'])} ₽

🎯 <b>Итого за 11 лет (2025-2035):</b>

- Прибыль от аренды: {fmt(calc['total_rental'])} ₽
- Прибыль от роста: {fmt(calc['total_growth'])} ₽
- <b>Общая прибыль: {fmt(calc['total_profit'])} ₽</b>

📊 Доходность: <b>{calc['roi_pct']:.0f}%</b> за 11 лет
📊 Средняя годовая: <b>{calc['avg_annual_pct']:.1f}%</b>
🏠 Стоимость в 2035: ~{fmt(calc['final_value'])} ₽

<i>Подробный расчёт в файле Excel</i>"""


if __name__ == "__main__":
    calc = calculate_investment(area=35.5, price_m2=612000)
    print(format_investment_text("В200", calc))
