"""
extractor.py — извлечение структурированных данных из сообщений
================================================================
Адаптация Sofia-GPT Extractor для RIZALTA Resort Belokurikha.
Один объект → нет location. Добавлены corpus и area.
Использует Responses API (gpt-5.2), effort: medium.
"""

import json
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, EXTRACTOR_MODEL, EXTRACTOR_MAX_TOKENS, EXTRACTOR_HISTORY_LIMIT

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


EXTRACTOR_SYSTEM_PROMPT = """
Ты — модуль извлечения информации из сообщений клиентов консультанта по недвижимости RIZALTA Resort Belokurikha.

ЗАДАЧА: Извлечь информацию из сообщения и вернуть JSON.

═══════════════════════════════════════════════════════════════════════════════
КОНТЕКСТ: RIZALTA Resort Belokurikha — курортный комплекс на Алтае.
Корпуса: Family (20-60 м²), Business (40-120 м²), Digital (20-40 м²).
Один объект — локацию извлекать не нужно.
═══════════════════════════════════════════════════════════════════════════════

СНАЧАЛА ОПРЕДЕЛИ КОНТЕКСТ ОТВЕТА:

1. answered_last_bot_question — клиент ответил на последний вопрос бота?
   - "yes" — да, ответил (даже если "не знаю")
   - "no" — нет, проигнорировал или сменил тему
   - "partial" — частично ответил

2. target_slot — на какой слот был вопрос бота?
   - "goal" / "budget" / "payment_type" / null

3. answer_mode — КАК клиент ответил?
   - "value" — дал конкретное значение
   - "unknown" — не знает
   - "needs_recommendation" — просит совет
   - "refusal" — отказ отвечать
   - "deferred" — отложил
   - "counter_question" — встречный вопрос
   - "off_topic" — не по теме

═══════════════════════════════════════════════════════════════════════════════
КРИТИЧЕСКОЕ ПРАВИЛО — CONFIDENCE И ANSWER_MODE:
═══════════════════════════════════════════════════════════════════════════════

Если answer_mode НЕ "value", то ВСЕ *_confidence = null.

- answer_mode="value" → можно ставить confirmed/mentioned
- Иначе → все *_confidence: null

Исключение: обобщающие ответы ("любой вариант", "без разницы") — это value.

═══════════════════════════════════════════════════════════════════════════════
РАЗЛИЧАЙ ТРИ ТИПА ИНФОРМАЦИИ:
═══════════════════════════════════════════════════════════════════════════════

1. ПОДТВЕРЖДЁННЫЙ ФАКТ (confidence: "confirmed")
   Клиент ЯВНО говорит о СВОИХ намерениях.
   "Мой бюджет 10 млн" → budget: 10000000, budget_confidence: "confirmed"
   "Для инвестиций" → goal: "investment", goal_confidence: "confirmed"

2. УПОМИНАНИЕ (confidence: "mentioned")
   Клиент упоминает, но НЕ подтверждает как свой выбор.
   "Видел у вас за 8 млн" → mentioned_price: 8000000

3. ВОПРОС (question_type)
   "Какие цены?" → question_type: "price"
   "Какая доходность?" → question_type: "profitability"

═══════════════════════════════════════════════════════════════════════════════
ПРАВИЛА ИЗВЛЕЧЕНИЯ ПОЛЕЙ:
═══════════════════════════════════════════════════════════════════════════════

goal (цель покупки):
- "investment" — инвестиция, вложение, заработать, сдавать, доход
- "personal" — для себя, жить, отдыхать, семья
- null — если неясно

budget (бюджет в рублях):
- Число: "10 млн" → 10000000, "до 15" → 15000000
- "от 5 до 10" → 10000000 (верхняя граница)
- null — если не указан

payment_type (способ оплаты):
- "full" — полная оплата, наличные
- "mortgage" — ипотека
- "installment" — рассрочка
- "any" — любой вариант (явный выбор "без разницы")
- null — если не упоминалось

preferred_corpus (предпочтительный корпус):
- "family" — Family
- "business" — Business
- "digital" — Digital
- null — если не указан

preferred_area (предпочтительная площадь):
- "small" — до 30 м² (студия, компактный)
- "medium" — 30-60 м² (однушка, двушка)
- "large" — 60+ м² (большая, просторная)
- null — если не указано

question_type (тип вопроса клиента):
- "price" — цены
- "availability" — наличие, что есть
- "process" — процесс покупки
- "mortgage_rate" — ставки ипотеки
- "profitability" — доходность, ROI, сравнение с депозитом
- "corpus_info" — информация о корпусах
- "location_info" — про Белокуриху / Алтай
- null — не задаёт вопрос

objection (возражение):
- "expensive" — дорого
- "think" — подумаю, не сейчас
- "far" — далеко, Белокуриха далеко, не море
- "construction" — стройка, ждать долго
- "management" — кто будет управлять
- "no_call" — не хочу созвон, только переписка
- null — нет возражения

wants_materials (просит материалы):
- true — явная просьба отправить/скинуть КП, презентацию
- false — всё остальное

contact_given (дал контакт):
- true — дал телефон или @telegram
- false — не дал

meeting_agreed (согласился на онлайн-показ):
- true — явное согласие на показ/созвон
- false — всё остальное

sentiment:
- "positive" / "neutral" / "negative" / "frustrated"

signals (латентные метрики):
- friction (0.0-1.0): уровень сопротивления
- call_readiness (0.0-1.0): готовность к созвону/показу
- engagement: "low" / "medium" / "high"
- urgency: "now" / "week" / "month" / "unclear"

═══════════════════════════════════════════════════════════════════════════════
ФОРМАТ ОТВЕТА — ТОЛЬКО JSON:
═══════════════════════════════════════════════════════════════════════════════

{
  "answered_last_bot_question": "yes" | "no" | "partial",
  "answer_mode": "value" | "unknown" | "needs_recommendation" | "refusal" | "deferred" | "counter_question" | "off_topic" | null,
  "target_slot": "goal" | "budget" | "payment_type" | null,

  "goal": "investment" | "personal" | null,
  "goal_confidence": "confirmed" | "mentioned" | null,

  "budget": 10000000 | null,
  "budget_confidence": "confirmed" | "mentioned" | null,

  "payment_type": "full" | "mortgage" | "installment" | "any" | null,
  "payment_type_confidence": "confirmed" | "mentioned" | null,

  "preferred_corpus": "family" | "business" | "digital" | null,
  "preferred_area": "small" | "medium" | "large" | null,

  "question_type": "price" | "availability" | "process" | "mortgage_rate" | "profitability" | "corpus_info" | "location_info" | null,
  "objection": "expensive" | "think" | "far" | "construction" | "management" | "no_call" | null,
  "wants_materials": true | false,
  "contact_given": true | false,
  "meeting_agreed": true | false,

  "mentioned_price": 10000000 | null,

  "sentiment": "positive" | "neutral" | "negative" | "frustrated",

  "signals": {
    "friction": 0.3,
    "call_readiness": 0.5,
    "engagement": "low" | "medium" | "high",
    "urgency": "now" | "week" | "month" | "unclear"
  }
}

ВЕРНИ ТОЛЬКО JSON, БЕЗ КОММЕНТАРИЕВ И ПОЯСНЕНИЙ.
"""

