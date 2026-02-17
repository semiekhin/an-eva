"""
message_processor.py — единый процессор сообщений АН Эва
=========================================================
Пайплайн: Extractor → State → Signals.
Решения по ответу принимает LLM-Генератор (не процессор).
Адаптация Sofia-GPT v3.0 для RIZALTA.
"""

import logging
from datetime import datetime

from extractor import extract, merge_extraction_to_state
from state_manager import StateManager, ClientState

log = logging.getLogger(__name__)


async def process_message(
    user_id: int,
    message: str,
    history: list[dict],
    state_manager: StateManager,
) -> dict:
    """
    Обработка сообщения: Extractor → State → Signals.

    Args:
        user_id: ID пользователя
        message: текст сообщения
        history: история [{"role": "user"/"assistant", "content": "..."}]
        state_manager: экземпляр StateManager

    Returns:
        {"client_state": ClientState, "extraction": dict}
    """
    log.info(f"[process] user={user_id}: {message[:60]}...")

    # 1. Текущее состояние
    client_state = await state_manager.get_state(user_id)

    # 2. Если диалог был завершён [END], но клиент написал снова — сбрасываем
    if client_state.dialog_finished:
        await state_manager.update_state(user_id, {
            "dialog_finished": False,
            "finish_type": None,
        })
        client_state.dialog_finished = False
        client_state.finish_type = None
        log.info(f"[process] dialog_finished reset for user={user_id}")

    # 3. Extractor — извлекаем факты из сообщения
    history_for_extractor = [{"role": m["role"], "content": m["content"]} for m in history]
    extraction = await extract(message, history_for_extractor)
    log.info(f"[process] extraction: goal={extraction.get('goal')}, budget={extraction.get('budget')}, "
             f"objection={extraction.get('objection')}, sentiment={extraction.get('sentiment')}")

    # 4. Merge extraction → state
    state_updates = merge_extraction_to_state(client_state.to_dict(), extraction)
    client_state = await state_manager.update_state(user_id, state_updates)

    # 5. Signals — латентные метрики
    signals = extraction.get("signals", {})
    if signals:
        await state_manager.update_state(user_id, {
            "friction": signals.get("friction", 0.3),
            "call_readiness": signals.get("call_readiness", 0.5),
            "engagement": signals.get("engagement", "medium"),
            "urgency": signals.get("urgency", "unclear"),
        })

    # 6. Счётчик запросов материалов
    if extraction.get("wants_materials"):
        new_count = (client_state.materials_request_count or 0) + 1
        await state_manager.update_state(user_id, {"materials_request_count": new_count})
        log.info(f"[process] materials_request_count → {new_count}")

    # 7. Очищаем временные флаги
    await state_manager.clear_temporary_flags(user_id)

    # Перечитываем финальное состояние
    client_state = await state_manager.get_state(user_id)
    log.info(f"[process] state: {client_state.summary()}")

    return {
        "client_state": client_state,
        "extraction": extraction,
    }
