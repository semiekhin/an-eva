# Текущий статус АН Эва

📅 **Последняя сессия:** 17.02.2026, 16:45 MSK
**Фаза:** 1–4 — Ядро + SSE + Лиды (бэкенд готов, фронт заблокирован Cloudflare)

## ✅ Что сделано 17.02.2026 (сессия 3, claude.ai)

### Бэкенд (всё работает, проверено curl):
- SSE-эндпоинт POST /api/chat/stream — потоковая отдача токенов
- lead_notifier.py — отправка лидов в Telegram через @RIZALTAEVA_bot
- Интеграция лидов в _full_pipeline() и /api/chat/stream
- Фильтрация [END] в generate_stream() — буферизация, клиент не видит маркер
- config.py: + TELEGRAM_BOT_TOKEN, TELEGRAM_NOTIFY_CHAT_ID, + CORS eva-dev
- .env: + TELEGRAM_BOT_TOKEN, TELEGRAM_NOTIFY_CHAT_ID

### Фронтенд (НЕ работает через Cloudflare):
- widget/chat.js переписан: SSE через ReadableStream + fallback на /api/chat
- sessionPromise — защита от race condition (двойной greeting)
- Flush буфера при завершении потока

### Проверено:
- curl localhost:8005 — SSE стримит посимвольно ✅
- curl через Cloudflare — SSE стримит ✅
- Лид в Telegram — приходит при [END] ✅
- Браузер через Cloudflare — SSE НЕ работает ❌ (буферизация CF)

## 🔄 Текущее состояние

### Работает:
- АН Эва на :8005 через systemd ✅
- Полный пайплайн: extractor → state → analyzer → RAG → generator ✅
- SSE стриминг (через curl) ✅
- Лиды → @RIZALTAEVA_bot (chat_id: 512319063) ✅
- [END] фильтрация в потоке ✅
- RAG — 50 примеров, семантический поиск ✅
- GitHub синхронизирован (нужен коммит сессии 3!) ⚠️
- Текущая Маргарита на :8001 — работает параллельно ✅

### НЕ работает:
- Виджет в браузере — Cloudflare буферизует SSE, клиент получает таймаут
- 7-10 сек до первого токена (3 последовательных LLM-вызова)
- Полный сценарий до [END] в браузере НЕ прогнан
- Observer (мониторинг в Telegram) не подключен

## ❌ Главная проблема: Cloudflare буферизует SSE

Cloudflare Tunnel проксирует трафик и копит SSE-токены в буфере.
curl работает (обходит буфер), браузер — нет.
Попытки починить padding (2KB, 8KB) и keepalive-комментариями — НЕ помогли.

### Решение: Nginx + Let's Encrypt (без Cloudflare для dev)
1. A-запись eva-dev.rizaltaservice.ru → 72.56.64.91 (в reg.ru DNS)
2. nginx reverse proxy → localhost:8005 с proxy_buffering off
3. certbot для SSL
4. Убрать Cloudflare tunnel для eva-dev

## 📁 Ключевые файлы на сервере /opt/an-eva/

### Ядро (сессия 2):
- main.py, config.py, extractor.py, state_manager.py, message_processor.py
- analyzer.py, rag_module.py, generator.py
- rizalta_prompt_v2.py, rizalta_context.py

### Новое (сессия 3):
- lead_notifier.py — отправка лидов в Telegram
- main.py — + /api/chat/stream, + _send_lead_notification()
- generator.py — фикс [END] буферизации в generate_stream()
- config.py — + TELEGRAM vars, + CORS
- widget/chat.js — полная перезапись (SSE + fallback)

### Прочее:
- widget/index.html — без изменений
- tests/ (11 файлов) — не обновлены
- .env (секреты, не в git)

## 🔜 Следующие задачи (приоритет)

### P0 — Блокеры:
1. Nginx + Let's Encrypt для eva-dev (убрать зависимость от CF)
2. Проверить SSE в браузере через nginx

### P1 — Скорость:
3. Параллельные вызовы extractor + analyzer (asyncio.gather) → -3 сек
4. Быстрая модель для extractor/analyzer (gpt-4o-mini вместо gpt-5.2)
5. Цель: < 5 сек до первого токена

### P2 — Тестирование:
6. Прогнать полный сценарий до [END] в браузере
7. Проверить greeting (один раз)
8. Тест лидов из браузера

### P3 — Продакшн:
9. Подключить виджет к лендингу rizaltabelokurikha.ru
10. Обновить docs/AN_EVA_CURRENT.md
11. Ротировать OpenAI API ключ (засвечен в чате!)

## ⚠️ Важный контекст

- Порт: 8005 (dev), 8001 только после замены старой Маргариты
- Путь: /opt/an-eva/
- Все существующие сервисы НЕ ТРОГАТЬ
- Процесс: 1Code (код) → merge+push (MacBook) → pull+restart (сервер)
- Сессия 3 сделана hotfix на сервере — НУЖЕН КОММИТ
- Лиды отправлять Sergio лично в Telegram, НЕ в Bitrix CRM
- Cloudflare tunnel НЕ подходит для SSE — нужен nginx

## 📊 Endpoints
```
GET  /api/health              — проверка
POST /api/session             — создание сессии + greeting
POST /api/session/resume      — восстановление сессии
POST /api/chat                — синхронный ответ (работает)
POST /api/chat/stream         — SSE стриминг (работает curl, НЕ работает браузер через CF)
GET  /api/history/{session_id} — история
GET  /api/docs/current        — этот файл
GET  /widget/                 — статика виджета
```
