"""
generator.py — LLM-генератор ответов Маргариты
=================================================
Responses API, reasoning: high, стриминг SSE.
Определяет [END] маркер для завершения диалога.
"""

import logging
import re
from typing import AsyncGenerator

from openai import AsyncOpenAI

from config import (
    OPENAI_API_KEY, GENERATOR_MODEL, GENERATOR_MAX_TOKENS,
    GENERATOR_HISTORY_LIMIT,
)

log = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Паттерн для поиска телефонов и @username
_PHONE_RE = re.compile(
    r'(?:\+?7|8)[\s\-\(]*(\d{3})[\s\-\)]*(\d{3})[\s\-]*(\d{2})[\s\-]*(\d{2})'
)
_DIGITS_RE = re.compile(r'(?<!\d)(\d{10,11})(?!\d)')
_TG_RE = re.compile(r'@([A-Za-z0-9_]{5,32})')


async def generate(
    system_prompt: str,
    history: list[dict],
    message: str,
) -> dict:
    """
    Генерирует ответ (не стриминг).

    Args:
        system_prompt: полный системный промпт (персона + state + RAG)
        history: история диалога
        message: текущее сообщение клиента

    Returns:
        {"answer": str, "ended": bool, "finish_type": str | None}
    """
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history[-GENERATOR_HISTORY_LIMIT:]
    ]
    messages.append({"role": "user", "content": message})

    try:
        response = await client.responses.create(
            model=GENERATOR_MODEL,
            instructions=system_prompt,
            input=messages,
            reasoning={"effort": "high"},
            max_output_tokens=GENERATOR_MAX_TOKENS,
        )
        answer = response.output_text or ""

        log.info(f"[gen] len={len(answer)}, tokens={getattr(response.usage, 'output_tokens', '?')}")

        # Проверка обрезки
        _check_truncation(response, answer)

        # [END] detection
        ended, finish_type = _detect_end(answer)
        if ended:
            answer = answer.replace("[END]", "").replace("[end]", "").strip()
            log.info(f"[gen] dialog ended, type={finish_type}")

        if not answer.strip():
            answer = "Подскажите, что для вас важнее — посмотреть варианты или обсудить условия?"

        return {"answer": answer, "ended": ended, "finish_type": finish_type}

    except Exception as e:
        log.error(f"[gen] error: {e}")
        return {
            "answer": "Простите, связь подвисла. Напишите ещё раз?",
            "ended": False,
            "finish_type": None,
        }


async def generate_stream(
    system_prompt: str,
    history: list[dict],
    message: str,
) -> AsyncGenerator[dict, None]:
    """
    Генерирует ответ потоком (SSE).

    Yields:
        {"type": "token", "token": str}
        {"type": "done", "ended": bool, "finish_type": str | None}
        {"type": "error", "error": str}
    """
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history[-GENERATOR_HISTORY_LIMIT:]
    ]
    messages.append({"role": "user", "content": message})

    full_text = ""

    try:
        stream = await client.responses.create(
            model=GENERATOR_MODEL,
            instructions=system_prompt,
            input=messages,
            reasoning={"effort": "high"},
            max_output_tokens=GENERATOR_MAX_TOKENS,
            stream=True,
        )

        buffer = ""
        async for event in stream:
            if event.type == "response.output_text.delta":
                delta = event.delta
                full_text += delta
                buffer += delta

                # Держим буфер если может быть [END]
                if "[" in buffer or buffer.endswith("["):
                    # Проверяем полный [END]
                    if "[END]" in buffer or "[end]" in buffer:
                        clean = buffer.replace("[END]", "").replace("[end]", "")
                        if clean:
                            yield {"type": "token", "token": clean}
                        buffer = ""
                    # Ещё не полный — ждём (макс 10 символов буфера)
                    elif len(buffer) > 10:
                        yield {"type": "token", "token": buffer}
                        buffer = ""
                else:
                    yield {"type": "token", "token": buffer}
                    buffer = ""

        # Flush остаток буфера
        if buffer:
            clean = buffer.replace("[END]", "").replace("[end]", "")
            if clean:
                yield {"type": "token", "token": clean}

        # Финализация
        ended, finish_type = _detect_end(full_text)
        log.info(f"[gen:stream] len={len(full_text)}, ended={ended}")

        yield {"type": "done", "ended": ended, "finish_type": finish_type}

    except Exception as e:
        log.error(f"[gen:stream] error: {e}")
        yield {"type": "error", "error": str(e)}


def _detect_end(text: str) -> tuple[bool, str | None]:
    """Определяет [END] маркер и тип завершения."""
    if "[END]" not in text and "[end]" not in text:
        return False, None

    # Определяем тип по содержимому
    lower = text.lower()
    if any(w in lower for w in ("созвон", "показ", "встреч", "звонок")):
        return True, "meeting"
    if any(w in lower for w in ("презентац", "материал", "подборк", "кп")):
        return True, "materials"
    return True, "contact"


def _check_truncation(response, answer: str):
    """Логирует предупреждение при обрезке ответа."""
    try:
        stop_reason = getattr(response.output[-1], "stop_reason", None) if response.output else None
        if stop_reason == "max_tokens":
            log.warning(f"[gen] TRUNCATED: stop=max_tokens, len={len(answer)}")
        elif len(answer) > 50 and not answer.rstrip().endswith(("?", "!", ".", ")", "\u00bb", '"')):
            log.warning(f"[gen] possible truncation: len={len(answer)}")
    except Exception:
        pass


def extract_phone_from_history(history: list[dict]) -> str | None:
    """Ищет номер телефона в сообщениях клиента."""
    for msg in reversed(history):
        if msg.get("role") != "user":
            continue
        match = _PHONE_RE.search(msg["content"])
        if match:
            return "7" + match.group(1) + match.group(2) + match.group(3) + match.group(4)
        # Fallback: 10-11 цифр подряд
        clean = msg["content"].replace(" ", "").replace("-", "")
        dmatch = _DIGITS_RE.search(clean)
        if dmatch:
            d = dmatch.group(1)
            if len(d) == 10:
                return "7" + d
            if len(d) == 11 and d[0] in ("7", "8"):
                return "7" + d[1:]
    return None


def extract_telegram_from_history(history: list[dict]) -> str | None:
    """Ищет @username в сообщениях клиента."""
    for msg in reversed(history):
        if msg.get("role") != "user":
            continue
        match = _TG_RE.search(msg["content"])
        if match:
            return "@" + match.group(1)
    return None
