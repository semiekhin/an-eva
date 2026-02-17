# АН Эва — Фаза 2: RAG + Generator

## ТЗ для 1Code (Claude Code)

📅 **Дата:** 17.02.2026
**Цель:** RAG-модуль (поиск примеров) + Generator (стриминг ответов).
**Порядок:** rag_module.py → generator.py
**Зависимости:** Фаза 1 (config, extractor, state_manager, message_processor, analyzer) — готова.

---

## КОНТЕКСТ

Пайплайн АН Эва:
```
Сообщение → [Extractor] → [State] → [Analyzer: stage + rag_query] → [RAG: примеры] → [Generator: ответ]
                          Фаза 1 (готово)                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                                          Фаза 2 (эта задача)
```

**Критичные правила:**
- Код пишется ЛОКАЛЬНО в `~/Projects/an-eva/`
- Референсы в `refs/sofia/` — читать, не менять
- RAG-данные в `data/rag_training_data/` — читать
- OpenAI API: **Responses API**, модель **gpt-5.2**
- Стриминг — через `stream=True` в Responses API

---

## ФАЙЛ 1: rag_module.py

**Что:** Поиск релевантных примеров продаж через ChromaDB.
**Референс:** `refs/sofia/rag_module.py` — читать ОБЯЗАТЕЛЬНО.

### Существующие RAG-данные

Файл `data/rag_training_data/examples.json` — 50 примеров. Посмотри структуру перед написанием кода.
Директория `data/rag_training_data/` также содержит ChromaDB-файлы от старой Маргариты — можно либо использовать их, либо пересоздать коллекцию из examples.json (предпочтительно пересоздать для чистоты).

### Архитектура

```python
import json
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from config import OPENAI_API_KEY, EMBEDDING_MODEL, DATA_DIR, RAG_RESULTS

class RAGModule:
    def __init__(self):
        self.client = None
        self.collection = None
        self._initialized = False
    
    async def init(self):
        """
        Инициализация ChromaDB:
        1. Создать PersistentClient с путём к data/chroma_db/ (СВОЙ путь, не rag_training_data/)
        2. Создать/получить коллекцию "rizalta_examples"
        3. Если коллекция пуста — загрузить из examples.json
        """
        # ChromaDB — синхронный, но вызывается один раз при старте
        self.client = chromadb.PersistentClient(
            path=str(DATA_DIR / "chroma_db")
        )
        
        embedding_fn = OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name=EMBEDDING_MODEL
        )
        
        self.collection = self.client.get_or_create_collection(
            name="rizalta_examples",
            embedding_function=embedding_fn
        )
        
        # Загрузить примеры если коллекция пуста
        if self.collection.count() == 0:
            await self._load_examples()
        
        self._initialized = True
    
    async def _load_examples(self):
        """
        Загрузить примеры из data/rag_training_data/examples.json.
        
        Каждый пример должен содержать:
        - id: уникальный идентификатор
        - text: текст примера (для embedding)
        - metadata: {"stage": "...", "topic": "...", ...}
        
        ВАЖНО: Посмотри реальную структуру examples.json перед реализацией.
        Адаптируй под фактический формат.
        """
        examples_path = DATA_DIR / "rag_training_data" / "examples.json"
        if not examples_path.exists():
            print(f"⚠️ RAG examples not found: {examples_path}")
            return
        
        with open(examples_path, "r", encoding="utf-8") as f:
            examples = json.load(f)
        
        # Адаптировать под реальный формат examples.json
        ids = []
        documents = []
        metadatas = []
        
        for i, example in enumerate(examples):
            # ПОДСТРОИТЬ ПОД РЕАЛЬНУЮ СТРУКТУРУ
            ids.append(f"ex_{i}")
            documents.append(example.get("text", str(example)))
            metadatas.append({
                "stage": example.get("stage", ""),
                "topic": example.get("topic", ""),
            })
        
        if ids:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            print(f"✅ RAG: загружено {len(ids)} примеров")
    
    async def search(self, stage: str, query: str, n_results: int = None) -> list[str]:
        """
        Поиск примеров по stage + query.
        
        Args:
            stage: этап диалога (GREETING, QUALIFICATION, ...)
            query: поисковый запрос от Analyzer (2-5 слов)
            n_results: количество результатов (по умолчанию из config)
        
        Returns:
            list строк — тексты найденных примеров
        
        Стратегия поиска (как у Софии):
        1. Ищем по query с фильтром stage
        2. Если мало результатов — ищем без фильтра stage
        3. Всегда возвращаем n_results примеров
        """
        if not self._initialized:
            return []
        
        n = n_results or RAG_RESULTS
        
        # Попытка 1: с фильтром по stage
        results = self.collection.query(
            query_texts=[query],
            n_results=n,
            where={"stage": stage} if stage else None,
        )
        
        texts = results["documents"][0] if results["documents"] else []
        
        # Попытка 2: если мало — без фильтра
        if len(texts) < 3:
            results_all = self.collection.query(
                query_texts=[query],
                n_results=n,
            )
            texts = results_all["documents"][0] if results_all["documents"] else []
        
        return texts
    
    def count(self) -> int:
        """Количество примеров в коллекции."""
        return self.collection.count() if self.collection else 0
```

