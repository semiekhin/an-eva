# АН Эва — Фаза 1: Ядро

## ТЗ для 1Code (Claude Code)

📅 **Дата:** 17.02.2026
**Цель:** Написать ядро системы — 5 файлов, каждый тестируется отдельно.
**Порядок:** config.py → extractor.py → state_manager.py → message_processor.py → analyzer.py

---

## КОНТЕКСТ

АН Эва — AI-консультант «Маргарита» для продажи инвестиционной недвижимости RIZALTA Resort Belokurikha. Архитектура копируется из Sofia-GPT (refs/sofia/) и адаптируется под RIZALTA.

**Критичные правила:**
- Код пишется ЛОКАЛЬНО в `~/Projects/an-eva/`
- НЕ трогать файлы в `/opt/sofia-gpt/`, `/opt/bot/`, `/opt/bot-dev/`, `/opt/rizalta-webchat/`
- Референсы лежат в `refs/sofia/` и `refs/margarita/` — читать, не менять
- Данные в `data/` — читать, не менять
- OpenAI API: **Responses API** (НЕ Chat Completions), модель **gpt-5.2**

---

## ФАЙЛ 1: config.py

**Что:** Центральная конфигурация проекта.

```python
"""
Конфигурация АН Эва.
Все пути, порты, настройки — здесь.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === Пути ===
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "an_eva.db"

# === Сервер ===
PORT = int(os.getenv("PORT", 8005))
HOST = os.getenv("HOST", "0.0.0.0")

# === OpenAI ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "gpt-5.2")
EMBEDDING_MODEL = "text-embedding-3-small"

# === Лимиты ===
HISTORY_LIMIT = 100          # макс сообщений в истории
EXTRACTOR_HISTORY = 6        # последних сообщений для extractor
ANALYZER_HISTORY = 20        # последних сообщений для analyzer
RAG_RESULTS = 7              # количество RAG-примеров
MAX_OUTPUT_TOKENS = 4000     # макс токенов в ответе generator

# === CORS ===
CORS_ORIGINS = [
    "https://rizaltabelokurikha.ru",
    "http://rizaltabelokurikha.ru",
    "https://www.rizaltabelokurikha.ru",
    "http://www.rizaltabelokurikha.ru",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
]

# === Этапы диалога ===
STAGES = [
    "GREETING",
    "QUALIFICATION",
    "PRESENTATION",
    "OBJECTION",
    "MEETING",
    "CLOSING",
]

# === Создание директорий ===
DB_DIR.mkdir(parents=True, exist_ok=True)
```

**Зависимости:** `python-dotenv`
**Тест:** `python -c "from config import *; print(f'DB: {DB_PATH}, Port: {PORT}, Model: {MODEL}')"` — должен вывести пути без ошибок.

---

## ФАЙЛ 2: extractor.py

**Что:** NLU-модуль. Извлекает ~10 полей из сообщения клиента через LLM.
**Референс:** `refs/sofia/extractor.py` — читать ОБЯЗАТЕЛЬНО перед написанием.

### Поля для извлечения (~10, НЕ 30 как в старой Маргарите)

```python
EXTRACTION_FIELDS = {
    # Квалификация (3 основных вопроса)
    "goal": {
        "type": "enum",
        "values": ["investment", "personal", "gift", "undecided"],
        "description": "Цель покупки"
    },
    "budget": {
        "type": "string",  # "5-7 млн", "до 10 млн", "15000000"
        "description": "Бюджет клиента"
    },
    "payment_type": {
        "type": "enum",
        "values": ["full", "mortgage", "installment", "undecided"],
        "description": "Способ оплаты"
    },
    
    # Предпочтения
    "preferred_corpus": {
        "type": "enum",
        "values": ["family", "business", "digital", "any"],
        "description": "Предпочитаемый корпус"
    },
    "preferred_area": {
        "type": "string",  # "студия", "30-40 м²", "большая"
        "description": "Предпочтения по площади"
    },
    
    # Сигналы
    "objection": {
        "type": "string",  # null или текст возражения
        "description": "Возражение клиента (если есть)"
    },
    "sentiment": {
        "type": "enum",
        "values": ["positive", "neutral", "negative", "skeptical"],
        "description": "Настроение клиента"
    },
    "contact_shared": {
        "type": "object",  # {"type": "telegram", "value": "@username"} или null
        "description": "Контакт если клиент поделился"
    },
    "question": {
        "type": "string",  # конкретный вопрос клиента, null если нет
        "description": "Конкретный вопрос клиента"
    },
    "intent": {
        "type": "enum",
        "values": ["greeting", "question", "objection", "agreement", "contact", "farewell", "other"],
        "description": "Намерение сообщения"
    }
}
```

