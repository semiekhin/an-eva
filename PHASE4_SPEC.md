# АН Эва — Фаза 4: Веб-слой (API + Виджет)

## ТЗ для 1Code (Claude Code)

📅 **Дата:** 17.02.2026
**Цель:** FastAPI приложение + чат-виджет. После этой фазы система работает end-to-end.
**Порядок:** main.py → widget/chat-widget.html → widget/chat-widget.js
**Зависимости:** Фазы 1-3 (все модули) — готовы.

---

## КОНТЕКСТ

Все модули готовы и протестированы (88 тестов). Фаза 4 собирает их в рабочее приложение:

```
Клиент на rizaltabelokurikha.ru → виджет (widget/)
    ↓ EventSource / fetch
FastAPI (main.py, порт 8005)
    ↓
message_processor → analyzer → rag_module → generator (стриминг)
    ↓
Ответ клиенту (SSE посимвольно)
```

**Референсы — читать ОБЯЗАТЕЛЬНО:**
- `refs/sofia/web_api.py` — полный веб-сервер Софии (сессии, стриминг, Bitrix, CORS)
- `refs/margarita/chat-widget.html` — текущий виджет (UI, стили)
- `refs/margarita/chat-widget.js` — загрузчик виджета

---

## ФАЙЛ 1: main.py

**Что:** FastAPI приложение — эндпоинты, lifespan, полный пайплайн.

### Эндпоинты

| Метод | URL | Назначение |
|-------|-----|------------|
| GET | `/api/health` | Health check |
| POST | `/api/session` | Создать сессию → вернуть session_id + приветствие |
| POST | `/api/session/resume` | Восстановить сессию из localStorage |
| POST | `/api/chat/stream` | Отправить сообщение → SSE стриминг ответа |
| GET | `/api/history/{session_id}` | История переписки |

### Архитектура