# Дефолтный результат при ошибке
_EMPTY_EXTRACTION = {
    "answered_last_bot_question": None,
    "answer_mode": None,
    "target_slot": None,
    "goal": None, "goal_confidence": None,
    "budget": None, "budget_confidence": None,
    "payment_type": None, "payment_type_confidence": None,
    "preferred_corpus": None, "preferred_area": None,
    "question_type": None,
    "objection": None,
    "wants_materials": False,
    "contact_given": False,
    "meeting_agreed": False,
    "mentioned_price": None,
    "sentiment": "neutral",
    "signals": {
        "friction": 0.3,
        "call_readiness": 0.5,
        "engagement": "medium",
        "urgency": "unclear",
    },
}


def _normalize_signals(result: dict) -> dict:
    """Гарантирует наличие signals с дефолтами."""
    if "signals" not in result or not isinstance(result.get("signals"), dict):
        result["signals"] = {}
    s = result["signals"]
    s.setdefault("friction", 0.3)
    s.setdefault("call_readiness", 0.5)
    s.setdefault("engagement", "medium")
    s.setdefault("urgency", "unclear")
    return result


def _parse_llm_json(raw: str) -> dict:
    """Парсит JSON из ответа LLM, убирая markdown-обёртку."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


async def extract(message: str, history: list[dict] | None = None) -> dict:
    """
    Извлекает структурированные данные из сообщения клиента.
    Асинхронная версия, использует Responses API.

    Args:
        message: текст сообщения клиента
        history: последние N сообщений [{"role": "user"/"assistant", "content": "..."}]

    Returns:
        dict с извлечёнными полями
    """
    parts = []
    if history:
        parts.append("ИСТОРИЯ ДИАЛОГА (последние сообщения):")
        for msg in history[-EXTRACTOR_HISTORY_LIMIT:]:
            role = "Клиент" if msg["role"] == "user" else "Бот"
            parts.append(f"{role}: {msg['content']}")
        parts.append("")

    parts.append(f"НОВОЕ СООБЩЕНИЕ КЛИЕНТА:\n{message}")
    user_content = "\n".join(parts)

    try:
        response = await client.responses.create(
            model=EXTRACTOR_MODEL,
            instructions=EXTRACTOR_SYSTEM_PROMPT + "\n\nВЕРНИ ТОЛЬКО JSON, БЕЗ MARKDOWN БЛОКОВ.",
            input=user_content,
            max_output_tokens=EXTRACTOR_MAX_TOKENS,
        )
        result = _parse_llm_json(response.output_text)
        return _normalize_signals(result)

    except Exception as e:
        return {**_EMPTY_EXTRACTION, "_error": str(e)}


def merge_extraction_to_state(current_state: dict, extraction: dict) -> dict:
    """
    Мержит результат extraction в текущее состояние.

    Правила:
    - confirmed перезаписывает mentioned
    - mentioned НЕ перезаписывает confirmed
    - Новые значения добавляются
    """
    updated = current_state.copy()

    # Поля с confidence
    for field in ("goal", "budget", "payment_type"):
        new_value = extraction.get(field)
        new_confidence = extraction.get(f"{field}_confidence")

        if new_value is None:
            continue

        current_confidence = updated.get(f"{field}_confidence")

        if new_confidence == "confirmed":
            updated[field] = new_value
            updated[f"{field}_confidence"] = "confirmed"
        elif new_confidence == "mentioned" and current_confidence != "confirmed":
            updated[field] = new_value
            updated[f"{field}_confidence"] = "mentioned"

    # Простые поля (перезаписываем если не None)
    for field in (
        "preferred_corpus", "preferred_area",
        "question_type", "objection", "wants_materials",
        "contact_given", "meeting_agreed",
        "mentioned_price", "sentiment",
    ):
        new_value = extraction.get(field)
        if new_value is not None:
            updated[field] = new_value

    # Специальные флаги
    if extraction.get("objection") == "no_call":
        updated["call_refused"] = True
    if extraction.get("contact_given"):
        updated["contact_collected"] = True

    return updated