### Архитектура

```python
import json
from openai import OpenAI
from config import OPENAI_API_KEY, MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

EXTRACTOR_PROMPT = """Ты — NLU-экстрактор для AI-консультанта по недвижимости RIZALTA Resort Belokurikha.

Извлеки из сообщения клиента следующие поля. Возвращай ТОЛЬКО валидный JSON.
Если поле нельзя определить — ставь null.

Поля:
- goal: "investment" | "personal" | "gift" | "undecided" | null
- budget: строка с бюджетом или null (например "5-7 млн", "до 10 млн")
- payment_type: "full" | "mortgage" | "installment" | "undecided" | null
- preferred_corpus: "family" | "business" | "digital" | "any" | null
- preferred_area: строка с предпочтениями по площади или null
- objection: текст возражения или null
- sentiment: "positive" | "neutral" | "negative" | "skeptical"
- contact_shared: {"type": "telegram"|"phone", "value": "..."} или null
- question: конкретный вопрос клиента или null
- intent: "greeting" | "question" | "objection" | "agreement" | "contact" | "farewell" | "other"

Контекст предыдущих сообщений для понимания:
{history_context}

Сообщение клиента:
{message}

Ответь ТОЛЬКО JSON-объектом, без markdown, без пояснений."""


async def extract(message: str, history: list[dict] = None) -> dict:
    """
    Извлекает поля из сообщения клиента.
    
    Args:
        message: текст сообщения клиента
        history: последние N сообщений [{"role": "user"/"assistant", "content": "..."}]
    
    Returns:
        dict с извлечёнными полями (null для неопределённых)
    """
    history_context = ""
    if history:
        history_context = "\n".join(
            f"{'Клиент' if m['role'] == 'user' else 'Маргарита'}: {m['content']}"
            for m in history[-6:]  # EXTRACTOR_HISTORY из config
        )
    
    prompt = EXTRACTOR_PROMPT.format(
        history_context=history_context or "Нет предыдущих сообщений",
        message=message
    )
    
    # Responses API (НЕ Chat Completions!)
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        reasoning={"effort": "medium"},  # лёгкий, быстрый
    )
    
    # Парсинг ответа
    raw = response.output_text.strip()
    # Убрать markdown обёртку если есть
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Фоллбэк: вернуть пустой результат
        result = {field: None for field in EXTRACTION_FIELDS}
        result["sentiment"] = "neutral"
        result["intent"] = "other"
    
    return result
```

**Ключевые принципы (из Софии):**
- Responses API, `reasoning.effort: "medium"` — быстрый, не тратит время
- Только JSON на выходе, без markdown
- Фоллбэк при ошибке парсинга — НЕ ронять пайплайн
- История — последние 6 сообщений (EXTRACTOR_HISTORY из config)

**Тест:**
```python
import asyncio
from extractor import extract

# Тест 1: приветствие
result = asyncio.run(extract("Здравствуйте, хочу узнать про инвестиции"))
assert result["intent"] == "greeting" or result["goal"] == "investment"
print("✅ Тест 1 пройден:", result)

# Тест 2: бюджет
result = asyncio.run(extract("У меня бюджет около 7 миллионов"))
assert result["budget"] is not None
print("✅ Тест 2 пройден:", result)

# Тест 3: возражение
result = asyncio.run(extract("Белокуриха — это далеко, неудобно добираться"))
assert result["objection"] is not None
print("✅ Тест 3 пройден:", result)

# Тест 4: контакт
result = asyncio.run(extract("Мой телеграм @ivan_test"))
assert result["contact_shared"] is not None
print("✅ Тест 4 пройден:", result)
```

