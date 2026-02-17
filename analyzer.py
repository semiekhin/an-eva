"""
analyzer.py — LLM-Analyzer для определения этапа и RAG-запроса
================================================================
Определяет stage диалога + формирует rag_query для поиска примеров.
Responses API, effort: medium.
Адаптация из Sofia-GPT web_api.py для RIZALTA.
"""

import json
import re
import logging
from openai import AsyncOpenAI

from config import (
    OPENAI_API_KEY, ANALYZER_MODEL, ANALYZER_MAX_TOKENS,
    ANALYZER_HISTORY_LIMIT, STAGES,
)
from state_manager import ClientState

log = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

ANALYZER_PROMPT = """Ты — аналитик диалогов продаж курортной недвижимости RIZALTA Resort Belokurikha.

Прочитай диалог и последнее сообщение клиента. Определи:
1. На какой вопрос/тему отвечает клиент?
2. Какой сейчас этап продажи?
3. Какие примеры из базы помогут консультанту ответить?

ЭТАПЫ:
- GREETING — приветствие, начало диалога
- QUALIFICATION — выясняем цель, бюджет, способ оплаты
- PRESENTATION — презентуем конкретные лоты, расчёт ROI, сравнение с депозитом
- MEETING — предлагаем онлайн-показ или отправку материалов
- OBJECTION — клиент возражает (дорого, далеко, стройка, подумаю, не море)
- CLOSING — завершение (контакт получен, показ согласован, прощание)

Ответь СТРОГО в формате JSON:
{
  "client_intent": "краткое описание что имеет в виду клиент",
  "stage": "ОДИН ИЗ ЭТАПОВ",
  "rag_query": "что искать в базе примеров (на русском, 3-7 слов)"
}"""


async def analyze(
    message: str,
    history: list[dict],
    client_state: ClientState,
) -> dict:
    """
    Определяет этап диалога и формирует RAG-запрос.

    Args:
        message: текст сообщения клиента
        history: история диалога
        client_state: текущее состояние клиента

    Returns:
        {"stage": str, "rag_query": str, "client_intent": str}
    """
    state_summary = client_state.summary()

    history_lines = []
    for msg in history[-ANALYZER_HISTORY_LIMIT:]:
        role = "Клиент" if msg["role"] == "user" else "Маргарита"
        history_lines.append(f"{role}: {msg['content']}")
    history_text = "\n".join(history_lines) if history_lines else "Диалог только начался"

    analyzer_input = f"""ИСТОРИЯ ДИАЛОГА:
{history_text}

НОВОЕ СООБЩЕНИЕ КЛИЕНТА:
{message}

ЧТО ИЗВЕСТНО О КЛИЕНТЕ:
{state_summary}"""

    # Дефолты
    stage = "QUALIFICATION"
    rag_query = message
    client_intent = ""

    try:
        response = await client.responses.create(
            model=ANALYZER_MODEL,
            instructions=ANALYZER_PROMPT,
            input=analyzer_input,
            reasoning={"effort": "medium"},
            max_output_tokens=ANALYZER_MAX_TOKENS,
        )
        raw = response.output_text or ""
        json_match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group())
            stage = analysis.get("stage", stage)
            rag_query = analysis.get("rag_query", rag_query)
            client_intent = analysis.get("client_intent", "")

            # Валидация stage
            if stage not in STAGES:
                log.warning(f"[analyzer] unknown stage '{stage}', fallback to QUALIFICATION")
                stage = "QUALIFICATION"

            log.info(f"[analyzer] stage={stage}, query='{rag_query[:40]}', intent='{client_intent[:40]}'")
        else:
            log.warning(f"[analyzer] JSON not found in response, fallback")

    except Exception as e:
        log.warning(f"[analyzer] error: {e}, fallback")

    return {
        "stage": stage,
        "rag_query": rag_query,
        "client_intent": client_intent,
    }
