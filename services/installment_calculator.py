"""
Единый калькулятор рассрочки RIZALTA.
Все формулы в одном месте, параметры из installment_config.json.

v1.0 (11.01.2026) — Single Source of Truth
"""

import json
from pathlib import Path
from typing import Dict, Any

# Загрузка конфига
CONFIG_PATH = Path(__file__).parent.parent / "data" / "installment_config.json"

def load_config() -> Dict[str, Any]:
    """Загружает конфиг рассрочки."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_service_fee() -> int:
    """Возвращает сервисный сбор."""
    return load_config()["service_fee"]

def calc_12m(price: int) -> Dict[str, Any]:
    """
    Рассчитывает рассрочку на 12 месяцев (0%).
    """
    cfg = load_config()
    service_fee = cfg["service_fee"]
    opts = cfg["programs"]["12m"]["options"]
    
    base = price - service_fee
    
    # ПВ 30% — равные платежи
    pv_30 = int(base * opts["30"]["down_payment_pct"] / 100)
    remaining_30 = base - pv_30
    monthly_30 = int(remaining_30 / 12)
    
    # ПВ 40% — 11 × fixed, остаток на 12-й
    pv_40 = int(base * opts["40"]["down_payment_pct"] / 100)
    remaining_40 = base - pv_40
    fixed_40 = opts["40"]["fixed_monthly"]
    last_40 = remaining_40 - (fixed_40 * opts["40"]["regular_months"])
    
    # ПВ 50% — 11 × fixed, остаток на 12-й
    pv_50 = int(base * opts["50"]["down_payment_pct"] / 100)
    remaining_50 = base - pv_50
    fixed_50 = opts["50"]["fixed_monthly"]
    last_50 = remaining_50 - (fixed_50 * opts["50"]["regular_months"])
    
    return {
        "base": base,
        "pv_30": pv_30, "monthly_30": monthly_30,
        "pv_40": pv_40, "fixed_40": fixed_40, "last_40": last_40,
        "pv_50": pv_50, "fixed_50": fixed_50, "last_50": last_50,
    }

def calc_18m(price: int) -> Dict[str, Any]:
    """
    Рассчитывает рассрочку на 18 месяцев с удорожанием.
    """
    cfg = load_config()
    service_fee = cfg["service_fee"]
    prog = cfg["programs"]["18m"]
    opts = prog["options"]
    
    base = price - service_fee
    balloon_pct = prog["balloon_pct"]
    payment_9 = int(base * balloon_pct / 100)  # 9-й платёж
    
    # ПВ 30% + удорожание
    pv_30 = int(base * opts["30"]["down_payment_pct"] / 100)
    remaining_30 = base - pv_30
    markup_30 = int(remaining_30 * opts["30"]["markup_pct"] / 100)
    total_30 = remaining_30 + markup_30
    monthly_30 = int(total_30 / prog["months"])
    final_price_30 = price + markup_30
    
    # ПВ 40% + удорожание
    pv_40 = int(base * opts["40"]["down_payment_pct"] / 100)
    remaining_40 = base - pv_40
    markup_40 = int(remaining_40 * opts["40"]["markup_pct"] / 100)
    total_40 = remaining_40 + markup_40
    fixed_40 = opts["40"]["fixed_monthly"]
    # 8 × fixed + 9-й + 8 × fixed + 18-й
    paid_40 = (fixed_40 * 8) + payment_9 + (fixed_40 * 8)
    last_40 = total_40 - paid_40
    final_price_40 = price + markup_40
    
    # ПВ 50% + удорожание
    pv_50 = int(base * opts["50"]["down_payment_pct"] / 100)
    remaining_50 = base - pv_50
    markup_50 = int(remaining_50 * opts["50"]["markup_pct"] / 100)
    total_50 = remaining_50 + markup_50
    fixed_50 = opts["50"]["fixed_monthly"]
    # 8 × fixed + 9-й + 8 × fixed + 18-й
    paid_50 = (fixed_50 * 8) + payment_9 + (fixed_50 * 8)
    last_50 = total_50 - paid_50
    final_price_50 = price + markup_50
    
    return {
        "base": base,
        "payment_9": payment_9,
        # 30%
        "pv_30": pv_30, "monthly_30": monthly_30, "markup_30": markup_30, "final_price_30": final_price_30,
        # 40%
        "pv_40": pv_40, "fixed_40": fixed_40, "last_40": last_40, "markup_40": markup_40, "final_price_40": final_price_40,
        # 50%
        "pv_50": pv_50, "fixed_50": fixed_50, "last_50": last_50, "markup_50": markup_50, "final_price_50": final_price_50,
    }

def calc_full(price: int) -> Dict[str, Any]:
    """
    Полный расчёт для лота: 12 мес + 18 мес.
    """
    i12 = calc_12m(price)
    i18 = calc_18m(price)
    
    return {
        "price": price,
        "base": i12["base"],
        "service_fee": get_service_fee(),
        "i12": i12,
        "i18": i18,
    }

def get_texts() -> Dict[str, str]:
    """Возвращает тексты для UI."""
    return load_config()["texts"]

def get_program_description(program: str, option: str) -> str:
    """Возвращает описание программы."""
    cfg = load_config()
    return cfg["programs"][program]["options"][option]["description"]
