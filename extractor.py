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
Извлеки информацию из сообщения клиента RIZALTA Resort Belokurikha (курортные апартаменты, Алтай). Верни JSON.

КОНТЕКСТ ОТВЕТА:
- answered_last_bot_question: "yes"/"no"/"partial"
- target_slot: "goal"/"budget"/"payment_type"/null
- answer_mode: "value"/"unknown"/"refusal"/"deferred"/"counter_question"/"off_topic"/null

ПРАВИЛО CONFIDENCE:
Если answer_mode НЕ "value" → все *_confidence = null.
- confirmed = клиент ЯВНО говорит о СВОИХ намерениях ("мой бюджет 10 млн")
- mentioned = упоминает, не подтверждая ("видел у вас за 8 млн")

ПОЛЯ:
- goal: "investment"/"personal"/null, goal_confidence
- budget: число в рублях (10 млн=10000000), budget_confidence
- payment_type: "full"/"mortgage"/"installment"/"any"/null, payment_type_confidence
- preferred_corpus: "family"/"business"/"digital"/null
- preferred_area: "small"(до 30м²)/"medium"(30-60)/"large"(60+)/null
- question_type: "price"/"availability"/"process"/"mortgage_rate"/"profitability"/"corpus_info"/"location_info"/null
- objection: "expensive"/"think"/"far"/"construction"/"management"/"no_call"/null
- wants_materials: true/false
- contact_given: true/false (дал телефон или @telegram)
- meeting_agreed: true/false
- mentioned_price: число/null
- sentiment: "positive"/"neutral"/"negative"/"frustrated"
- urgency: "now"/"week"/"month"/"unclear"

ВЕРНИ ТОЛЬКО JSON:
{"answered_last_bot_question":"...","answer_mode":"...","target_slot":null,"goal":null,"goal_confidence":null,"budget":null,"budget_confidence":null,"payment_type":null,"payment_type_confidence":null,"preferred_corpus":null,"preferred_area":null,"question_type":null,"objection":null,"wants_materials":false,"contact_given":false,"meeting_agreed":false,"mentioned_price":null,"sentiment":"neutral","urgency":"unclear"}
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
    "urgency": "unclear",
}


def _normalize_signals(result: dict) -> dict:
    """Гарантирует наличие urgency с дефолтом."""
    result.setdefault("urgency", "unclear")
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
