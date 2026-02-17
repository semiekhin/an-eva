"""
lead_notifier.py — отправка лидов Sergio в Telegram
"""

import logging
import aiohttp
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_NOTIFY_CHAT_ID

log = logging.getLogger(__name__)


async def send_lead_to_telegram(
    user_id: int,
    session_id: str,
    finish_type: str | None,
    client_state,
    phone: str | None = None,
    telegram_username: str | None = None,
    last_messages: list[dict] | None = None,
) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_NOTIFY_CHAT_ID:
        log.warning("[lead] TELEGRAM_BOT_TOKEN or TELEGRAM_NOTIFY_CHAT_ID not set")
        return False

    type_emoji = {"meeting": "📞", "materials": "📎", "contact": "👤"}.get(finish_type, "✅")
    type_text = {"meeting": "Показ/созвон", "materials": "Материалы", "contact": "Контакт"}.get(finish_type, finish_type or "Завершение")

    lines = [
        f"{type_emoji} <b>Новый лид — АН Эва</b>",
        "",
        f"<b>Тип:</b> {type_text}",
    ]

    if phone:
        lines.append(f"<b>Телефон:</b> <code>{phone}</code>")
    if telegram_username:
        lines.append(f"<b>Telegram:</b> {telegram_username}")
    if not phone and not telegram_username:
        lines.append(f"<b>Контакт:</b> не оставил")

    lines.append("")
    if client_state.goal:
        goal_text = "Инвестиция" if client_state.goal == "investment" else "Для себя"
        lines.append(f"<b>Цель:</b> {goal_text}")
    if client_state.budget:
        lines.append(f"<b>Бюджет:</b> {client_state.budget / 1_000_000:.0f} млн ₽")
    if client_state.payment_type:
        pay_map = {"full": "100%", "mortgage": "Ипотека", "installment": "Рассрочка", "any": "Любой"}
        lines.append(f"<b>Оплата:</b> {pay_map.get(client_state.payment_type, client_state.payment_type)}")
    if client_state.preferred_corpus:
        lines.append(f"<b>Корпус:</b> {client_state.preferred_corpus}")

    if last_messages:
        lines.append("")
        lines.append("<b>Последние сообщения:</b>")
        for m in last_messages[-6:]:
            role = "👤" if m["role"] == "user" else "🤖"
            text = m["content"][:150]
            lines.append(f"{role} {text}")

    lines.append("")
    lines.append(f"<i>session: {session_id[:8]}... | user: {user_id}</i>")

    text = "\n".join(lines)

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_NOTIFY_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    log.info(f"[lead] sent to Telegram: {finish_type}, user={user_id}")
                    return True
                else:
                    body = await resp.text()
                    log.error(f"[lead] Telegram API error {resp.status}: {body}")
                    return False
    except Exception as e:
        log.error(f"[lead] send error: {e}")
        return False
