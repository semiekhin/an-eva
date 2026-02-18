"""
main.py — FastAPI Web API для АН Эва (RIZALTA webchat)
=======================================================
Единая точка входа. Полный пайплайн:
  session → save msg → process_message → analyzer → RAG → generator → save reply

Запуск: uvicorn main:app --host 0.0.0.0 --port 8005
"""

import uuid
import json as json_module
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import HOST, PORT, CORS_ORIGINS, GENERATOR_HISTORY_LIMIT, BASE_DIR
from state_manager import StateManager
from message_processor import process_message
from analyzer import analyze
from rag_module import init_rag, search_examples, format_examples_for_prompt
from generator import generate, generate_stream, extract_phone_from_history, extract_telegram_from_history
from rizalta_prompt_v2 import get_system_prompt, format_state_summary
from rizalta_context import get_rizalta_context
from lead_notifier import send_lead_to_telegram

# ── Логирование ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AN-EVA] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ── Глобальный StateManager ─────────────────────────────────────────────────

state_manager = StateManager()

WEB_USER_ID_OFFSET = 9_000_000
GREETING = "Здравствуйте! Я Маргарита, консультант RIZALTA Resort Belokurikha. Чем могу помочь?"


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"AN Eva Web API starting on {HOST}:{PORT}...")
    await state_manager.init()
    init_rag()
    log.info("StateManager + RAG initialized")
    yield
    await state_manager.close()
    log.info("AN Eva Web API stopped")


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="AN Eva — RIZALTA Webchat", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Models ───────────────────────────────────────────────────────────────────

class SessionRequest(BaseModel):
    page_url: str | None = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    timestamp: str


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_or_create_user_id(session_id: str) -> int:
    """Получает user_id по session_id, создаёт нового при необходимости."""
    sess = await state_manager.get_session(session_id)
    if sess:
        return sess["user_id"]

    # Новый user_id: MAX(user_id) + 1 (offset 9M для веб-пользователей)
    cursor = await state_manager._db.execute(
        "SELECT COALESCE(MAX(user_id), ?) FROM web_sessions", (WEB_USER_ID_OFFSET,)
    )
    row = await cursor.fetchone()
    new_uid = row[0] + 1

    await state_manager.create_session(session_id, new_uid)
    log.info(f"[session] new: {session_id[:8]}... -> user_id={new_uid}")
    return new_uid


async def _full_pipeline(user_id: int, session_id: str, message: str) -> str:
    """
    Полный пайплайн обработки сообщения:
    1. Save user message
    2. Process (extractor → state → signals)
    3. Analyze (stage + rag_query)
    4. RAG search
    5. Generate response
    6. Handle [END]
    7. Save bot reply
    """
    # 1. Сохраняем сообщение пользователя
    await state_manager.save_message(session_id, user_id, "user", message)

    # 2. Получаем историю
    history = await state_manager.get_history(session_id, limit=GENERATOR_HISTORY_LIMIT)

    # 3. Process: extractor → state → signals
    result = await process_message(
        user_id=user_id,
        message=message,
        history=history,
        state_manager=state_manager,
    )
    client_state = result["client_state"]

    # 4. Analyzer: stage + rag_query
    analysis = await analyze(
        message=message,
        history=history,
        client_state=client_state,
    )
    stage = analysis["stage"]
    rag_query = analysis["rag_query"]
    log.info(f"[pipeline] user={user_id}: stage={stage}, query='{rag_query[:30]}'")

    # 5. RAG
    examples = search_examples(stage, rag_query)
    examples_prompt = format_examples_for_prompt(examples) if examples else ""
    if examples:
        log.info(f"[pipeline] RAG [{stage}]: {len(examples)} examples")

    # 6. Generator
    state_summary = format_state_summary(client_state)
    rizalta_context = get_rizalta_context()
    system_prompt = get_system_prompt(state_summary, rizalta_context, examples_prompt)

    gen_result = await generate(
        system_prompt=system_prompt,
        history=history,
        message=message,
    )
    reply = gen_result["answer"]

    # 7. Handle [END]
    if gen_result["ended"]:
        await state_manager.update_state(user_id, {
            "dialog_finished": True,
            "finish_type": gen_result["finish_type"],
        })
        log.info(f"[pipeline] dialog ended, type={gen_result['finish_type']}")
        full_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        await _send_lead_notification(user_id, session_id, gen_result["finish_type"], full_history)

    # 8. Сохраняем ответ бота
    await state_manager.save_message(session_id, user_id, "assistant", reply)
    await state_manager.touch_session(session_id)

    return reply




async def _send_lead_notification(user_id: int, session_id: str, finish_type: str | None, history: list[dict]):
    """Отправляет уведомление о лиде в Telegram."""
    try:
        client_state = await state_manager.get_state(user_id)
        phone = extract_phone_from_history(history)
        tg_user = extract_telegram_from_history(history)
        await send_lead_to_telegram(
            user_id=user_id,
            session_id=session_id,
            finish_type=finish_type,
            client_state=client_state,
            phone=phone,
            telegram_username=tg_user,
            last_messages=history,
        )
    except Exception as e:
        log.error(f"[lead] notification error: {e}")

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "timestamp": datetime.now().isoformat()}


