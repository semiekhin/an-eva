"""
Финансовые расчёты и форматирование.

Содержит:
- Расчёт ROI
- Подбор лота под бюджет
- Портфельные сценарии
- Форматирование сумм
"""

from typing import Dict, Any, List, Optional

from services.data_loader import load_finance, get_finance_defaults, get_min_lot


# ====== Утилиты ======

def fmt_rub(value: float) -> str:
    """Форматирует число как сумму в рублях с пробелами."""
    try:
        return f"{int(round(value)):,}".replace(",", " ") + " ₽"
    except Exception:
        return str(value)


def normalize_unit_code(raw: str) -> str:
    """
    Нормализует код юнита:
    - Верхний регистр
    - Кириллица → латиница (А→A, В→B, ...)
    - Убирает пробелы и спецсимволы
    """
    if not raw:
        return ""
    
    code = str(raw).strip().upper()
    
    # Кириллица → латиница
    table = str.maketrans({
        "А": "A",
        "В": "B",
        "Е": "E",
        "К": "K",
        "М": "M",
        "Н": "H",
        "О": "O",
        "Р": "P",
        "С": "S",
        "Т": "T",
        "У": "Y",
        "Х": "X",
        "№": "",
        " ": "",
    })
    code = code.translate(table)
    
    # Только буквы и цифры
    code = "".join(ch for ch in code if ch.isalnum())
    
    return code


# ====== Поиск юнита ======

def get_unit_by_code(finance: Dict[str, Any], unit_code: str) -> Optional[Dict[str, Any]]:
    """
    Находит юнит по коду из rizalta_finance.json.
    Учитывает кириллицу/латиницу.
    """
    target = normalize_unit_code(unit_code)
    
    # Поиск в units
    units = finance.get("units", []) or []
    for u in units:
        cfg_code = normalize_unit_code(u.get("unit_code", ""))
        if cfg_code == target:
            return u
    
    # Fallback: min_lot
    min_lot = finance.get("min_lot", {}) or {}
    if normalize_unit_code(min_lot.get("unit_code", "")) == target:
        defaults = get_finance_defaults(finance)
        return {
            "unit_code": min_lot.get("unit_code"),
            "title": min_lot.get("title") or "Минимальный лот",
            "area_m2": min_lot.get("area_m2"),
            "price_rub": min_lot.get("price_rub"),
            "daily_rate_rub": defaults.get("daily_rate_rub"),
            "occupancy_pct": defaults.get("occupancy_pct"),
            "expenses_pct": defaults.get("expenses_pct"),
        }
    
    return None


# ====== Расчёт ROI ======