```python
import json
import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import PORT, HOST, CORS_ORIGINS, ANALYZER_HISTORY, HISTORY_LIMIT
from state_manager import StateManager
from message_processor import process_message
from analyzer import analyze
from rag_module import RAGModule
from generator import generate_stream, check_end_marker, build_generator_input
from rizalta_prompt_v2 import get_system_prompt
from rizalta_context import get_rizalta_context

# === Глобальные объекты ===
state_manager: StateManager = None
rag_module: RAGModule = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте, очистка при остановке."""
    global state_manager, rag_module
    
    state_manager = StateManager()
    await state_manager.init()
    
    rag_module = RAGModule()
    await rag_module.init()
    
    print(f"✅ АН Эва запущена на порту {PORT}")
    print(f"✅ RAG: {rag_module.count()} примеров")
    
    yield
    
    await state_manager.close()
    print("🛑 АН Эва остановлена")


app = FastAPI(title="АН Эва — Маргарита AI", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика для виджета
app.mount("/widget", StaticFiles(directory="widget"), name="widget")


# === Health ===
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "rag_examples": rag_module.count() if rag_module else 0,
    }


# === Создать сессию ===
@app.post("/api/session")
async def create_session(request: Request):
    """
    Создать новую сессию.
    Body: {"page_url": "...", "utm_source": "...", "utm_medium": "...", "utm_campaign": "..."}
    
    Returns: {"session_id": "...", "greeting": "..."}
    
    ВАЖНО: Приветствие генерируется на основе page_url и сохраняется в историю.
    """
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    
    session_id = str(uuid.uuid4())
    user_id = await state_manager.create_session(
        session_id=session_id,
        page_url=data.get("page_url", ""),
        utm_source=data.get("utm_source"),
        utm_medium=data.get("utm_medium"),
        utm_campaign=data.get("utm_campaign"),
    )
    
    # Приветствие (статичное, не через LLM — быстрее)
    greeting = generate_greeting(data.get("page_url", ""))
    
    # Сохранить приветствие в историю (урок из Софии #5)
    await state_manager.save_message(session_id, user_id, "assistant", greeting)
    
    return {"session_id": session_id, "greeting": greeting}


# === Восстановить сессию ===
@app.post("/api/session/resume")
async def resume_session(request: Request):
    """
    Восстановить сессию из localStorage.
    Body: {"session_id": "..."}
    
    Returns: {"session_id": "...", "history": [...], "active": true/false}
    """
    data = await request.json()
    session_id = data.get("session_id")
    
    if not session_id:
        return JSONResponse({"error": "session_id required"}, status_code=400)
    
    session = await state_manager.get_session(session_id)
    if not session:
        return JSONResponse({"active": False}, status_code=200)
    
    # Обновить last_active
    await state_manager.touch_session(session_id)
    
    # История
    history = await state_manager.get_history(session_id, limit=HISTORY_LIMIT)
    
    # Проверить не завершён ли диалог
    state = await state_manager.get_state(session["user_id"])
    
    return {
        "session_id": session_id,
        "active": not state.get("dialog_finished", False),
        "history": history,
    }


# === Чат со стримингом ===
@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    """
    Основной эндпоинт чата. SSE стриминг.
    Body: {"session_id": "...", "message": "..."}
    
    Response: SSE stream
        data: {"token": "слово"}
        data: {"token": "ещё"}
        data: {"done": true, "has_end": false}
    """
    data = await request.json()
    session_id = data.get("session_id")
    message = data.get("message", "").strip()
    
    if not session_id or not message:
        return JSONResponse({"error": "session_id and message required"}, status_code=400)
    
    # Получить сессию
    session = await state_manager.get_session(session_id)
    if not session:
        return JSONResponse({"error": "session not found"}, status_code=404)
    
    user_id = session["user_id"]
    
    # Проверить не завершён ли диалог
    state = await state_manager.get_state(user_id)
    if state.get("dialog_finished"):
        return JSONResponse({"error": "dialog finished"}, status_code=400)
    
    # Сохранить сообщение пользователя
    await state_manager.save_message(session_id, user_id, "user", message)
    
    async def event_generator():
        try:
            # 1. Message Processor (Extractor → State)
            proc_result = await process_message(
                message=message,
                session_id=session_id,
                user_id=user_id,
                state_manager=state_manager,
            )
            
            # 2. Analyzer (stage + rag_query)
            history = await state_manager.get_history(session_id, limit=ANALYZER_HISTORY)
            analysis = await analyze(
                message=message,
                state_summary=proc_result["state_summary"],
                signals=proc_result["signals"],
                history=history,
            )
            
            # 3. RAG
            rag_examples = await rag_module.search(
                analysis["stage"], 
                analysis["rag_query"]
            )
            
            # 4. Generator (стриминг)
            full_response = []
            async for token in generate_stream(
                system_prompt=get_system_prompt(),
                state_summary=proc_result["state_summary"],
                rag_examples=rag_examples,
                history=history,
                message=message,
                rizalta_context=get_rizalta_context(),
            ):
                full_response.append(token)
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            
            # 5. Post-processing
            response_text = "".join(full_response)
            clean_text, has_end = check_end_marker(response_text)
            
            # Сохранить ответ
            await state_manager.save_message(session_id, user_id, "assistant", clean_text)
            
            # Если [END] — завершить диалог
            if has_end:
                await state_manager.finish_dialog(user_id, "contact_collected")
                # TODO Фаза 6: отправить лид в CRM
            
            yield f"data: {json.dumps({'done': True, 'has_end': has_end}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            print(f"❌ Chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # для Nginx/Cloudflare — не буферизовать
        },
    )


# === История ===
@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    history = await state_manager.get_history(session_id, limit=HISTORY_LIMIT)
    return {"history": history}


# === Приветствие ===
def generate_greeting(page_url: str = "") -> str:
    """
    Статичное приветствие (без LLM — мгновенный ответ).
    Можно адаптировать под page_url.
    """
    # Базовое приветствие
    return (
        "Добрый день! Я Маргарита, ваш персональный консультант "
        "по инвестиционной недвижимости RIZALTA Resort Belokurikha) "
        "Чем могу помочь — рассматриваете инвестицию или подбираете для себя?"
    )


# === Запуск ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
```

### Ключевые принципы