---

## ФАЙЛ 3: state_manager.py

**Что:** Управление состоянием клиента в SQLite. Connection pool через aiosqlite.
**Референс:** `refs/sofia/state_manager.py` — читать ОБЯЗАТЕЛЬНО.

### Схема БД

```sql
-- Веб-сессии
CREATE TABLE IF NOT EXISTS web_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    page_url TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT
);

-- Состояние клиента
CREATE TABLE IF NOT EXISTS client_state (
    user_id INTEGER PRIMARY KEY,
    
    -- Квалификация
    goal TEXT,                    -- investment/personal/gift/undecided
    goal_confidence TEXT DEFAULT 'none',  -- none/mentioned/confirmed
    budget TEXT,
    budget_confidence TEXT DEFAULT 'none',
    payment_type TEXT,            -- full/mortgage/installment/undecided
    payment_type_confidence TEXT DEFAULT 'none',
    
    -- Предпочтения
    preferred_corpus TEXT,        -- family/business/digital/any
    preferred_area TEXT,
    
    -- Сигналы
    last_objection TEXT,
    sentiment TEXT DEFAULT 'neutral',
    engagement INTEGER DEFAULT 0,  -- счётчик сообщений
    
    -- Конверсия
    contact_type TEXT,            -- telegram/phone
    contact_value TEXT,
    meeting_agreed INTEGER DEFAULT 0,
    dialog_finished INTEGER DEFAULT 0,
    finish_type TEXT,             -- contact_collected/user_left/manual
    
    -- Счётчики (для правила двух попыток)
    questions_asked INTEGER DEFAULT 0,       -- сколько вопросов задали
    materials_offered INTEGER DEFAULT 0,     -- сколько раз предложили материалы
    meeting_offered INTEGER DEFAULT 0,       -- сколько раз предложили встречу
    
    -- Таймстампы
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- История сообщений
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_id INTEGER,
    role TEXT NOT NULL,          -- user/assistant/system
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES web_sessions(session_id)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON web_sessions(last_active);
```

### Архитектура

```python
import aiosqlite
from config import DB_PATH

class StateManager:
    def __init__(self):
        self.db_path = str(DB_PATH)
        self._db = None  # единственное подключение
    
    async def init(self):
        """Инициализация: подключение + создание таблиц + WAL mode."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA busy_timeout=5000")
        await self._create_tables()
    
    async def close(self):
        if self._db:
            await self._db.close()
    
    async def _create_tables(self):
        """Создать таблицы (SQL выше)."""
        ...
    
    # === Сессии ===
    async def create_session(self, session_id: str, page_url: str = None, 
                              utm_source: str = None, utm_medium: str = None,
                              utm_campaign: str = None) -> int:
        """Создать сессию, вернуть user_id (auto-increment)."""
        ...
    
    async def get_session(self, session_id: str) -> dict | None:
        """Получить сессию по session_id."""
        ...
    
    async def resume_session(self, session_id: str) -> dict | None:
        """Восстановить сессию: вернуть state + последние сообщения."""
        ...
    
    async def touch_session(self, session_id: str):
        """Обновить last_active."""
        ...
    
    # === Состояние ===
    async def get_state(self, user_id: int) -> dict:
        """Получить состояние клиента."""
        ...
    
    async def update_state(self, user_id: int, extracted: dict):
        """
        Обновить состояние по данным из Extractor.
        
        ПРАВИЛО: confirmed перезаписывает mentioned, не наоборот.
        Если текущее значение confirmed, а новое mentioned — не трогать.
        """
        ...
    
    async def get_state_summary(self, user_id: int) -> str:
        """
        Текстовое описание состояния для промпта Generator.
        Пример: "Цель: инвестиция (подтверждено). Бюджет: 7-10 млн (упомянуто). Оплата: не определена."
        """
        ...
    
    # === Сообщения ===
    async def save_message(self, session_id: str, user_id: int, 
                           role: str, content: str):
        """Сохранить сообщение в историю."""
        ...
    
    async def get_history(self, session_id: str, limit: int = None) -> list[dict]:
        """Получить историю сообщений. limit по умолчанию из config.HISTORY_LIMIT."""
        ...
    
    # === Конверсия ===
    async def finish_dialog(self, user_id: int, finish_type: str = "contact_collected"):
        """Пометить диалог как завершённый."""
        ...
```