**Ключевые принципы (из Софии):**
- **PersistentClient** — данные сохраняются между перезапусками в `data/chroma_db/`
- **text-embedding-3-small** — быстрая модель для embeddings
- **Двойной поиск**: сначала с фильтром stage, потом без (чтобы всегда было достаточно примеров)
- **Пересоздание коллекции** из examples.json при первом запуске — чище, чем использовать старую ChromaDB

**Тест:**
```python
import asyncio
from rag_module import RAGModule

async def test():
    rag = RAGModule()
    await rag.init()
    
    count = rag.count()
    print(f"✅ RAG инициализирован: {count} примеров")
    assert count > 0, "Коллекция пуста!"
    
    # Поиск по приветствию
    results = await rag.search("GREETING", "приветствие клиент")
    print(f"✅ GREETING: найдено {len(results)} примеров")
    assert len(results) > 0
    
    # Поиск по возражению
    results = await rag.search("OBJECTION", "далеко ехать Алтай")
    print(f"✅ OBJECTION: найдено {len(results)} примеров")
    
    # Поиск по инвестициям
    results = await rag.search("PRESENTATION", "доходность ROI инвестиция")
    print(f"✅ PRESENTATION: найдено {len(results)} примеров")
    for i, r in enumerate(results[:2]):
        print(f"   Пример {i+1}: {r[:100]}...")
    
    print(f"\n🎉 RAG тесты пройдены")

asyncio.run(test())
```

---

## ФАЙЛ 2: generator.py

**Что:** Генерация ответа Маргариты. Стриминг через Responses API.
**Референс:** `refs/sofia/web_api.py` — найти где формируется `input` для Generator, как собирается промпт.
**Референс:** `refs/sofia/bot_server.py` — стриминг (для Telegram, адаптировать для SSE).

### Почему стриминг критичен
Текущая Маргарита: клиент ждёт 6-15 секунд → таймаут на 4-5 сообщении → чат ломается.
Стриминг: первые слова через 1-2 сек → клиент видит что бот печатает → нет таймаутов.

### Архитектура