1. **lifespan** — инициализация StateManager и RAG при старте, закрытие при остановке
2. **Greeting в историю** — урок из Софии #5, greeting сохраняется как assistant message
3. **SSE стриминг** — `text/event-stream`, `X-Accel-Buffering: no` для Cloudflare
4. **Post-processing после стриминга** — собрать полный ответ, проверить [END], сохранить в БД
5. **Статичное приветствие** — без LLM, мгновенно. LLM только для ответов на сообщения
6. **Ошибки в стриме** — не ронять соединение, отдать `{"error": "..."}` через SSE

### Тест main.py

```bash
# Запустить сервер
cd ~/Projects/an-eva
python main.py &

# В другом терминале или через curl:

# Health
curl -s http://localhost:8005/api/health | python -m json.tool

# Создать сессию
curl -s -X POST http://localhost:8005/api/session \
  -H "Content-Type: application/json" \
  -d '{"page_url": "https://rizaltabelokurikha.ru"}' | python -m json.tool

# Чат (стриминг) — подставить session_id из ответа выше
curl -N -X POST http://localhost:8005/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id": "ПОДСТАВИТЬ", "message": "Расскажите про инвестиции"}'

# Должен увидеть поток: data: {"token": "..."}\n\n

# Остановить сервер
kill %1
```

---

## ФАЙЛ 2: widget/chat-widget.html

**Что:** Чат-виджет с SSE стримингом. Встраивается в iframe на лендинге.
**Референс:** `refs/margarita/chat-widget.html` — текущий виджет (UI, стили). Скопировать дизайн, обновить логику.

### Что обновить по сравнению с текущим виджетом

1. **Стриминг** — заменить обычный fetch на EventSource/fetch+ReadableStream
2. **API URL** — настраиваемый (dev: `eva-dev.rizaltaservice.ru`, prod: `webchat.rizaltaservice.ru`)
3. **localStorage** — сохранять session_id для resume
4. **Resume** — при загрузке проверять localStorage → `/api/session/resume`
5. **Typing indicator** — реальный, от стриминга (не фейковый таймер)
6. **Quick replies** — опциональные кнопки быстрых ответов
7. **Disable input** — пока идёт стриминг, input заблокирован
8. **Auto-scroll** — прокрутка вниз при новых токенах

### Структура HTML

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RIZALTA — Маргарита AI</title>
    <style>
        /* 
        Скопировать стили из refs/margarita/chat-widget.html
        Адаптировать: 
        - Убрать лишнее
        - Добавить .typing-indicator
        - Добавить .message--streaming (для сообщения в процессе стриминга)
        - Добавить .quick-reply кнопки
        */
    </style>
