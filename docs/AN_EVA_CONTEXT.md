# ⚠️ СУЩЕСТВУЮЩИЕ СЕРВИСЫ НЕ ТРОГАТЬ! ПОРТ 8005 (DEV)! ⚠️

# АН Эва — AI-консультант RIZALTA v1.1.0

📅 **Последняя сессия:** 18.02.2026
**Статус:** MVP работает, SSE стримит в браузере, лиды уходят в Telegram

## Что это

Веб-чат виджет с AI-консультантом «Маргарита» для лендинга rizaltabelokurikha.ru. Квалифицирует клиентов → презентует инвестиционные апартаменты → собирает контакт → отправляет лид в Telegram.

Архитектура основана на Sofia-GPT v3.0: Extractor → LLM-Analyzer → RAG → Generator.

---

## Инфраструктура

- **Сервер:** `ssh -p 2222 root@72.56.64.91` (Timeweb, 4 vCPU, 8 GB RAM)
- **Путь:** `/opt/an-eva/`
- **Порт:** 8005 (dev) → 8001 только после замены старой Маргариты
- **systemd:** `an-eva.service` (enabled, active)
- **Домен:** `eva-dev.rizaltaservice.ru` → A-запись 72.56.64.91 (DNS only, nginx + Let's Encrypt)
- **GitHub:** github.com/semiekhin/an-eva (public)
- **Разработка:** 1Code на MacBook `~/Projects/an-eva/` → merge+push → pull+restart на сервере
- **Worktree 1Code:** `~/.21st/worktrees/an-eva/` — коммитить и мержить вручную

## Стек

- Python 3.12 + FastAPI + uvicorn
- OpenAI Responses API — extractor/analyzer (gpt-4o-mini), generator (gpt-5.2)
- ChromaDB 1.5.0 — RAG (50 примеров)
- aiosqlite (WAL mode) — состояние клиентов, история, сессии
- aiohttp — отправка лидов в Telegram
- Vanilla JS виджет (без фреймворков)
- nginx + Let's Encrypt (reverse proxy, SSE без буферизации)

---

## Пайплайн обработки сообщения

```
Клиент → виджет → POST /api/chat/stream
  │
  ├─ 1. save_message (user)
  ├─ 2. get_history
  ├─ 3. process_message:
  │     ├─ get_state (SQLite)
  │     ├─ extract (OpenAI gpt-4o-mini) → NLU: goal, budget, payment, objection...
  │     └─ merge_extraction → update_state (SQLite)
  ├─ 4. analyze (OpenAI gpt-4o-mini) → stage + rag_query
  ├─ 5. search_examples (ChromaDB) → RAG примеры (top 7)
  ├─ 6. build_system_prompt (persona + state + context + RAG)
  ├─ 7. generate_stream (OpenAI gpt-5.2, stream=True) → SSE токены
  ├─ 8. [END] detection → lead_notifier → Telegram
  └─ 9. save_message (assistant)
```

---

## Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/health` | Проверка сервиса |
| POST | `/api/session` | Создание сессии + greeting (body: `{}`) |
| POST | `/api/session/resume` | Восстановление сессии |
| POST | `/api/chat` | Синхронный ответ (без стриминга) |
| POST | `/api/chat/stream` | SSE стриминг (основной) |
| GET | `/api/history/{session_id}` | История диалога |
| GET | `/api/docs/current` | Текущий статус (MD, без кеша) |
| GET | `/api/docs/context` | Полный контекст проекта (MD, без кеша) |
| GET | `/widget/` | Статика виджета |

---

## Файловая структура

```
/opt/an-eva/
├── main.py                  (401 строк) — FastAPI, endpoints, пайплайн, SSE
├── config.py                (95 строк)  — настройки, env-переменные, константы
├── extractor.py             (319 строк) — NLU: извлечение данных из сообщений (gpt-4o-mini)
├── state_manager.py         (365 строк) — SQLite: состояние клиента, история, сессии
├── message_processor.py     (87 строк)  — оркестратор: extractor → state → signals
├── analyzer.py              (117 строк) — определение этапа диалога + RAG-запрос (gpt-4o-mini)
├── rag_module.py            (232 строк) — ChromaDB: семантический поиск примеров
├── generator.py             (213 строк) — генерация ответа, stream/non-stream (gpt-5.2)
├── lead_notifier.py         (85 строк)  — отправка лидов в Telegram @RIZALTAEVA_bot
├── rizalta_prompt_v2.py     (262 строк) — системный промпт Маргариты (персона, техники)
├── rizalta_context.py       (65 строк)  — объектные данные RIZALTA (цены, корпуса, ROI)
├── .env                     — секреты (не в git)
├── .gitignore
├── PHASE1_SPEC.md … PHASE4_SPEC.md — спецификации фаз разработки
│
├── widget/
│   ├── index.html           (283 строк) — HTML виджета (CSS внутри)
│   └── chat.js              (327 строк) — JS: SSE + fallback на /api/chat
│
├── data/
│   ├── properties.db        — 348 лотов (Family 255 + Business 103)
│   ├── corp3_units.json     — корпус Digital (128 avail / 154 sold)
│   ├── units.json           — все юниты
│   ├── rizalta_knowledge.md — база знаний о RIZALTA
│   ├── chroma_db/           — основная ChromaDB (коллекция rizalta_sales)
│   └── rag_training_data/   — 50 RAG-примеров + ChromaDB
│       └── examples.json
│
├── db/
│   └── an_eva.db            — SQLite: сессии, состояния, история (WAL mode)
│
├── services/
│   ├── investment_calc.py   — калькулятор ROI
│   ├── installment_calculator.py — рассрочка
│   ├── deposit_calculator.py — сравнение с депозитом
│   └── calculations.py      — общие расчёты
│
├── docs/
│   ├── AN_EVA_CONTEXT.md    — этот файл (полный контекст проекта)
│   ├── AN_EVA_CURRENT.md    — текущий статус (обновляется каждую сессию)
│   ├── AN_EVA_PROJECT.md    — проектный документ (архитектура, ТЗ)
│   ├── AN_EVA_KNOWLEDGE.md  — база знаний
│   ├── SESSION_END_TEMPLATE.md — шаблон завершения сессии
│   └── CHANGELOG.md
│
├── refs/                    — референсные файлы (read-only)
│   ├── sofia/               — архитектура Sofia-GPT
│   └── margarita/           — старая Маргарита (виджет, промпт)
│
└── tests/                   — 11 тестовых файлов
```

**Всего:** ~2756 строк кода (без тестов, данных, документации)

---

## Корпуса RIZALTA

- **Корпус 1 «Family»:** 255 лотов (properties.db)
- **Корпус 2 «Business»:** 103 лота (properties.db) — СКРЫТ
- **Корпус 3 «Digital»:** 128 available / 154 sold (corp3_units.json, whitelist)

---

## ✅ Что работает

- Полный пайплайн extractor → state → analyzer → RAG → generator ✅
- SSE стриминг в браузере через nginx + Let's Encrypt ✅
- Синхронный /api/chat (fallback) ✅
- Лиды → @RIZALTAEVA_bot в Telegram при [END] ✅
- [END] фильтрация в потоке (буферизация токенов) ✅
- Виджет: greeting, диалог, сбор контакта — полный цикл ✅
- Сессии с persistence (localStorage) ✅
- RAG — 50 примеров, семантический поиск по stage ✅
- Старая Маргарита на :8001 — работает параллельно ✅

---

## ❌ Известные проблемы

### Проблема: ~11 сек до первого токена (отложена)
Два последовательных LLM-вызова (extractor ~5с + analyzer ~2.3с) + RAG (~2.6с) + generator start (~0.6с).
Промпт extractor-а ~250 строк — тяжёлый даже для gpt-4o-mini.

**Возможные решения (когда вернёмся к оптимизации):**
- Объединить extractor + analyzer в один LLM-вызов
- Упростить промпт extractor-а
- Chat Completions API вместо Responses API (может быть быстрее)
- Сервер в России, API в США — сетевая задержка неизбежна

---

## 🔜 Задачи (приоритет)

### P3 — Подключение к лендингу (следующая сессия):
1. Посмотреть HTML лендинга rizaltabelokurikha.ru — как подключена старая Маргарита
2. Заменить ссылку/iframe на АН Эву (eva-dev.rizaltaservice.ru)
3. Лендинг на reg.ru (IP: 31.31.196.78, другой сервер)
4. Мобильное тестирование

### P1 — Оптимизация скорости (отложена):
5. Объединить extractor+analyzer в один вызов или упростить промпт
6. Цель: < 5 сек до первого токена

### P4 — Дополнительное:
7. Observer (мониторинг в Telegram)
8. Deep links из Telegram бота в веб-чат
9. Расширение RAG (больше примеров)
10. Замена старой Маргариты (:8001 → :8005 переключение)

---

## ⚠️ Принцип изоляции — существующие сервисы НЕ ТРОГАТЬ

| Сервис | Путь | Порт | Статус |
|--------|------|------|--------|
| Sofia-GPT | `/opt/sofia-gpt/` | — | 🔒 НЕ ТРОГАТЬ |
| RIZALTA Bot PROD | `/opt/bot/` | 8000 | 🔒 НЕ ТРОГАТЬ |
| RIZALTA Bot DEV | `/opt/bot-dev/` | 8002 | 🔒 НЕ ТРОГАТЬ |
| WebChat (старая Маргарита) | `/opt/rizalta-webchat/` | 8001 | 🔒 НЕ ТРОГАТЬ (до замены) |
| WebApp PROD | — | 8003 | 🔒 НЕ ТРОГАТЬ |
| WebApp DEV | — | 8004 | 🔒 НЕ ТРОГАТЬ |

---

## Процесс разработки

1. **1Code (MacBook):** пишем код в `~/Projects/an-eva/`
2. **Merge + push:** `cd ~/Projects/an-eva && git merge <branch> && git push`
3. **Сервер:** `cd /opt/an-eva && git pull && systemctl restart an-eva`
4. **На сервере НЕ редактировать** код (кроме .env и hotfix с немедленным коммитом)
5. **Hotfix на сервере:** `git add -A && git commit -m "hotfix: ..." && git push` → потом pull на MacBook

---

## nginx конфиг

Файл: `/etc/nginx/sites-enabled/eva-dev`
- Reverse proxy → localhost:8005
- `proxy_buffering off` — для SSE
- SSL: Let's Encrypt (автообновление certbot)
- Без Cloudflare (A-запись DNS only)

---

## Лиды

**Куда:** Sergio лично в Telegram (chat_id: 512319063) через @RIZALTAEVA_bot
**НЕ в Bitrix CRM!**
**Формат:** тип лида, контакт клиента, квалификация, последние сообщения

---

## 📎 Ссылки

**Актуальные (сервер, без кеша):**
- https://eva-dev.rizaltaservice.ru/api/docs/context
- https://eva-dev.rizaltaservice.ru/api/docs/current

**GitHub:**
- https://github.com/semiekhin/an-eva

**Лендинг (целевой сайт):**
- https://rizaltabelokurikha.ru (IP: 31.31.196.78, хостинг reg.ru)

---

Перед началом работы уточни: есть ли доступ к серверу?
Если нужны детали — читай документацию: `cat /opt/an-eva/docs/AN_EVA_*.md`