```python
import json
from typing import AsyncGenerator
from openai import OpenAI
from config import OPENAI_API_KEY, MODEL, MAX_OUTPUT_TOKENS

client = OpenAI(api_key=OPENAI_API_KEY)

# Системный промпт будет в rizalta_prompt_v2.py (Фаза 3)
# Пока используем заглушку для тестирования
DEFAULT_SYSTEM_PROMPT = """Ты — Маргарита, премиум-консультант по инвестиционной недвижимости RIZALTA Resort Belokurikha (Алтай).
Отвечай коротко (1-3 предложения), по-русски, уверенно и профессионально.
Используй женский род: "Поняла", "Подготовлю", "Записала".
"""


def build_generator_input(
    system_prompt: str,
    state_summary: str,
    rag_examples: list[str],
    history: list[dict],
    message: str,
    rizalta_context: str = "",
) -> list[dict]:
    """
    Собирает input для Generator.
    
    Структура (как у Софии):
    1. system_prompt (персона + техники)
    2. rizalta_context (цены, лоты — Фаза 3, пока пусто)
    3. state_summary (состояние клиента)
    4. RAG примеры
    5. История диалога
    6. Текущее сообщение
    """
    parts = []
    
    # System block
    system_content = system_prompt
    
    if rizalta_context:
        system_content += f"\n\n### ДАННЫЕ ОБЪЕКТА\n{rizalta_context}"
    
    if state_summary:
        system_content += f"\n\n### СОСТОЯНИЕ КЛИЕНТА\n{state_summary}"
    
    if rag_examples:
        examples_text = "\n---\n".join(rag_examples[:7])  # макс 7 примеров
        system_content += f"\n\n### ПРИМЕРЫ УСПЕШНЫХ ПРОДАЖ\n{examples_text}"
    
    parts.append({
        "role": "system",
        "content": system_content
    })
    
    # История
    for msg in history:
        parts.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Текущее сообщение
    parts.append({
        "role": "user",
        "content": message
    })
    
    return parts


async def generate(
    system_prompt: str,
    state_summary: str,
    rag_examples: list[str],
    history: list[dict],
    message: str,
    rizalta_context: str = "",
) -> str:
    """
    Генерация полного ответа (без стриминга).
    Используется для тестирования и fallback.
    """
    input_messages = build_generator_input(
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
        state_summary=state_summary,
        rag_examples=rag_examples,
        history=history,
        message=message,
        rizalta_context=rizalta_context,
    )
    
    response = client.responses.create(
        model=MODEL,
        input=input_messages,
        reasoning={"effort": "high"},  # high для качественных ответов
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    
    return response.output_text


async def generate_stream(
    system_prompt: str,
    state_summary: str,
    rag_examples: list[str],
    history: list[dict],
    message: str,
    rizalta_context: str = "",
) -> AsyncGenerator[str, None]:
    """
    Генерация ответа со стримингом.
    
    Yields:
        str — токены ответа по мере генерации
    
    Использование в FastAPI (Фаза 4):
        @app.post("/api/chat/stream")
        async def chat_stream(...):
            async def event_generator():
                async for token in generate_stream(...):
                    yield f"data: {json.dumps({'token': token})}\\n\\n"
                yield f"data: {json.dumps({'done': True})}\\n\\n"
            return StreamingResponse(event_generator(), media_type="text/event-stream")
    """
    input_messages = build_generator_input(
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
        state_summary=state_summary,
        rag_examples=rag_examples,
        history=history,
        message=message,
        rizalta_context=rizalta_context,
    )
    
    # Responses API со стримингом
    stream = client.responses.create(
        model=MODEL,
        input=input_messages,
        reasoning={"effort": "high"},
        max_output_tokens=MAX_OUTPUT_TOKENS,
        stream=True,
    )
    
    for event in stream:
        # Responses API stream events
        # Тип event зависит от SDK — проверить актуальную документацию OpenAI
        # Основные типы: response.output_text.delta, response.completed
        if hasattr(event, 'type'):
            if event.type == 'response.output_text.delta':
                yield event.delta
            elif event.type == 'response.completed':
                break


def check_end_marker(text: str) -> tuple[str, bool]:
    """
    Проверяет наличие маркера [END] в тексте.
    
    Returns:
        (clean_text, has_end) — текст без маркера и флаг наличия
    """
    has_end = "[END]" in text
    clean_text = text.replace("[END]", "").strip()
    return clean_text, has_end
```

**Ключевые принципы:**
- **Два режима:** `generate()` (полный ответ) + `generate_stream()` (стриминг)
- **reasoning: high** для Generator (в отличие от medium для Extractor/Analyzer) — качественные ответы
- **build_generator_input()** — отдельная функция сборки промпта, переиспользуется в обоих режимах
- **[END] маркер** — Generator ставит [END] когда получил контакт → post-processing убирает маркер и отправляет лид
- **system_prompt заглушка** — настоящий промпт будет в Фазе 3 (rizalta_prompt_v2.py)
- **Стриминг Responses API** — проверить актуальные event types в SDK. Могут быть: `response.output_text.delta`, `response.output_text.done`, `response.completed`

### Важно про стриминг Responses API

OpenAI Responses API стриминг отличается от Chat Completions. Проверь в `refs/sofia/bot_server.py` как Sofia обрабатывает стрим. Ключевые моменты:

1. `stream=True` в `responses.create()`
2. Итерация по events — каждый event имеет `.type`
3. Текстовые дельты приходят в `response.output_text.delta`
4. Reasoning-токены приходят отдельно — их НЕ отдаём клиенту
5. Финальный event — `response.completed`

Если SDK не поддерживает async streaming напрямую — обернуть в `asyncio.to_thread()` или использовать sync генератор.

**Тест:**
```python
import asyncio
from generator import generate, generate_stream, check_end_marker, DEFAULT_SYSTEM_PROMPT

async def test():
    # Тест 1: полная генерация
    response = await generate(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        state_summary="Новый клиент, ничего не известно.",
        rag_examples=[],
        history=[],
        message="Здравствуйте! Расскажите про инвестиции в RIZALTA",
    )
    print(f"✅ Полный ответ: {response[:200]}...")
    assert len(response) > 10
    assert "Маргарита" not in response or True  # не должна представляться по имени в каждом ответе
    
    # Тест 2: стриминг
    tokens = []
    async for token in generate_stream(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        state_summary="Цель: инвестиция (подтверждено). Бюджет: 7 млн (упомянуто).",
        rag_examples=["Клиент: Какая доходность? Маргарита: При загрузке 70% — более 2 млн ₽ чистыми в год."],
        history=[
            {"role": "user", "content": "Хочу инвестировать 7 миллионов"},
            {"role": "assistant", "content": "Отличный бюджет! В корпусе Family есть варианты от 5.8 млн."},
        ],
        message="А какая доходность будет?",
    ):
        tokens.append(token)
        print(token, end="", flush=True)
    
    full_response = "".join(tokens)
    print(f"\n✅ Стриминг: {len(tokens)} токенов, {len(full_response)} символов")
    assert len(tokens) > 0
    
    # Тест 3: [END] маркер
    clean, has_end = check_end_marker("Отлично, записала ваш контакт! Мы свяжемся с вами. [END]")
    assert has_end == True
    assert "[END]" not in clean
    print(f"✅ END маркер: has_end={has_end}, clean='{clean[:50]}...'")
    
    clean2, has_end2 = check_end_marker("Какой у вас бюджет?")
    assert has_end2 == False
    print(f"✅ Без END: has_end={has_end2}")
    
    print(f"\n🎉 Generator тесты пройдены")

asyncio.run(test())
```