def compute_rent_cashflow(unit: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Рассчитывает арендный денежный поток.
    
    Returns:
        {
            "gross_year_rub": валовая выручка,
            "net_year_rub": чистый доход,
            "roi_year_pct": ROI в %
        }
    """
    defaults = defaults or {}
    
    try:
        price = float(unit.get("price_rub", 0) or 0)
        daily_rate = float(unit.get("daily_rate_rub") or defaults.get("daily_rate_rub", 0) or 0)
        occ = float(unit.get("occupancy_pct") or defaults.get("occupancy_pct", 0) or 0)
        exp = float(unit.get("expenses_pct") or defaults.get("expenses_pct", 0) or 0)
        
        gross = daily_rate * 365 * (occ / 100.0)
        net = gross * (1 - exp / 100.0)
        roi = (net / price * 100.0) if price > 0 else 0.0
        
        return {
            "gross_year_rub": gross,
            "net_year_rub": net,
            "roi_year_pct": roi,
        }
    except Exception as e:
        return {
            "error": str(e),
            "gross_year_rub": 0,
            "net_year_rub": 0,
            "roi_year_pct": 0,
        }


def format_growth_projection(entry_point_rub: float, growth: List[Dict[str, Any]]) -> List[str]:
    """
    Форматирует прогноз капитала по годам.
    """
    lines = []
    try:
        for row in growth:
            year = row.get("year")
            pct = float(row.get("total_return_pct", 0))
            capital = entry_point_rub * (1 + pct / 100.0)
            profit = capital - entry_point_rub
            lines.append(
                f"• {year}: капитал ~{fmt_rub(capital)} "
                f"(прибыль ~{fmt_rub(profit)}, доходность {pct:.2f}%)"
            )
    except Exception as e:
        lines.append(f"(Ошибка расчёта: {e})")
    return lines


# ====== Расчёт точки входа ======

def get_entry_ratio(finance: Dict[str, Any]) -> float:
    """
    Вычисляет коэффициент "точка входа / цена" по минимальному лоту.
    """
    min_lot = get_min_lot(finance)
    
    try:
        ml_price = float(min_lot.get("price_rub", 0) or 0)
        ml_entry = float(min_lot.get("entry_point_rub", 0) or 0)
        
        if ml_price > 0 and ml_entry > 0:
            return ml_entry / ml_price
    except Exception:
        pass
    
    return 0.30  # fallback: 30%


def calc_entry_point(price: float, entry_ratio: float) -> float:
    """Рассчитывает точку входа по цене и коэффициенту."""
    return price * entry_ratio


# ====== Портфельные сценарии ======

def build_portfolio_scenarios(finance: Dict[str, Any], budget_rub: int) -> str:
    """
    Формирует 2-3 портфельных сценария под бюджет инвестора:
    - 1× A209, 1× B210, 1× A305
    - 2× A209, 2× B210, ...
    - Комбинации: 1× A209 + 1× B210, ...
    """
    units_cfg = finance.get("units", []) or []
    defaults = get_finance_defaults(finance)
    entry_ratio = get_entry_ratio(finance)
    min_lot = get_min_lot(finance)
    
    # Собираем данные по ключевым юнитам
    target_codes = {"A209", "B210", "A305"}
    uinfo: Dict[str, Dict[str, Any]] = {}
    
    for u in units_cfg:
        raw_code = str(u.get("unit_code", "")).strip()
        code = normalize_unit_code(raw_code)
        if code not in target_codes:
            continue
        
        price = float(u.get("price_rub", 0) or 0)
        daily_rate = float(u.get("daily_rate_rub") or defaults.get("daily_rate_rub", 0) or 0)
        occ = float(u.get("occupancy_pct") or defaults.get("occupancy_pct", 0) or 0)
        expenses = float(u.get("expenses_pct") or defaults.get("expenses_pct", 0) or 0)
        
        gross_year = daily_rate * 365.0 * (occ / 100.0)
        net_year = gross_year * (1.0 - expenses / 100.0)
        entry_point = price * entry_ratio
        
        uinfo[code] = {
            "code": code,
            "price": price,
            "area_m2": u.get("area_m2"),
            "entry": entry_point,
            "net_year": net_year,
        }
    
    if not uinfo:
        return ""
    
    scenarios: List[Dict[str, Any]] = []
    
    def add_scenario(label: str, composition: Dict[str, int]) -> None:
        total_entry = 0.0
        total_price = 0.0
        total_net = 0.0
        
        for code, cnt in composition.items():
            info = uinfo.get(code)
            if not info:
                return
            total_entry += info["entry"] * cnt
            total_price += info["price"] * cnt
            total_net += info["net_year"] * cnt
        
        if total_entry <= 0 or total_price <= 0:
            return
        
        roi = (total_net / total_price) * 100.0
        scenarios.append({
            "label": label,
            "composition": composition,
            "total_entry": total_entry,
            "total_price": total_price,
            "total_net": total_net,
            "roi": roi,
        })
    
    codes_present = sorted(uinfo.keys())
    
    # Одиночные лоты
    for code in codes_present:
        add_scenario(f"1× {code}", {code: 1})
    
    # Два одинаковых
    for code in codes_present:
        add_scenario(f"2× {code}", {code: 2})
    
    # Комбинации по два разных
    for i, ci in enumerate(codes_present):
        for cj in codes_present[i + 1:]:
            add_scenario(f"1× {ci} + 1× {cj}", {ci: 1, cj: 1})
    
    if not scenarios:
        return ""
    
    # Фильтруем по бюджету: точка входа не сильно выше бюджета
    max_entry = budget_rub * 1.10  # +10% допуск
    suitable = [s for s in scenarios if s["total_entry"] <= max_entry]
    
    if not suitable:
        return ""
    
    # Сортируем: сначала максимально использующий бюджет
    suitable.sort(key=lambda s: s["total_entry"], reverse=True)
    
    top = suitable[:3]
    
    lines: List[str] = []
    lines.append(f"\n\n📦 <b>Варианты портфеля под бюджет {fmt_rub(budget_rub)}</b>")
    
    for idx, sc in enumerate(top, start=1):
        lines.append("")
        lines.append(f"Вариант {idx}: {sc['label']}")
        lines.append(f"• Точка входа по пакету: {fmt_rub(sc['total_entry'])}")
        lines.append(f"• Совокупная цена по договору: {fmt_rub(sc['total_price'])}")
        lines.append(f"• Ориентировочный чистый доход от аренды: ~{fmt_rub(sc['total_net'])}/год")
        lines.append(f"• Доходность по аренде: ~{sc['roi']:.2f}% годовых относительно цены пакета")
        
        if sc["total_price"] > budget_rub:
            lines.append(
                "• Совокупная цена пакета выше заявленного бюджета — можно зайти за счёт "
                "рассрочки или ипотеки."
            )
        else:
            lines.append("• Пакет вписывается в ваш заявленный бюджет по цене.")
    
    return "\n".join(lines)


# ====== Подбор лотов под бюджет ======

def suggest_units_for_budget(budget_rub: int, pay_format: str) -> str:
    """
    Подбирает юниты под бюджет, используя новый инвестиционный план.
    """
    return generate_investment_plan(budget_rub, pay_format)


# ====== Детальный подбор лота (старый формат) ======

def format_lot_recommendation(budget_rub: int, preferred_format: str) -> str:
    """
    Детальный подбор лота с рекомендациями по бюджету.
    """
    finance = load_finance() or {}
    min_lot = finance.get("min_lot", {})
    scenarios = finance.get("investment_scenarios", [])
    
    unit_code = min_lot.get("unit_code", "A209")
    price = min_lot.get("price_rub", 14415000)
    real_price = min_lot.get("real_price_rub", price - 150000)
    entry = min_lot.get("entry_point_rub", 5766000)
    
    # Берём первый сценарий как базовый
    base_scen = scenarios[0] if scenarios else {}
    year1_payment = base_scen.get("year1_monthly_payment_rub", 262000)
    year1_months = base_scen.get("year1_months", 12)
    remaining_share_pct = base_scen.get("remaining_share_after_year1_pct", 40)
    first_year_roi = base_scen.get("first_year_roi_pct", 70)
    payback_years = base_scen.get("payback_years", 4)
    
    total_year1_payments = year1_payment * year1_months
    total_cash_year1 = entry + total_year1_payments
    
    lines: List[str] = []
    lines.append("🧩 <b>Подбор лота под ваш бюджет</b>\n")
    lines.append(f"💰 Ориентировочный бюджет: {fmt_rub(budget_rub)}")
    lines.append(f"⚙️ Предпочитаемый формат: {preferred_format.capitalize()}\n")
    
    # Базовый лот A209
    lines.append("🏡 <b>Минимальный инвестиционный лот: A209</b>")
    lines.append(
        f"• Цена по договору: {fmt_rub(price)} "
        f"(реальная стоимость с учётом включённых услуг ≈ {fmt_rub(real_price)})"
    )
    lines.append(f"• Точка входа: {fmt_rub(entry)} — с этой суммы вы фактически заходите в сделку.")
    lines.append("")
    lines.append("📆 <b>Сценарий входа по A209</b>")
    lines.append(f"• Ежемесячный платёж первый год: {fmt_rub(year1_payment)} × {year1_months} мес.")
    lines.append(f"• За год: {fmt_rub(total_year1_payments)} платежей + точка входа {fmt_rub(entry)}")
    lines.append(f"• Общие вложения за первый год: ≈ {fmt_rub(total_cash_year1)}")
    lines.append(f"• После 1-го года остаётся закрыть около {remaining_share_pct}% стоимости объекта.")
    lines.append("")
    lines.append("📈 <b>Инвест-результат по сценарию A209</b>")
    lines.append(f"• Ожидаемая доходность первого года: около {first_year_roi}% годовых.")
    lines.append(f"• Ориентировочная полная окупаемость вложений: ~{payback_years} года.\n")
    
    # Рекомендации по бюджету
    if budget_rub <= 10_000_000:
        lines.append("🎯 <b>Ваш бюджет до 10 млн ₽</b>")
        lines.append(
            "Это как раз зона, где A209 выглядит оптимальным решением: "
            "минимально возможный рабочий вход с точкой входа 5,766 млн ₽ "
            "и понятной схемой закрытия остатка."
        )
        lines.append(
            "Мы можем настроить сценарий так, чтобы часть платежей закрывалась за счёт аренды, "
            "а вы концентрировались на комфортном ежемесячном платеже."
        )
    elif budget_rub <= 20_000_000:
        lines.append("🎯 <b>Ваш бюджет 10–20 млн ₽</b>")
        lines.append(
            "В этом диапазоне A209 остаётся надёжной базой, "
            "но дополнительно можно рассматривать более крупные лоты (B210, A305) — "
            "они дают больше площади и потенциал по доходу."
        )
    elif budget_rub <= 30_000_000:
        lines.append("🎯 <b>Ваш бюджет 20–30 млн ₽</b>")
        lines.append(
            "В этом диапазоне возможны более продвинутые стратегии: "
            "два лота формата A209 для диверсификации или более крупный объект. "
            "Это уже история про портфельное размещение капитала."
        )
    else:
        lines.append("🎯 <b>Ваш бюджет выше 30 млн ₽</b>")
        lines.append(
            "Это уже уровень, где можно собирать полноценный мини-портфель из нескольких гостиничных номеров, "
            "комбинируя разные корпусы и типы лотов."
        )
    
    lines.append("")
    lines.append(
        "🧮 Формат «ипотека» или «рассрочка» мы подстроим под ваш комфортный ежемесячный платёж."
    )
    lines.append(
        "👉 Логичный следующий шаг — онлайн-показ с менеджером застройщика."
    )
    
    return "\n".join(lines)


def generate_finance_text(unit_code: str, finance: dict) -> str:
    """
    Генерирует динамический текст по рассрочке и ипотеке для юнита.
    Читает данные из JSON.
    """
    from services.data_loader import get_finance_defaults
    
    unit = get_unit_by_code(finance, unit_code)
    if not unit:
        return f"⚠️ Юнит {unit_code} не найден в конфигурации."
    
    title = unit.get("title", f"Гостиничный номер {unit_code}")
    area = unit.get("area_m2", "?")
    price = float(unit.get("price_rub", 0))
    
    # Прогнозы цен из capitalization_projection
    cap = unit.get("capitalization_projection", {}) or {}
    price_2027 = cap.get("price_2027_rub")
    price_2029 = cap.get("price_2029_rub")
    
    # Рассчитываем рост
    growth_pct = 0
    if price > 0 and price_2027:
        growth_pct = round((price_2027 - price) / price * 100)
    
    # Иконка по типу юнита
    icons = {"A209": "💎", "B210": "🔥", "A305": "👑"}
    icon = icons.get(unit_code, "🏡")
    
    # Описание по типу юнита
    subtitles = {
        "A209": "Легкий старт",
        "B210": "Золотая середина", 
        "A305": "Премиум актив"
    }
    subtitle = subtitles.get(unit_code, "")
    
    descriptions = {
        "A209": ("Ваш билет в инвестиции: Компактный и ликвидный номер",
                 "Идеальный лот для первого актива. Самый низкий порог входа, при этом — полноценная доходность и ликвидность при перепродаже."),
        "B210": ("Выбор инвесторов: Максимальный баланс цены и аренды",
                 "Классический гостиничный номер. Самый востребованный формат у туристов, который генерирует стабильно высокий денежный поток (Cash Flow)."),
        "A305": ("Премиальный актив: Семейный люкс с максимальным ростом",
                 "Дефицитный формат. Таких номеров мало, поэтому на них всегда высокий спрос и самая дорогая аренда в пиковые сезоны.")
    }
    desc = descriptions.get(unit_code, ("", ""))
    
    lines = []
    
    # Заголовок
    if subtitle:
        lines.append(f"{icon} <b>{title} ({area} м²) — {subtitle}</b>")
    else:
        lines.append(f"{icon} <b>{title} ({area} м²)</b>")
    lines.append("")
    
    # Описание
    if desc[0]:
        lines.append(f"🏆 <b>{desc[0]}</b>")
        lines.append("")
        lines.append(desc[1])
        lines.append("")
    
    # Экономика
    lines.append("💰 <b>Экономика лота:</b>")
    lines.append(f"▪️ Цена сейчас: <b>{fmt_rub(price)}</b>")
    if price_2027:
        if growth_pct > 0:
            lines.append(f"▪️ Прогноз цены (2027): <b>~{fmt_rub(price_2027)}</b> (+{growth_pct}%)")
        else:
            lines.append(f"▪️ Прогноз цены (2027): <b>~{fmt_rub(price_2027)}</b>")
    lines.append("")
    
    # Бонус
    lines.append("ℹ️ <b>Бонус:</b> В стоимость уже включено оформление и юристы (экономия 150 000 ₽).")
    lines.append("")
    
    # Варианты покупки
    lines.append("👇 <b>Варианты покупки:</b>")
    lines.append("")
    
    # Ипотека
    mortgage_programs = finance.get("mortgage_programs", [])
    if mortgage_programs:
        mp = mortgage_programs[0]
        # Пересчитываем для текущего юнита (пропорционально от A209)
        base_price = float(finance.get("min_lot", {}).get("price_rub", 15251250))
        ratio = price / base_price if base_price > 0 else 1
        
        first_payment = round(float(mp.get("first_payment_rub", 0)) * ratio)
        reduced_payment = round(float(mp.get("reduced_payment_rub", 0)) * ratio)
        promo_rate = mp.get("promo_rate_pct", 4.4)
        
        lines.append("<b>1️⃣ «Умная ипотека» (Хит продаж 🔥)</b>")
        lines.append("Заходите в актив с минимальной нагрузкой на кошелек в первый год.")
        lines.append("")
        lines.append(f"- Первый взнос: ~{fmt_rub(first_payment)}")
        lines.append(f"- Платёж в первый год: всего {fmt_rub(reduced_payment)}/мес (Льготная ставка ~{promo_rate}%)")
        lines.append("- <b>Суть стратегии:</b> Пока идет стройка и актив дорожает, вы платите копейки. Когда включается полный платеж, аренда помогает его гасить.")
        lines.append("")
    
    # Рассрочки из JSON
    installment_programs = finance.get("installment_programs", [])
    installment_notes = finance.get("installment_notes", {})
    
    # Группируем по срокам
    programs_12m = [p for p in installment_programs if p.get("months") == 12]
    programs_18m = [p for p in installment_programs if p.get("months") == 18]
    
    # Рассрочка 12 месяцев
    if programs_12m:
        lines.append("<b>2️⃣ Рассрочка на 12 месяцев (без удорожания)</b>")
        lines.append("")
        for prog in programs_12m:
            pv_pct = prog.get("first_payment_pct", 30)
            pv_rub = round(price * pv_pct / 100)
            comment = prog.get("comment", "")
            fixed_monthly = prog.get("fixed_monthly_rub")
            
            if fixed_monthly:
                lines.append(f"• ПВ {pv_pct}% ({fmt_rub(pv_rub)}): {comment}")
            else:
                remaining = price - pv_rub
                monthly = round(remaining / 12)
                lines.append(f"• ПВ {pv_pct}% ({fmt_rub(pv_rub)}): далее ~{fmt_rub(monthly)}/мес")
        lines.append("")
    
    # Рассрочка 18 месяцев
    if programs_18m:
        lines.append("<b>3️⃣ Рассрочка на 18 месяцев (с удорожанием)</b>")
        lines.append("")
        for prog in programs_18m:
            pv_pct = prog.get("first_payment_pct", 30)
            pv_rub = round(price * pv_pct / 100)
            rate = prog.get("rate_pct", 0)
            comment = prog.get("comment", "")
            
            lines.append(f"• ПВ {pv_pct}% ({fmt_rub(pv_rub)}), удорожание {rate}%: {comment}")
        lines.append("")
    
    # Дополнительные заметки
    quarterly_note = installment_notes.get("quarterly_option")
    discount_note = installment_notes.get("full_payment_discount")
    
    if quarterly_note or discount_note:
        lines.append("<b>💡 Дополнительно:</b>")
        if quarterly_note:
            lines.append(f"• {quarterly_note}")
        if discount_note:
            lines.append(f"• {discount_note}")
        lines.append("")
    
    # Призыв к действию
    lines.append("💬 <b>Хотите график платежей под ваш бюджет?</b>")
    lines.append("Нажмите «Записаться на онлайн-показ» — менеджер сделает персональный расчет за 5 минут.")
    
    return "\n".join(lines)


# ====== Инвестиционный план ======

def fmt_millions(value: float) -> str:
    """Форматирует число в миллионы."""
    m = value / 1_000_000
    if m >= 10:
        return f"{m:.0f} млн"
    return f"{m:.1f} млн"


def generate_investment_pdf(budget_rub: int, chat_id: int, username: str = "") -> Optional[str]:
    """
    Генерирует PDF с инвестиционным планом.
    Возвращает путь к файлу или None при ошибке.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
        import os
        from datetime import datetime
    except ImportError as e:
        print(f"[PDF] reportlab не установлен: {e}")
        return None
    
    finance = load_finance()
    if not finance:
        return None
    
    defaults = get_finance_defaults(finance)
    units_cfg = finance.get("units", []) or []
    entry_ratio = get_entry_ratio(finance)
    
    # Собираем информацию по юнитам
    units_info = {}
    for u in units_cfg:
        code = normalize_unit_code(u.get("unit_code", ""))
        if code in ["A209", "B210", "A305"]:
            price = float(u.get("price_rub", 0))
            entry = price * entry_ratio
            daily = float(u.get("daily_rate_rub") or defaults.get("daily_rate_rub", 0))
            occ = float(u.get("occupancy_pct") or defaults.get("occupancy_pct", 60))
            exp = float(u.get("expenses_pct") or defaults.get("expenses_pct", 50))
            gross = daily * 365 * (occ / 100)
            net = gross * (1 - exp / 100)
            
            units_info[code] = {
                "price": price,
                "entry": entry,
                "net_year": net,
            }
    
    if not units_info:
        return None
    
    # Генерируем портфели
    portfolios = []
    codes = list(units_info.keys())
    
    for total_units in range(1, 11):
        from itertools import combinations_with_replacement
        for combo in combinations_with_replacement(codes, total_units):
            total_entry = sum(units_info[c]["entry"] for c in combo)
            
            if total_entry <= budget_rub * 1.05 and total_entry >= budget_rub * 0.5:
                total_price = sum(units_info[c]["price"] for c in combo)
                total_net = sum(units_info[c]["net_year"] for c in combo)
                
                counts = {}
                for c in combo:
                    counts[c] = counts.get(c, 0) + 1
                
                label_parts = []
                for c in ["A209", "B210", "A305"]:
                    if c in counts:
                        label_parts.append(f"{counts[c]}× {c}")
                label = " + ".join(label_parts)
                
                # Расчёт капитала к 2029 для сортировки
                cap_2029 = total_price * 1.8465 + total_net * 3
                
                portfolios.append({
                    "label": label,
                    "total_entry": total_entry,
                    "total_price": total_price,
                    "total_net": total_net,
                    "usage_pct": (total_entry / budget_rub) * 100,
                    "num_units": total_units,
                    "cap_2029": cap_2029,
                })
    
    # Сортируем по максимальному капиталу к 2029 (убывание)
    portfolios.sort(key=lambda p: p["cap_2029"], reverse=True)
    
    seen = set()
    unique_portfolios = []
    for p in portfolios:
        if p["label"] not in seen:
            seen.add(p["label"])
            unique_portfolios.append(p)
    
    if not unique_portfolios:
        return None
    
    best = unique_portfolios[0]
    
    # Коэффициенты роста
    growth_factors = {
        2025: 1.0339,
        2026: 1.2373,
        2027: 1.5424,
        2028: 1.7569,
        2029: 1.8465,
    }
    
    # Расчёты
    remaining = max(0, best["total_price"] - budget_rub)
    monthly_12 = round(remaining / 12 / 1000) * 1000 if remaining > 0 else 0
    monthly_18 = round(remaining * 1.04 / 18 / 1000) * 1000 if remaining > 0 else 0
    overpay_18 = round((remaining * 0.04) / 1000) * 1000 if remaining > 0 else 0
    
    mortgage = finance.get("mortgage_programs", [])
    mortgage_payment = 0
    if mortgage and remaining > 0:
        mp = mortgage[0]
        base_reduced = float(mp.get("reduced_payment_rub", 54000))
        base_credit = float(mp.get("credit_amount_rub", 10800000))
        ratio = remaining / base_credit if base_credit > 0 else 1
        mortgage_payment = round(base_reduced * ratio / 1000) * 1000
    
    final_value = best["total_price"] * growth_factors[2029]
    total_income = best["total_net"] * 3
    final_capital = final_value + total_income
    profit_pct = ((final_capital - budget_rub) / budget_rub) * 100
    
    # Создаём PDF
    filepath = f"/tmp/rizalta_plan_{chat_id}_{int(datetime.now().timestamp())}.pdf"
    
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # Регистрируем шрифт с поддержкой кириллицы
    try:
        # Пробуем DejaVuSans (обычно есть в Linux)
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        ]
        font_path = None
        font_path_bold = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_path = fp
                font_path_bold = fp.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                break
        
        if font_path and os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("DejaVu", font_path))
            if os.path.exists(font_path_bold):
                pdfmetrics.registerFont(TTFont("DejaVu-Bold", font_path_bold))
            else:
                pdfmetrics.registerFont(TTFont("DejaVu-Bold", font_path))
            FONT = "DejaVu"
            FONT_BOLD = "DejaVu-Bold"
        else:
            # Fallback на встроенный шрифт (без кириллицы)
            FONT = "Helvetica"
            FONT_BOLD = "Helvetica-Bold"
    except Exception as e:
        print(f"[PDF] Ошибка регистрации шрифта: {e}")
        FONT = "Helvetica"
        FONT_BOLD = "Helvetica-Bold"
    
    # Цвета
    DARK_BLUE = HexColor("#1a365d")
    GOLD = HexColor("#d4af37")
    GRAY = HexColor("#4a5568")
    LIGHT_GRAY = HexColor("#e2e8f0")
    
    # Хелперы
    y = height - 40*mm
    
    def draw_text(text, x, size=11, color=GRAY, bold=False):
        nonlocal y
        c.setFillColor(color)
        c.setFont(FONT_BOLD if bold else FONT, size)
        c.drawString(x*mm, y, text)
    
    def next_line(space=6):
        nonlocal y
        y -= space*mm
    
    def draw_line():
        nonlocal y
        c.setStrokeColor(LIGHT_GRAY)
        c.setLineWidth(0.5)
        c.line(20*mm, y, width - 20*mm, y)
        y -= 3*mm
    
    # === HEADER ===
    c.setFillColor(DARK_BLUE)
    c.setFont(FONT_BOLD, 24)
    c.drawString(20*mm, y, "RIZALTA")
    c.setFont(FONT, 10)
    c.drawString(20*mm, y - 6*mm, "Resort Belokurikha")
    
    c.setFillColor(GRAY)
    c.setFont(FONT, 9)
    c.drawRightString(width - 20*mm, y, f"Дата: {datetime.now().strftime('%d.%m.%Y')}")
    if username:
        c.drawRightString(width - 20*mm, y - 5*mm, f"Для: @{username}")
    
    y -= 25*mm
    
    # === TITLE ===
    c.setFillColor(DARK_BLUE)
    c.setFont(FONT_BOLD, 18)
    c.drawString(20*mm, y, "Персональный инвестиционный план")
    y -= 12*mm
    
    draw_line()
    next_line(2)
    
    # === BUDGET & PORTFOLIO ===
    draw_text(f"Ваш бюджет: {budget_rub/1_000_000:.0f} млн ₽", 20, 14, DARK_BLUE, bold=True)
    next_line(8)
    
    draw_text(f"Рекомендуемый портфель: {best['label']}", 20, 12, GOLD, bold=True)
    next_line(6)
    
    num_units = best['num_units']
    units_word = "гостиничный номер" if num_units == 1 else "гостиничный номера" if num_units in [2,3,4] else "гостиничных номеров"
    draw_text(f"{num_units} {units_word} │ Использовано {best['usage_pct']:.0f}% бюджета", 20, 10)
    next_line(10)
    
    draw_line()
    next_line(2)
    
    # === СТРУКТУРА СДЕЛКИ ===
    draw_text("СТРУКТУРА СДЕЛКИ", 20, 12, DARK_BLUE, bold=True)
    next_line(8)
    
    draw_text(f"Общая стоимость портфеля:", 20, 10)
    draw_text(f"{best['total_price']/1_000_000:.0f} млн ₽", 90, 10, DARK_BLUE, bold=True)
    next_line(6)
    
    draw_text(f"Ваш первый взнос:", 20, 10)
    draw_text(f"{budget_rub/1_000_000:.0f} млн ₽", 90, 10, DARK_BLUE, bold=True)
    next_line(6)
    
    if remaining > 0:
        draw_text(f"Остаток к оплате:", 20, 10)
        draw_text(f"{remaining/1_000_000:.0f} млн ₽", 90, 10, DARK_BLUE, bold=True)
        next_line(10)
        
        draw_line()
        next_line(2)
        
        # === ВАРИАНТЫ ОПЛАТЫ ===
        draw_text("ВАРИАНТЫ ОПЛАТЫ ОСТАТКА", 20, 12, DARK_BLUE, bold=True)
        next_line(8)
        
        draw_text("Рассрочка 12 мес (без переплаты):", 20, 10, bold=True)
        draw_text(f"~{monthly_12:,} ₽/мес".replace(",", " "), 90, 10)
        next_line(6)
        
        draw_text("Рассрочка 18 мес (+4%):", 20, 10, bold=True)
        draw_text(f"~{monthly_18:,} ₽/мес, переплата ~{overpay_18:,} ₽".replace(",", " "), 90, 10)
        next_line(6)
        
        if mortgage_payment > 0:
            draw_text("Ипотека (льготный период):", 20, 10, bold=True)
            draw_text(f"1-й год: ~{mortgage_payment:,} ₽/мес".replace(",", " "), 90, 10)
            next_line(6)
    
    next_line(4)
    draw_line()
    next_line(2)
    
    # === ПРОГНОЗ КАПИТАЛА ===
    draw_text("ПРОГНОЗ КАПИТАЛА", 20, 12, DARK_BLUE, bold=True)
    next_line(8)
    
    base_price = best["total_price"]
    annual_net = best["total_net"]
    
    for year in [2025, 2027, 2029]:
        factor = growth_factors.get(year, 1.0)
        portfolio_value = base_price * factor
        
        if year >= 2027:
            years_of_income = year - 2026
            cumulative_income = annual_net * years_of_income
        else:
            cumulative_income = 0
        
        total_capital = portfolio_value + cumulative_income
        
        if year == 2025:
            note = "(старт)"
        elif year == 2027:
            note = "— сдача объекта"
        else:
            note = f"(+{((total_capital - budget_rub) / budget_rub) * 100:.0f}%)"
        
        draw_text(f"{year}:", 20, 10, bold=True)
        draw_text(f"{total_capital/1_000_000:.0f} млн ₽ {note}", 35, 10)
        next_line(6)
    
    next_line(4)
    draw_line()
    next_line(2)
    
    # === ИТОГ ===
    c.setFillColor(GOLD)
    c.setFont(FONT_BOLD, 14)
    c.drawString(20*mm, y, f"ИТОГ К 2029 ГОДУ")
    y -= 10*mm
    
    draw_text(f"Вложено всего: {best['total_price']/1_000_000:.0f} млн ₽", 20, 11)
    next_line(6)
    draw_text(f"Капитал: {final_capital/1_000_000:.0f} млн ₽", 20, 11)
    next_line(6)
    
    c.setFillColor(DARK_BLUE)
    c.setFont(FONT_BOLD, 12)
    profit = final_capital - budget_rub
    c.drawString(20*mm, y, f"Чистая прибыль: +{profit/1_000_000:.0f} млн ₽ (+{profit_pct:.0f}%)")
    y -= 15*mm
    
    # === АЛЬТЕРНАТИВЫ ===
    alternatives = [p for p in unique_portfolios[1:4] if p["label"] != best["label"]]
    
    # Проверяем хватает ли места (нужно ~50mm для альтернатив + футер)
    need_new_page = y < 70*mm and alternatives
    
    if need_new_page:
        # Футер на первой странице
        c.setStrokeColor(LIGHT_GRAY)
        c.line(20*mm, 30*mm, width - 20*mm, 30*mm)
        c.setFillColor(GRAY)
        c.setFont(FONT, 8)
        c.drawString(20*mm, 23*mm, "RIZALTA Resort Belokurikha │ Алтайский край, г. Белокуриха")
        
        # Новая страница
        c.showPage()
        y = height - 40*mm
        
        # Заголовок второй страницы
        c.setFillColor(DARK_BLUE)
        c.setFont(FONT_BOLD, 14)
        c.drawString(20*mm, y, "АЛЬТЕРНАТИВНЫЕ ПОРТФЕЛИ")
        y -= 15*mm
        
        for p in alternatives:
            cap_2029 = p["total_price"] * growth_factors[2029] + p["total_net"] * 3
            c.setFillColor(GRAY)
            c.setFont(FONT, 10)
            c.drawString(20*mm, y, f"• {p['label']}")
            y -= 6*mm
            c.drawString(25*mm, y, f"Капитал к 2029: {cap_2029/1_000_000:.0f} млн ₽")
            y -= 10*mm
    else:
        # Всё на одной странице
        if alternatives:
            draw_line()
            next_line(2)
            draw_text("АЛЬТЕРНАТИВНЫЕ ПОРТФЕЛИ", 20, 11, DARK_BLUE, bold=True)
            next_line(7)
            
            for p in alternatives:
                cap_2029 = p["total_price"] * growth_factors[2029] + p["total_net"] * 3
                draw_text(f"• {p['label']} → к 2029: {cap_2029/1_000_000:.0f} млн ₽", 20, 9)
                next_line(5)
    
    # === FOOTER ===
    c.setStrokeColor(LIGHT_GRAY)
    c.line(20*mm, 30*mm, width - 20*mm, 30*mm)
    
    c.setFillColor(GRAY)
    c.setFont(FONT, 8)
    c.drawString(20*mm, 23*mm, "RIZALTA Resort Belokurikha │ Алтайский край, г. Белокуриха")
    c.drawString(20*mm, 19*mm, "Данный расчёт носит информационный характер и не является публичной офертой.")
    
    c.save()
    
    return filepath