</head>
<body>
    <div id="chat-container">
        <div id="chat-header">
            <!-- Шапка: аватар + имя + статус -->
        </div>
        <div id="chat-messages">
            <!-- Сообщения -->
        </div>
        <div id="chat-input-area">
            <input type="text" id="chat-input" placeholder="Напишите сообщение..." />
            <button id="chat-send">→</button>
        </div>
    </div>

    <script>
    // === КОНФИГУРАЦИЯ ===
    const API_URL = window.CHAT_API_URL || 'https://eva-dev.rizaltaservice.ru';
    // При деплое на прод заменить на: 'https://webchat.rizaltaservice.ru'
    
    let sessionId = localStorage.getItem('an_eva_session_id');
    let isStreaming = false;

    // === ИНИЦИАЛИЗАЦИЯ ===
    async function init() {
        if (sessionId) {
            // Resume
            const res = await fetch(`${API_URL}/api/session/resume`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: sessionId}),
            });
            const data = await res.json();
            
            if (data.active) {
                // Восстановить историю
                data.history.forEach(msg => appendMessage(msg.role, msg.content));
                return;
            }
        }
        
        // Новая сессия
        await createSession();
    }

    async function createSession() {
        const res = await fetch(`${API_URL}/api/session`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({page_url: window.location.href}),
        });
        const data = await res.json();
        
        sessionId = data.session_id;
        localStorage.setItem('an_eva_session_id', sessionId);
        
        // Показать приветствие
        appendMessage('assistant', data.greeting);
    }

    // === ОТПРАВКА СООБЩЕНИЯ ===
    async function sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (!message || isStreaming) return;
        
        input.value = '';
        appendMessage('user', message);
        
        isStreaming = true;
        disableInput(true);
        
        // Создать пустое сообщение для стриминга
        const msgEl = appendMessage('assistant', '', true);  // streaming=true
        
        try {
            const response = await fetch(`${API_URL}/api/chat/stream`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: sessionId, message: message}),
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, {stream: true});
                
                // Парсить SSE
                const lines = buffer.split('\n');
                buffer = lines.pop();  // неполная строка остаётся в буфере
                
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.token) {
                        appendToken(msgEl, data.token);
                        scrollToBottom();
                    }
                    
                    if (data.done) {
                        finishStreaming(msgEl);
                        if (data.has_end) {
                            // Диалог завершён — можно показать уведомление
                            showEndNotice();
                        }
                    }
                    
                    if (data.error) {
                        appendToken(msgEl, '\n⚠️ Произошла ошибка, попробуйте ещё раз');
                        finishStreaming(msgEl);
                    }
                }
            }
        } catch (e) {
            appendToken(msgEl, '\n⚠️ Ошибка соединения');
            finishStreaming(msgEl);
        }
    }

    // === UI ФУНКЦИИ ===
    function appendMessage(role, content, streaming = false) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = `message message--${role}${streaming ? ' message--streaming' : ''}`;
        div.textContent = content;
        container.appendChild(div);
        scrollToBottom();
        return div;
    }

    function appendToken(msgEl, token) {
        msgEl.textContent += token;
    }

    function finishStreaming(msgEl) {
        msgEl.classList.remove('message--streaming');
        isStreaming = false;
        disableInput(false);
    }

    function disableInput(disabled) {
        document.getElementById('chat-input').disabled = disabled;
        document.getElementById('chat-send').disabled = disabled;
    }

    function scrollToBottom() {
        const container = document.getElementById('chat-messages');
        container.scrollTop = container.scrollHeight;
    }

    function showEndNotice() {
        // Опционально: показать что диалог завершён
    }

    // === ОБРАБОТЧИКИ ===
    document.getElementById('chat-send').addEventListener('click', sendMessage);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Старт
    init();
    </script>
</body>
</html>
```

### Важные моменты

1. **fetch + ReadableStream** вместо EventSource — EventSource не поддерживает POST, а нам нужен POST для отправки сообщений
2. **SSE парсинг вручную** — читаем поток, парсим `data: {...}\n\n`
3. **localStorage** — session_id сохраняется и восстанавливается
4. **Disable input во время стриминга** — предотвращает двойные отправки
5. **Дизайн** — скопировать из `refs/margarita/chat-widget.html`, это уже отлаженный премиум-дизайн

---

## ФАЙЛ 3: widget/chat-widget.js

**Что:** Загрузчик виджета для лендинга. Создаёт iframe.
**Референс:** `refs/margarita/chat-widget.js`

```javascript
/**
 * АН Эва — загрузчик чат-виджета.
 * Подключается на лендинге: <script src="https://API_URL/widget/chat-widget.js"></script>
 */