**Ключевые принципы (из Софии):**
- **Одно подключение** к SQLite через aiosqlite (НЕ 14+ как в старой Маргарите)
- **WAL mode** для конкурентного доступа
- **busy_timeout=5000** чтобы не падать при одновременных запросах
- **confirmed > mentioned** — если goal_confidence = "confirmed", а extractor вернул "mentioned" — НЕ менять
- **get_state_summary()** — формирует текст для промпта, а не сырой dict

**Тест:**
```python
import asyncio
from state_manager import StateManager

async def test():
    sm = StateManager()
    await sm.init()
    
    # Создать сессию
    user_id = await sm.create_session("test-session-123", page_url="https://rizaltabelokurikha.ru")
    print(f"✅ Сессия создана, user_id: {user_id}")
    
    # Обновить состояние
    await sm.update_state(user_id, {"goal": "investment", "budget": "7 млн"})
    state = await sm.get_state(user_id)
    print(f"✅ Состояние: {state}")
    
    # Сохранить сообщение
    await sm.save_message("test-session-123", user_id, "user", "Хочу инвестировать")
    await sm.save_message("test-session-123", user_id, "assistant", "Отлично! Какой у вас бюджет?")
    history = await sm.get_history("test-session-123")
    print(f"✅ История: {len(history)} сообщений")
    
    # State summary
    summary = await sm.get_state_summary(user_id)
    print(f"✅ Summary: {summary}")
    
    await sm.close()

asyncio.run(test())
```

---

## ФАЙЛ 4: message_processor.py

**Что:** Единый пайплайн: Extractor → State Update → Signals.
**Референс:** `refs/sofia/message_processor.py` — короткий, ~90 строк.

### Архитектура

```python
from extractor import extract
from state_manager import StateManager
from config import EXTRACTOR_HISTORY


async def process_message(
    message: str,
    session_id: str,
    user_id: int,
    state_manager: StateManager
) -> dict:
    """
    Обрабатывает входящее сообщение:
    1. Получает историю для Extractor
    2. Извлекает поля через Extractor
    3. Обновляет состояние в БД
    4. Формирует сигналы для дальнейшей обработки
    
    Returns:
        {
            "extracted": {...},       # сырой результат Extractor
            "state": {...},           # обновлённое состояние
            "state_summary": "...",   # текстовое описание для промпта
            "signals": {              # сигналы для Analyzer/Generator
                "has_contact": bool,
                "has_objection": bool,
                "is_greeting": bool,
                "dialog_finished": bool,
            }
        }
    """
    # 1. История для extractor (последние 6 сообщений)
    history = await state_manager.get_history(session_id, limit=EXTRACTOR_HISTORY)
    
    # 2. Extractor
    extracted = await extract(message, history)
    
    # 3. Обновить состояние
    await state_manager.update_state(user_id, extracted)
    
    # 4. Проверить контакт → finish
    if extracted.get("contact_shared"):
        contact = extracted["contact_shared"]
        # Сохранить контакт в state отдельно
        await state_manager.update_state(user_id, {
            "contact_type": contact.get("type"),
            "contact_value": contact.get("value"),
        })
    
    # 5. Собрать результат
    state = await state_manager.get_state(user_id)
    state_summary = await state_manager.get_state_summary(user_id)
    
    signals = {
        "has_contact": bool(extracted.get("contact_shared")),
        "has_objection": bool(extracted.get("objection")),
        "is_greeting": extracted.get("intent") == "greeting",
        "dialog_finished": bool(state.get("dialog_finished")),
    }
    
    return {
        "extracted": extracted,
        "state": state,
        "state_summary": state_summary,
        "signals": signals,
    }
```

**Принципы:**
- Тонкий слой: связывает Extractor и State, не содержит бизнес-логику
- Формирует signals для downstream (Analyzer, Generator)
- Контакт обрабатывается отдельно