def generate_investment_plan(budget_rub: int, pay_format: str = "") -> str:
    """
    Генерирует полный инвестиционный план под бюджет.
    Максимизирует использование бюджета по точкам входа.
    """
    finance = load_finance()
    if not finance:
        return (
            "Финансовые параметры проекта пока не настроены. "
            "Лучше связаться с менеджером для персонального расчёта."
        )
    
    defaults = get_finance_defaults(finance)
    units_cfg = finance.get("units", []) or []
    entry_ratio = get_entry_ratio(finance)
    
    # Собираем информацию по юнитам
    units_info = {}
    for u in units_cfg:
        code = normalize_unit_code(u.get("unit_code", ""))
        if code in ["A209", "B210", "A305"]:
            price = float(u.get("price_rub", 0))
            entry = price * entry_ratio
            daily = float(u.get("daily_rate_rub") or defaults.get("daily_rate_rub", 0))
            occ = float(u.get("occupancy_pct") or defaults.get("occupancy_pct", 60))
            exp = float(u.get("expenses_pct") or defaults.get("expenses_pct", 50))
            gross = daily * 365 * (occ / 100)
            net = gross * (1 - exp / 100)
            
            cap = u.get("capitalization_projection", {})
            price_2027 = cap.get("price_2027_rub", price * 1.54)
            price_2029 = cap.get("price_2029_rub", price * 1.86)
            
            units_info[code] = {
                "code": code,
                "title": u.get("title", f"Гостиничный номер {code}"),
                "area": u.get("area_m2", 0),
                "price": price,
                "entry": entry,
                "net_year": net,
                "price_2027": price_2027,
                "price_2029": price_2029,
            }
    
    if not units_info:
        return "Данные по гостиничный номерам не найдены."
    
    # Генерируем все возможные комбинации портфелей
    portfolios = []
    codes = list(units_info.keys())
    
    # Максимум 10 юнитов в портфеле
    for total_units in range(1, 11):
        from itertools import combinations_with_replacement
        for combo in combinations_with_replacement(codes, total_units):
            total_entry = sum(units_info[c]["entry"] for c in combo)
            
            # Проверяем что вписывается в бюджет (±5%)
            if total_entry <= budget_rub * 1.05 and total_entry >= budget_rub * 0.5:
                total_price = sum(units_info[c]["price"] for c in combo)
                total_net = sum(units_info[c]["net_year"] for c in combo)
                total_2029 = sum(units_info[c]["price_2029"] for c in combo)
                
                # Подсчитываем количество каждого типа
                counts = {}
                for c in combo:
                    counts[c] = counts.get(c, 0) + 1
                
                # Формируем название
                label_parts = []
                for c in ["A209", "B210", "A305"]:
                    if c in counts:
                        label_parts.append(f"{counts[c]}× {c}")
                label = " + ".join(label_parts)
                
                portfolios.append({
                    "label": label,
                    "counts": counts,
                    "total_entry": total_entry,
                    "total_price": total_price,
                    "total_net": total_net,
                    "total_2029": total_2029,
                    "usage_pct": (total_entry / budget_rub) * 100,
                    "num_units": total_units,
                })
    
    # Коэффициенты роста
    growth_factors = {
        2025: 1.0339,
        2026: 1.2373,
        2027: 1.5424,
        2028: 1.7569,
        2029: 1.8465,
    }
    
    # Рассчитываем капитал к 2029 для каждого портфеля
    for p in portfolios:
        p["cap_2029"] = p["total_price"] * growth_factors[2029] + p["total_net"] * 3
    
    # Сортируем по максимальному капиталу к 2029 (убывание)
    portfolios.sort(key=lambda p: p["cap_2029"], reverse=True)
    
    # Убираем дубликаты по label
    seen = set()
    unique_portfolios = []
    for p in portfolios:
        if p["label"] not in seen:
            seen.add(p["label"])
            unique_portfolios.append(p)
    
    # Берём топ-5
    top_portfolios = unique_portfolios[:5]
    
    if not top_portfolios:
        return f"Не удалось подобрать портфель под бюджет {fmt_rub(budget_rub)}."
    
    # Лучший портфель
    best = top_portfolios[0]
    
    # Начинаем формировать ответ
    lines = []
    lines.append(f"🎯 <b>Ваш инвестиционный план</b>")
    lines.append(f"Бюджет: {fmt_millions(budget_rub)} ₽")
    lines.append("")
    
    # Рекомендуемый портфель
    num_units = best['num_units']
    if num_units == 1:
        units_word = "гостиничный номер"
    elif num_units in [2, 3, 4]:
        units_word = "гостиничный номера"
    else:
        units_word = "гостиничных номеров"
    
    lines.append(f"📦 <b>Рекомендуемый портфель: {best['label']}</b>")
    lines.append(f"{num_units} {units_word} │ Использовано {best['usage_pct']:.0f}% бюджета")
    lines.append("")
    
    # Структура сделки (без ASCII-рамки)
    remaining = best["total_price"] - budget_rub
    if remaining < 0:
        remaining = 0
    
    lines.append("💰 <b>СТРУКТУРА СДЕЛКИ</b>")
    lines.append(f"• Общая стоимость портфеля: {fmt_millions(best['total_price'])} ₽")
    lines.append(f"• Ваш первый взнос: {fmt_millions(budget_rub)} ₽")
    if remaining > 0:
        lines.append(f"• Остаток к оплате: {fmt_millions(remaining)} ₽")
    lines.append("")
    
    # Варианты оплаты остатка
    if remaining > 0:
        lines.append("💳 <b>ВАРИАНТЫ ОПЛАТЫ ОСТАТКА</b>")
        lines.append("")
        
        # Рассрочка 12 мес
        monthly_12 = round(remaining / 12 / 1000) * 1000  # округляем до тысяч
        lines.append("📅 <b>Рассрочка 12 мес</b> (без переплаты)")
        lines.append(f"   ~{fmt_rub(monthly_12)}/мес")
        lines.append("")
        
        # Рассрочка 18 мес
        total_with_rate = remaining * 1.04
        monthly_18 = round(total_with_rate / 18 / 1000) * 1000
        overpay = round((total_with_rate - remaining) / 1000) * 1000
        lines.append("📅 <b>Рассрочка 18 мес</b> (+4% годовых)")
        lines.append(f"   ~{fmt_rub(monthly_18)}/мес, переплата ~{fmt_rub(overpay)}")
        lines.append("")
        
        # Ипотека
        mortgage = finance.get("mortgage_programs", [])
        if mortgage:
            mp = mortgage[0]
            promo_rate = mp.get("promo_rate_pct", 4.4)
            base_reduced = float(mp.get("reduced_payment_rub", 54000))
            base_credit = float(mp.get("credit_amount_rub", 10800000))
            ratio = remaining / base_credit if base_credit > 0 else 1
            reduced_payment = round(base_reduced * ratio / 1000) * 1000
            
            lines.append(f"🏦 <b>Ипотека</b> (льготный период 12 мес)")
            lines.append(f"   1-й год: ~{fmt_rub(reduced_payment)}/мес (ставка {promo_rate}%)")
            lines.append("   Со 2-го года: аренда помогает гасить платёж")
            lines.append("")
    
    # Прогноз капитала
    lines.append("📈 <b>ПРОГНОЗ КАПИТАЛА</b>")
    lines.append("")
    
    base_price = best["total_price"]
    annual_net = best["total_net"]
    
    cumulative_income = 0
    for year in [2025, 2027, 2029]:
        factor = growth_factors.get(year, 1.0)
        portfolio_value = base_price * factor
        
        if year >= 2027:
            years_of_income = year - 2026  # 2027=1год, 2029=3года
            cumulative_income = annual_net * years_of_income
        
        total_capital = portfolio_value + cumulative_income
        profit_pct = ((total_capital - budget_rub) / budget_rub) * 100
        
        if year == 2025:
            lines.append(f"<b>{year}:</b> {fmt_millions(total_capital)} ₽ (старт)")
        elif year == 2027:
            lines.append(f"<b>{year}:</b> {fmt_millions(total_capital)} ₽ — сдача объекта, начало дохода")
        else:
            lines.append(f"<b>{year}:</b> {fmt_millions(total_capital)} ₽ (+{profit_pct:.0f}% от вложенного)")
    
    lines.append("")
    
    # Итог
    final_value = base_price * growth_factors[2029]
    total_income = annual_net * 3
    final_capital = final_value + total_income
    profit_from_budget = final_capital - budget_rub
    
    lines.append("💡 <b>ИТОГ К 2029 ГОДУ</b>")
    lines.append(f"• Вложено всего: {fmt_millions(best['total_price'])} ₽")
    lines.append(f"• Капитал: {fmt_millions(final_capital)} ₽")
    lines.append(f"• Чистая прибыль: <b>+{fmt_millions(profit_from_budget)} ₽</b> (+{(profit_from_budget/budget_rub)*100:.0f}%)")
    lines.append("")
    
    # Альтернативные портфели (без первого, он уже показан)
    alternatives = [p for p in top_portfolios[1:4] if p["label"] != best["label"]]
    if alternatives:
        lines.append("🔥 <b>Альтернативы:</b>")
        for p in alternatives:
            cap_2029 = p["total_price"] * growth_factors[2029] + p["total_net"] * 3
            lines.append(f"• {p['label']} → к 2029: {fmt_millions(cap_2029)} ₽")
        lines.append("")
    
    # Призыв к действию
    lines.append("💬 Хотите обсудить детали с менеджером?")
    
    return "\n".join(lines)
