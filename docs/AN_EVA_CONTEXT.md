# ⚠️ СУЩЕСТВУЮЩИЕ СЕРВИСЫ НЕ ТРОГАТЬ! ПОРТ 8005 (DEV)! ⚠️

# АН Эва — AI-консультант RIZALTA v1.2.0

📅 **Последнее обновление:** 19.02.2026 (сессия 5)
**Статус:** Виджет на боевом лендинге, воронка в доработке

## Что это

Веб-чат виджет с AI-консультантом **«Марго»** для лендинга rizaltabelokurikha.ru. Квалифицирует клиентов → презентует инвестиционные апартаменты → собирает контакт → отправляет лид в Telegram.

Архитектура основана на Sofia-GPT v3.0: Extractor → LLM-Analyzer → RAG → Generator.

---

## Инфраструктура

- **Сервер:** `ssh -p 2222 root@72.56.64.91` (Timeweb, 4 vCPU, 8 GB RAM)
- **Путь:** `/opt/an-eva/`
- **Порт:** 8005 (dev) → 8001 только после замены старой Маргариты
- **systemd:** `an-eva.service` (enabled, active)
- **Домен:** `eva-dev.rizaltaservice.ru` → A-запись 72.56.64.91 (DNS only, nginx + Let's Encrypt)
- **Лендинг:** `rizaltabelokurikha.ru` (reg.ru, IP 31.31.196.78) — виджет подключён
- **GitHub:** github.com/semiekhin/an-eva (public)
- **Разработка:** 1Code на MacBook `~/Projects/an-eva/` → merge+push → pull+restart на сервере
- **Worktree 1Code:** `~/.21st/worktrees/an-eva/` — коммитить и мержить вручную

## Стек

- Python 3.12 + FastAPI + uvicorn
- OpenAI Responses API: **gpt-4o-mini** (extractor, analyzer), **gpt-5.2** (generator)
- ChromaDB 1.5.0 — RAG (50 примеров)
- aiosqlite (WAL mode) — состояние клиентов, история, сессии
- aiohttp — отправка лидов в Telegram
- Vanilla JS виджет — embeddable `chat-widget.js` (без фреймворков)
- nginx + Let's Encrypt (reverse proxy, SSE без буферизации)

---

## Пайплайн обработки сообщения

```
Клиент → виджет на rizaltabelokurikha.ru → POST /api/chat/stream (eva-dev.rizaltaservice.ru)
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

Extractor и analyzer последовательны (analyzer зависит от extractor). Параллелизация невозможна.

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
| GET | `/api/docs/context` | Этот файл (MD, без кеша) |
| GET | `/api/docs/current` | Текущий статус (MD, без кеша) |
| GET | `/widget/` | Статика виджета |

---

## Файловая структура

```
/opt/an-eva/
├── main.py                  — FastAPI, endpoints, пайплайн, SSE
├── config.py                — настройки, env-переменные, константы, CORS
├── extractor.py             — NLU: извлечение данных из сообщений (gpt-4o-mini)
├── state_manager.py         — SQLite: состояние клиента, история, сессии
├── message_processor.py     — оркестратор: extractor → state → signals
├── analyzer.py              — определение этапа диалога + RAG-запрос (gpt-4o-mini)
├── rag_module.py            — ChromaDB: семантический поиск примеров
├── generator.py             — генерация ответа, stream/non-stream (gpt-5.2)
├── lead_notifier.py         — отправка лидов в Telegram @RIZALTAEVA_bot
├── rizalta_prompt_v2.py     — системный промпт Марго (персона, техники, воронка)
├── rizalta_context.py       — объектные данные RIZALTA (корпуса, витрина лотов, цены)
├── .env                     — секреты (не в git)
│
├── widget/
│   ├── index.html           — HTML виджета (standalone, для тестирования)
│   ├── chat.js              — JS виджета (standalone)
│   └── chat-widget.js       — EMBEDDABLE виджет (подключён к лендингу)
│
├── data/
│   ├── properties.db        — Family 255 лотов + Business 105 лотов (SQLite)
│   ├── corp3_units.json     — Digital 128 available (JSON)
│   ├── units.json           — все юниты
│   ├── rizalta_knowledge.md — база знаний о RIZALTA
│   ├── chroma_db/           — основная ChromaDB
│   └── rag_training_data/   — 50 RAG-примеров
│
├── db/
│   └── an_eva.db            — SQLite: сессии, состояния, история (WAL mode)
│
├── services/                — НЕ подключены к пайплайну (будущий function calling)
│   ├── investment_calc.py   — калькулятор ROI
│   ├── installment_calculator.py — рассрочка
│   ├── deposit_calculator.py — сравнение с депозитом
│   └── calculations.py      — общие расчёты
│
├── docs/
│   ├── AN_EVA_CONTEXT.md    — этот файл
│   ├── AN_EVA_CURRENT.md    — текущий статус
│   ├── AN_EVA_PROJECT.md    — проектный документ
│   └── AN_EVA_KNOWLEDGE.md  — база знаний
│
├── refs/                    — референсные файлы (read-only)
└── tests/
```

---

## Корпуса RIZALTA (продаются три)

| Корпус | Лотов avail | Площадь | Цена от | Источник |
|--------|-------------|---------|---------|----------|
| Family (1) | 255 | 22–85 м² | 14.3 млн | properties.db |
| Business (2) | 105 | 24.5–113 м² | 18.8 млн | properties.db |
| Digital (3) | 128 | 23.5–152 м² | 14.5 млн | corp3_units.json |

Legend и Wellness — НЕ продаются, убраны из контекста.

### Витрина лотов (в rizalta_context.py):
- Family, 22 м², 6 этаж — 14.3 млн (точка входа)
- Family, 40.9 м², 9 этаж — 25.8 млн
- Digital, 23.5 м², 6 этаж — 14.5 млн
- Digital, 41.5 м², 1 этаж — 24.4 млн
- Business, 24.5 м², 2 этаж — 18.8 млн
- Business, 80 м², 9 этаж — 56.7 млн

---

## Виджет на лендинге

**Как подключён:**
На `rizaltabelokurikha.ru` (reg.ru) одна строка перед `</body>`:
```html
<script src="https://eva-dev.rizaltaservice.ru/widget/chat-widget.js"></script>
```

**Что делает chat-widget.js:**
- Самодостаточный embeddable скрипт (инжектит HTML+CSS+JS)
- Экспортирует `window.openBot()` — 3 кнопки на лендинге вызывают эту функцию
- SSE стриминг + fallback на `/api/chat`
- Сессии с persistence (localStorage)
- Мобильная адаптация (fullscreen на <480px)
- Quick replies: «Рассчитать доход», «Цены и планировки», «Запланировать онлайн-показ»
- Постоянная кнопка: «📞 Связаться с отделом продаж»

**CORS настроен** в config.py — rizaltabelokurikha.ru в списке разрешённых.

---

## .env (секреты на сервере)

```
OPENAI_API_KEY=<ротирован 17.02>
PORT=8005
DEBUG=true
TELEGRAM_BOT_TOKEN=8115075748:AAEIvLiJMPZLMe4jeZJ3aM_yqyr0RRcZEmA
TELEGRAM_NOTIFY_CHAT_ID=512319063
```

---

## ✅ Что работает

- Виджет на боевом лендинге rizaltabelokurikha.ru ✅
- Марго (не Маргарита) — ребрендинг завершён ✅
- Полный пайплайн extractor → state → analyzer → RAG → generator ✅
- SSE стриминг в браузере через nginx + Let's Encrypt ✅
- Синхронный /api/chat (fallback) ✅
- Лиды → @RIZALTAEVA_bot в Telegram при [END] ✅
- [END] фильтрация в потоке ✅
- Реальные цены: Family от 14.3, Business от 18.8, Digital от 14.5 млн ✅
- Витрина 6 лотов из базы ✅
- Телефон убран — Марго только собирает контакт клиента ✅
- API ключ ротирован ✅
- gpt-4o-mini для extractor/analyzer ✅
- RAG — 50 примеров, семантический поиск ✅
- Старая Маргарита на :8001 — работает параллельно (можно гасить) ✅

---

## ❌ Известные проблемы

### Скорость: ~11 сек до первого токена
Три последовательных LLM-вызова. Параллелизация невозможна (analyzer зависит от extractor).
gpt-4o-mini для extractor/analyzer уже применён. Отложено — вернёмся позже.

---

## 🔜 Задачи (приоритет)

### P1 — Воронка и приветствие (СЛЕДУЮЩАЯ СЕССИЯ):

**1. Новое приветствие (greeting)**
Найти: `grep -n greeting /opt/an-eva/main.py`
Должно содержать:
- Представление Марго как помощника-консультанта
- Что может: цены, планировки, расчёт дохода, вопросы по ДДУ и договору с УК
- Минимальная цена от 14.3 млн (фильтр холодных лидов)
- Окупаемость ~6.5 лет

**2. Воронка с МГП-крючком**
МГП = минимальный гарантированный доход (фиксируется в договоре).
Размер и срок МГП сообщает только менеджер.
Стратегия:
- Приветствие → цена фильтрует холодных
- 2 вопроса: бюджет + сроки инвестиции (НЕ 4 вопроса подряд — это допрос)
- Ценность: конкретный лот + примерный расчёт дохода
- МГП как крючок: «В договоре фиксируется минимальный гарантированный доход. Детали подготовит менеджер — оставьте номер)»
- Контакт → [END]

**3. Quick replies под воронку**
Обновить стартовые и после-ответные кнопки

**4. Правила промпта**
- Марго НИКОГДА не даёт телефон отдела продаж (уже сделано)
- Марго упоминает факт МГП но НЕ называет цифры
- Тёплый клиент = тот кто продолжил после цены 14.3 млн и задаёт конкретные вопросы

### P2 — Скорость (отложено):
- ~11 сек до первого токена
- Варианты: gpt-4o-mini для generator, кеширование RAG, оптимизация промптов

### P3 — Расширение:
- Подключение services/ через function calling (investment_calc, installment_calc, deposit_calc)
- Расширение RAG
- Observer (мониторинг в Telegram)
- Замена старой Маргариты (:8001 → гасить)
- Софья (Telegram-бот как второй этап воронки) — отложено, сначала статистика MVP

---

## ⚠️ Принцип изоляции — существующие сервисы НЕ ТРОГАТЬ

| Сервис | Путь | Порт | Статус |
|--------|------|------|--------|
| Sofia-GPT | `/opt/sofia-gpt/` | — | 🔒 НЕ ТРОГАТЬ |
| RIZALTA Bot PROD | `/opt/bot/` | 8000 | 🔒 НЕ ТРОГАТЬ |
| RIZALTA Bot DEV | `/opt/bot-dev/` | 8002 | 🔒 НЕ ТРОГАТЬ |
| WebChat (старая) | `/opt/rizalta-webchat/` | 8001 | 🔒 Можно гасить |
| WebApp PROD | — | 8003 | 🔒 НЕ ТРОГАТЬ |
| WebApp DEV | — | 8004 | 🔒 НЕ ТРОГАТЬ |

---

## Процесс разработки

1. **1Code (MacBook):** пишем код в `~/Projects/an-eva/`
2. **Merge + push:** `cd ~/Projects/an-eva && git merge <branch> && git push`
3. **Сервер:** `cd /opt/an-eva && git pull && systemctl restart an-eva`
4. **На сервере НЕ редактировать** код (кроме .env и hotfix)
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

## Ссылки

- **GitHub:** https://github.com/semiekhin/an-eva
- **Контекст (этот файл):** https://eva-dev.rizaltaservice.ru/api/docs/context
- **Статус:** https://eva-dev.rizaltaservice.ru/api/docs/current
- **Лендинг:** https://rizaltabelokurikha.ru

---

## История сессий

### Сессии 2-4 (17.02.2026):
- Ядро написано: 25 файлов, ~2756 строк
- Полный пайплайн, SSE, лиды в Telegram
- gpt-4o-mini для extractor/analyzer
- API ключ ротирован
- Сценарии прогнаны

### Сессия 5 (19.02.2026):
- Embeddable виджет chat-widget.js подключён к лендингу
- Ребрендинг Маргарита → Марго
- Цены актуализированы (14.3 / 18.8 / 14.5 млн)
- Legend и Wellness убраны
- Витрина 6 лотов из реальной базы
- Телефон убран, только сбор контакта
- Постоянная кнопка «Связаться с отделом продаж»
- Согласована воронка: цена-фильтр → 2 вопроса → ценность → МГП-крючок → контакт