**Тест:**
```python
import asyncio
from state_manager import StateManager
from message_processor import process_message

async def test():
    sm = StateManager()
    await sm.init()
    
    user_id = await sm.create_session("test-mp-001")
    
    result = await process_message(
        message="Добрый день! Интересует инвестиция в RIZALTA, бюджет примерно 8 миллионов",
        session_id="test-mp-001",
        user_id=user_id,
        state_manager=sm
    )
    
    print(f"✅ Extracted: {result['extracted']}")
    print(f"✅ State summary: {result['state_summary']}")
    print(f"✅ Signals: {result['signals']}")
    
    assert result["extracted"]["goal"] == "investment"
    assert result["extracted"]["budget"] is not None
    
    await sm.close()

asyncio.run(test())
```

---

## ФАЙЛ 5: analyzer.py

**Что:** LLM-Analyzer. Определяет этап диалога + формирует rag_query. Заменяет детерминистический planner (29 actions) на один LLM-вызов.
**Референс:** `refs/sofia/web_api.py` — найти `analyzer_prompt` (inline в функции обработки сообщений) и `refs/sofia/bot_server.py`.

### Архитектура

```python
import json
from openai import OpenAI
from config import OPENAI_API_KEY, MODEL, STAGES, ANALYZER_HISTORY

client = OpenAI(api_key=OPENAI_API_KEY)

ANALYZER_PROMPT = """Ты — аналитик диалога продаж инвестиционной недвижимости RIZALTA Resort Belokurikha (Алтай).

Определи текущий этап диалога и сформулируй запрос для поиска подходящих примеров.

Этапы:
- GREETING — начало разговора, приветствие
- QUALIFICATION — выяснение цели, бюджета, способа оплаты
- PRESENTATION — презентация лотов, цен, расчётов ROI
- OBJECTION — работа с возражениями клиента
- MEETING — предложение онлайн-показа или отправки материалов
- CLOSING — сбор контакта, завершение диалога

Состояние клиента:
{state_summary}

Сигналы:
{signals}

История диалога:
{history}

Последнее сообщение клиента:
{message}

Определи:
1. stage — текущий этап (одно из: GREETING, QUALIFICATION, PRESENTATION, OBJECTION, MEETING, CLOSING)
2. rag_query — запрос на русском для поиска примеров похожих ситуаций в продажах (2-5 слов)

Ответь ТОЛЬКО JSON: {{"stage": "...", "rag_query": "..."}}"""


async def analyze(
    message: str,
    state_summary: str,
    signals: dict,
    history: list[dict],
) -> dict:
    """
    Определяет этап диалога и формирует RAG-запрос.
    
    Returns:
        {"stage": "QUALIFICATION", "rag_query": "бюджет инвестиции"}
    """
    history_text = "\n".join(
        f"{'Клиент' if m['role'] == 'user' else 'Маргарита'}: {m['content']}"
        for m in history[-ANALYZER_HISTORY:]
    )
    
    signals_text = ", ".join(f"{k}: {v}" for k, v in signals.items())
    
    prompt = ANALYZER_PROMPT.format(
        state_summary=state_summary,
        signals=signals_text,
        history=history_text or "Нет истории",
        message=message,
    )
    
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        reasoning={"effort": "medium"},
    )
    
    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    
    try:
        result = json.loads(raw)
        # Валидация stage
        if result.get("stage") not in STAGES:
            result["stage"] = "GREETING"
        if not result.get("rag_query"):
            result["rag_query"] = "приветствие клиент"
    except json.JSONDecodeError:
        result = {"stage": "GREETING", "rag_query": "приветствие клиент"}
    
    return result
```

**Принципы (из Софии):**
- LLM вместо детерминистического planner — гибче, проще, надёжнее
- `reasoning.effort: "medium"` — быстрый вызов
- Фоллбэк на GREETING при ошибке
- rag_query на русском, 2-5 слов — для ChromaDB

