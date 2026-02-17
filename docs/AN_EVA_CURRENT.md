# Текущий статус АН Эва

📅 **Последняя сессия:** 17.02.2026, 15:00 MSK
**Фаза:** 1–4 — Ядро написано, сервис запущен на DEV

## ✅ Что сделано 17.02.2026 (сессия 2)
- Merge ветки functional-gopher-db8bc3 в main (25 файлов, 3975 строк)
- Push на GitHub — репо больше не пустой
- Cloudflare tunnel: eva-dev.rizaltaservice.ru → :8005 (через PROD tunnel)
- RAG починен: list_collections() → get_or_create_collection (ChromaDB 1.5.0)
- .env создан на сервере (OPENAI_API_KEY, PORT=8005)
- systemd сервис an-eva запущен и включен (enable)
- Полный пайплайн протестирован: session → chat → ответ с конкретикой
- Процесс разработки зафиксирован: 1Code → merge → push → pull на сервер

## 🔄 Текущее состояние
### Работает:
- АН Эва на :8005 через systemd ✅
- eva-dev.rizaltaservice.ru — внешний доступ ✅
- RAG — 50 примеров, семантический поиск ✅
- Полный пайплайн: extractor → state → analyzer → RAG → generator ✅
- GitHub синхронизирован с MacBook и сервером ✅
- Текущая Маргарита на :8001 — работает параллельно ✅

### Не сделано:
- Стриминг (SSE) — ответы приходят целиком, нет посимвольной отправки
- Виджет не подключен к АН Эве (всё ещё смотрит на старую Маргариту)
- CRM интеграция (Bitrix) не настроена
- Observer (мониторинг в Telegram) не подключен
- Полный сценарий до [END] не прогнан
- OpenAI ключ: старые ключи скомпрометированы (были в чате), рекомендуется перевыпуск

## 📁 Структура на сервере
```
/opt/an-eva/
├── main.py                    ✅ FastAPI, эндпоинты, lifespan
├── config.py                  ✅ Настройки, порт 8005
├── extractor.py               ✅ NLU ~10 полей
├── state_manager.py           ✅ SQLite + aiosqlite
├── message_processor.py       ✅ Extractor → State → Signals
├── analyzer.py                ✅ LLM-Analyzer (stage + rag_query)
├── rag_module.py              ✅ ChromaDB 1.5.0, 50 примеров
├── generator.py               ✅ gpt-5.2, Responses API
├── rizalta_prompt_v2.py       ✅ Промпт Маргариты
├── rizalta_context.py         ✅ Объектный контекст RIZALTA
├── .env                       ✅ Секреты (не в git)
├── tests/                     ✅ 11 тест-файлов
├── widget/
│   ├── index.html             ✅ Виджет чата
│   └── chat.js                ✅ JS логика
├── data/
│   ├── properties.db          ✅ 348 лотов
│   ├── rag_training_data/     ✅ 50 примеров + ChromaDB индекс
│   └── ...                    ✅ Остальные данные
├── services/                  ✅ Калькуляторы
├── db/                        ✅ Папка создана
└── docs/                      ✅ Документация
```

## 🔜 Следующий шаг
1. Подключить виджет к eva-dev.rizaltaservice.ru для тестирования
2. Прогнать полный сценарий: приветствие → квалификация → презентация → сбор контакта → [END]
3. Реализовать стриминг (SSE) — критично для UX
4. Перевыпустить OpenAI ключ

## ⚠️ Важный контекст для следующего чата
- АН Эва ЗАПУЩЕНА на :8005, доступна через eva-dev.rizaltaservice.ru
- Процесс: 1Code (код) → merge+push (терминал MacBook) → pull+restart (сервер)
- На сервере НИКОГДА не редактировать код (кроме .env). Исключение — hotfix с немедленным коммитом
- RAG фикс был сделан на сервере и закоммичен оттуда (долг закрыт)
- Cloudflare: eva-dev добавлен в PROD tunnel config.yml (не отдельный tunnel)
- Старая Маргарита на :8001 — не трогать до полной готовности АН Эвы