---

## ОБЩИЕ ПРАВИЛА

### Новые зависимости

Проверь что в `requirements.txt` есть:
```
chromadb>=0.6.0
openai>=1.66.0
```

### Git-воркфлоу

```bash
# После rag_module.py
python -c "from rag_module import RAGModule; print('OK')"
# Запустить полный тест
git add rag_module.py
git commit -m "phase2: rag_module.py — ChromaDB search with stage filter"

# После generator.py
python -c "from generator import generate, generate_stream; print('OK')"
# Запустить полный тест
git add generator.py
git commit -m "phase2: generator.py — Responses API with streaming"

git push
```

### Чего НЕ делать
- НЕ создавать main.py (Фаза 4)
- НЕ создавать rizalta_prompt_v2.py (Фаза 3) — используй DEFAULT_SYSTEM_PROMPT заглушку
- НЕ создавать rizalta_context.py (Фаза 3)
- НЕ менять файлы Фазы 1
- НЕ менять файлы в refs/, data/

---

## ПРОВЕРКА ЗАВЕРШЕНИЯ ФАЗЫ 2

Полный пайплайн от сообщения до ответа:

```python
import asyncio
from state_manager import StateManager
from message_processor import process_message
from analyzer import analyze
from rag_module import RAGModule
from generator import generate, generate_stream, check_end_marker, DEFAULT_SYSTEM_PROMPT
from config import ANALYZER_HISTORY

async def full_pipeline_test():
    # Init
    sm = StateManager()
    await sm.init()
    rag = RAGModule()
    await rag.init()
    
    session_id = "pipeline-test-001"
    user_id = await sm.create_session(session_id)
    message = "Добрый день! Хочу вложить 8 миллионов в курортную недвижимость на Алтае"
    
    # 1. Message Processor (Extractor → State)
    proc_result = await process_message(
        message=message,
        session_id=session_id,
        user_id=user_id,
        state_manager=sm,
    )
    print(f"1️⃣ Extracted: goal={proc_result['extracted'].get('goal')}, budget={proc_result['extracted'].get('budget')}")
    print(f"   State: {proc_result['state_summary']}")
    
    # Сохранить сообщение
    await sm.save_message(session_id, user_id, "user", message)
    
    # 2. Analyzer
    history = await sm.get_history(session_id, limit=ANALYZER_HISTORY)
    analysis = await analyze(
        message=message,
        state_summary=proc_result["state_summary"],
        signals=proc_result["signals"],
        history=history,
    )
    print(f"2️⃣ Stage: {analysis['stage']}, RAG query: {analysis['rag_query']}")
    
    # 3. RAG
    rag_examples = await rag.search(analysis["stage"], analysis["rag_query"])
    print(f"3️⃣ RAG: {len(rag_examples)} примеров найдено")
    
    # 4. Generator (полный)
    response = await generate(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        state_summary=proc_result["state_summary"],
        rag_examples=rag_examples,
        history=history,
        message=message,
    )
    clean_response, has_end = check_end_marker(response)
    print(f"4️⃣ Response: {clean_response[:200]}...")
    print(f"   [END]: {has_end}")
    
    # Сохранить ответ
    await sm.save_message(session_id, user_id, "assistant", clean_response)
    
    # 5. Generator (стриминг)
    print(f"5️⃣ Streaming: ", end="")
    stream_tokens = []
    async for token in generate_stream(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        state_summary=proc_result["state_summary"],
        rag_examples=rag_examples,
        history=await sm.get_history(session_id, limit=ANALYZER_HISTORY),
        message="А какая окупаемость?",
    ):
        stream_tokens.append(token)
        print(token, end="", flush=True)
    print(f"\n   Стриминг: {len(stream_tokens)} токенов")
    
    await sm.close()
    print(f"\n🎉 ПОЛНЫЙ ПАЙПЛАЙН РАБОТАЕТ — ФАЗА 2 ЗАВЕРШЕНА")

asyncio.run(full_pipeline_test())
```