@app.post("/api/session")
async def create_session(req: SessionRequest):
    session_id = str(uuid.uuid4())
    user_id = await _get_or_create_user_id(session_id)

    # Сохраняем page_url
    if req.page_url:
        await state_manager._db.execute(
            "UPDATE web_sessions SET page_url = ? WHERE session_id = ?",
            (req.page_url, session_id),
        )
        await state_manager._db.commit()

    # Сохраняем greeting в историю (BUG-005 fix из Софии)
    await state_manager.save_message(session_id, user_id, "assistant", GREETING)

    log.info(f"[session] created: {session_id[:8]}... from {req.page_url or 'unknown'}")
    return {"session_id": session_id, "greeting": GREETING}


@app.post("/api/session/resume")
async def resume_session(req: ChatRequest):
    sess = await state_manager.get_session(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    history = await state_manager.get_history(req.session_id, limit=50)
    await state_manager.touch_session(req.session_id)

    log.info(f"[session] resumed: {req.session_id[:8]}... msgs={len(history)}")
    return {"session_id": req.session_id, "history": history}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    if len(req.message) > 2000:
        raise HTTPException(status_code=400, detail="Message too long (max 2000)")

    user_id = await _get_or_create_user_id(req.session_id)

    reply = await _full_pipeline(
        user_id=user_id,
        session_id=req.session_id,
        message=req.message.strip(),
    )

    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        timestamp=datetime.now().isoformat(),
    )



@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE стриминг ответа Маргариты."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    if len(req.message) > 2000:
        raise HTTPException(status_code=400, detail="Message too long (max 2000)")

    user_id = await _get_or_create_user_id(req.session_id)

    async def event_stream():

        await state_manager.save_message(req.session_id, user_id, "user", req.message.strip())
        history = await state_manager.get_history(req.session_id, limit=GENERATOR_HISTORY_LIMIT)

        yield ": processing\n\n"

        result = await process_message(
            user_id=user_id,
            message=req.message.strip(),
            history=history,
            state_manager=state_manager,
        )
        client_state = result["client_state"]

        yield ": analyzing\n\n"

        analysis = await analyze(
            message=req.message.strip(),
            history=history,
            client_state=client_state,
        )
        stage = analysis["stage"]
        rag_query = analysis["rag_query"]
        log.info(f"[stream] user={user_id}: stage={stage}, query=\'{rag_query[:30]}\'")

        examples = search_examples(stage, rag_query)
        examples_prompt = format_examples_for_prompt(examples) if examples else ""

        state_summary = format_state_summary(client_state)
        rizalta_context = get_rizalta_context()
        system_prompt = get_system_prompt(state_summary, rizalta_context, examples_prompt)

        full_reply = ""
        ended = False
        finish_type = None

        async for chunk in generate_stream(
            system_prompt=system_prompt,
            history=history,
            message=req.message.strip(),
        ):
            if chunk["type"] == "token":
                full_reply += chunk["token"]
                data = json_module.dumps({"type": "token", "token": chunk["token"]}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            elif chunk["type"] == "done":
                ended = chunk.get("ended", False)
                finish_type = chunk.get("finish_type")
            elif chunk["type"] == "error":
                data = json_module.dumps({"type": "error", "error": chunk["error"]}, ensure_ascii=False)
                yield f"data: {data}\n\n"

        if ended:
            full_reply = full_reply.replace("[END]", "").replace("[end]", "").strip()
            await state_manager.update_state(user_id, {
                "dialog_finished": True,
                "finish_type": finish_type,
            })
            await _send_lead_notification(user_id, req.session_id, finish_type, history + [
                {"role": "user", "content": req.message.strip()},
                {"role": "assistant", "content": full_reply},
            ])

        if not full_reply.strip():
            full_reply = "Подскажите, что для вас важнее — посмотреть варианты или обсудить условия?"

        await state_manager.save_message(req.session_id, user_id, "assistant", full_reply)
        await state_manager.touch_session(req.session_id)

        data = json_module.dumps({"type": "done", "ended": ended}, ensure_ascii=False)
        yield f"data: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/history/{session_id}")
async def get_history(session_id: str, limit: int = 50):
    sess = await state_manager.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await state_manager.get_history(session_id, limit=limit)
    return {
        "session_id": session_id,
        "messages": [
            {"role": "bot" if m["role"] == "assistant" else "user", "content": m["content"]}
            for m in messages
        ],
    }


# ── Docs ──────────────────────────────────────────────────────────────────────

@app.get("/api/docs/current")
async def docs_current():
    path = BASE_DIR / "docs" / "AN_EVA_CURRENT.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="docs/AN_EVA_CURRENT.md not found")
    content = path.read_text(encoding="utf-8")
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/docs/context")
async def docs_context():
    path = BASE_DIR / "docs" / "AN_EVA_CONTEXT.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="docs/AN_EVA_CONTEXT.md not found")
    content = path.read_text(encoding="utf-8")
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


# ── Статика виджета ──────────────────────────────────────────────────────────

app.mount("/widget", StaticFiles(directory="widget", html=True), name="widget")


# ── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