(function() {
    // Конфигурация
    const API_URL = 'https://eva-dev.rizaltaservice.ru';  // Заменить на prod при деплое
    const WIDGET_URL = API_URL + '/widget/chat-widget.html';
    
    // Создать кнопку
    const btn = document.createElement('div');
    btn.id = 'an-eva-chat-btn';
    btn.innerHTML = '💬';  // или SVG иконка
    btn.style.cssText = `
        position: fixed; bottom: 20px; right: 20px;
        width: 60px; height: 60px; border-radius: 50%;
        background: #2563eb; color: white; font-size: 28px;
        display: flex; align-items: center; justify-content: center;
        cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999; transition: transform 0.2s;
    `;
    btn.onmouseenter = () => btn.style.transform = 'scale(1.1)';
    btn.onmouseleave = () => btn.style.transform = 'scale(1)';
    
    // Создать iframe (скрытый)
    const iframe = document.createElement('iframe');
    iframe.id = 'an-eva-chat-iframe';
    iframe.src = WIDGET_URL;
    iframe.style.cssText = `
        position: fixed; bottom: 90px; right: 20px;
        width: 380px; height: 520px; max-height: 80vh;
        border: none; border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        z-index: 9998; display: none;
    `;
    
    // Мобильная адаптация
    if (window.innerWidth <= 768) {
        iframe.style.cssText += `
            width: 100%; height: 100%; max-height: 100vh;
            bottom: 0; right: 0; border-radius: 0;
        `;
    }
    
    let isOpen = false;
    btn.addEventListener('click', () => {
        isOpen = !isOpen;
        iframe.style.display = isOpen ? 'block' : 'none';
        btn.innerHTML = isOpen ? '✕' : '💬';
    });
    
    document.body.appendChild(btn);
    document.body.appendChild(iframe);
})();
```

---

## ТЕСТЫ

### Автоматический тест main.py

```python
"""
Тест main.py — запустить отдельно.
Требует: pip install httpx
"""
import asyncio
import httpx

BASE = "http://localhost:8005"

async def test_api():
    async with httpx.AsyncClient() as client:
        # 1. Health
        r = await client.get(f"{BASE}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        print(f"✅ Health: {data}")
        
        # 2. Создать сессию
        r = await client.post(f"{BASE}/api/session", json={"page_url": "https://rizaltabelokurikha.ru"})
        assert r.status_code == 200
        data = r.json()
        session_id = data["session_id"]
        assert "greeting" in data
        print(f"✅ Session: {session_id}, greeting: {data['greeting'][:50]}...")
        
        # 3. Resume
        r = await client.post(f"{BASE}/api/session/resume", json={"session_id": session_id})
        assert r.status_code == 200
        data = r.json()
        assert data["active"] == True
        assert len(data["history"]) >= 1  # greeting
        print(f"✅ Resume: active={data['active']}, history={len(data['history'])}")
        
        # 4. Chat stream
        async with client.stream(
            "POST",
            f"{BASE}/api/chat/stream",
            json={"session_id": session_id, "message": "Расскажите про инвестиции в RIZALTA"},
        ) as response:
            tokens = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = __import__("json").loads(line[6:])
                    if event.get("token"):
                        tokens.append(event["token"])
                    if event.get("done"):
                        print(f"✅ Stream done, has_end={event.get('has_end')}")
                        break
            
            full = "".join(tokens)
            print(f"✅ Response ({len(tokens)} tokens): {full[:100]}...")
        
        # 5. History
        r = await client.get(f"{BASE}/api/history/{session_id}")
        assert r.status_code == 200
        data = r.json()
        assert len(data["history"]) >= 3  # greeting + user + assistant
        print(f"✅ History: {len(data['history'])} messages")
        
        print(f"\n🎉 API тесты пройдены")

asyncio.run(test_api())
```

### Ручной тест

1. `python main.py` — запустить сервер
2. Открыть `http://localhost:8005/widget/chat-widget.html` в браузере
3. Должен увидеть чат, приветствие Маргариты
4. Написать сообщение → увидеть стриминг ответа
5. Обновить страницу → resume, история сохранилась
6. Ctrl+C — остановить сервер

---

## ПРАВИЛА

### Git-воркфлоу

```bash
# После main.py (без виджета — только API)
python -c "from main import app; print('FastAPI OK')"
git add main.py
git commit -m "phase4: main.py — FastAPI endpoints, SSE streaming, lifespan"

# После виджета
git add widget/
git commit -m "phase4: widget — chat UI with SSE streaming, localStorage resume"

git push
```

### Чего НЕ делать
- НЕ создавать bitrix_client.py (Фаза 6)
- НЕ создавать observer.py (Фаза 6)
- НЕ менять модули Фаз 1-3 (если только не баг)
- НЕ менять файлы в refs/
- Если нужно добавить httpx в requirements.txt для тестов — можно

### Порт
- **DEV: 8005** — не занят, безопасно
- НЕ использовать 8001 (текущая Маргарита) и другие занятые порты