**Тест:**
```python
import asyncio
from analyzer import analyze

async def test():
    # Тест 1: начало диалога
    result = await analyze(
        message="Здравствуйте!",
        state_summary="Новый клиент, ничего не известно.",
        signals={"is_greeting": True, "has_objection": False},
        history=[]
    )
    print(f"✅ Greeting: {result}")
    assert result["stage"] == "GREETING"
    
    # Тест 2: возражение
    result = await analyze(
        message="Белокуриха — это далеко, не уверен",
        state_summary="Цель: инвестиция. Бюджет: 7 млн.",
        signals={"is_greeting": False, "has_objection": True},
        history=[
            {"role": "user", "content": "Хочу инвестировать 7 млн"},
            {"role": "assistant", "content": "Отличный бюджет! Рассмотрим Family корпус."},
        ]
    )
    print(f"✅ Objection: {result}")
    assert result["stage"] == "OBJECTION"
    
    # Тест 3: контакт
    result = await analyze(
        message="Давайте, мой телеграм @ivan",
        state_summary="Цель: инвестиция. Бюджет: 7 млн. Встреча предложена.",
        signals={"has_contact": True, "has_objection": False},
        history=[
            {"role": "assistant", "content": "Могу отправить презентацию или организовать онлайн-показ?"},
        ]
    )
    print(f"✅ Closing: {result}")
    assert result["stage"] in ["CLOSING", "MEETING"]

asyncio.run(test())
```

---

## ОБЩИЕ ПРАВИЛА

### Зависимости (requirements.txt)

```
fastapi>=0.115.0
uvicorn>=0.34.0
aiosqlite>=0.20.0
openai>=1.66.0
chromadb>=0.6.0
python-dotenv>=1.0.0
```

### Git-воркфлоу

После каждого файла:
```bash
cd ~/Projects/an-eva
python -c "from <module> import *; print('OK')"  # быстрый импорт-тест
# Запустить полный тест из секции Тест
git add <file>.py requirements.txt
git commit -m "phase1: <file>.py — описание"
```

После всех 5 файлов:
```bash
git push
```

### Чего НЕ делать
- НЕ создавать main.py (это Фаза 4)
- НЕ создавать generator.py (это Фаза 2)
- НЕ создавать rag_module.py (это Фаза 2)
- НЕ создавать промпты (это Фаза 3)
- НЕ менять файлы в refs/, data/, services/
- НЕ использовать Chat Completions API — только Responses API
- НЕ делать синхронные вызовы SQLite — только aiosqlite

### .env (создать в корне проекта для локального тестирования)

```
OPENAI_API_KEY=sk-...
PORT=8005
MODEL=gpt-5.2
```

---

## ПРОВЕРКА ЗАВЕРШЕНИЯ ФАЗЫ 1

После всех 5 файлов должно работать:

```python
import asyncio
from state_manager import StateManager
from message_processor import process_message
from analyzer import analyze
from config import ANALYZER_HISTORY

async def full_test():
    sm = StateManager()
    await sm.init()
    
    # Создать сессию
    user_id = await sm.create_session("full-test-001")
    
    # Обработать сообщение
    result = await process_message(
        message="Добрый день! Хочу инвестировать в недвижимость на Алтае, бюджет 7-8 миллионов",
        session_id="full-test-001",
        user_id=user_id,
        state_manager=sm
    )
    
    # Сохранить сообщение в историю
    await sm.save_message("full-test-001", user_id, "user", 
                          "Добрый день! Хочу инвестировать в недвижимость на Алтае, бюджет 7-8 миллионов")
    
    # Analyzer
    history = await sm.get_history("full-test-001", limit=ANALYZER_HISTORY)
    analysis = await analyze(
        message="Добрый день! Хочу инвестировать в недвижимость на Алтае, бюджет 7-8 миллионов",
        state_summary=result["state_summary"],
        signals=result["signals"],
        history=history,
    )
    
    print(f"✅ Extracted: {result['extracted']}")
    print(f"✅ State: {result['state_summary']}")
    print(f"✅ Signals: {result['signals']}")
    print(f"✅ Analysis: {analysis}")
    
    assert analysis["stage"] in ["GREETING", "QUALIFICATION"]
    assert analysis["rag_query"] is not None
    
    await sm.close()
    print("\n🎉 ФАЗА 1 ЗАВЕРШЕНА УСПЕШНО")

asyncio.run(full_test())
```
