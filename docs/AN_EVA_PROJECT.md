# АН ЭВА — Проектный документ

📅 **Создан:** 16.02.2026
**Обновлён:** 16.02.2026
**Кодовое название:** АН Эва
**Статус:** Проектирование

---

## 1. ЧТО ЭТО

AI-консультант «Маргарита» для продажи инвестиционной недвижимости RIZALTA Resort Belokurikha (Алтай). Веб-виджет на лендинге rizaltabelokurikha.ru. Квалифицирует клиентов → собирает контакт → конвертирует в онлайн-показ.

**Суть проекта:** Взять проверенную архитектуру Sofia-GPT v3.0 (Extractor → LLM-Analyzer → RAG → Generator), подключить данные из Telegram-бота RIZALTA (348 лотов, калькуляторы, PDF), обернуть в персону Маргариты и развернуть на существующем лендинге.

**Почему не доработка, а переписка:** Текущая Маргарита (`/opt/rizalta-webchat/`) имеет критические проблемы — таймауты на 4-5 сообщении, нет стриминга (ожидание 6-15 сек), тяжёлый Extractor (30 полей), захардкоженный planner (29 actions), 14+ SQLite соединений на запрос, RAG всего 50 примеров. Архитектура Софии решает все эти проблемы.

---

## ⚠️ ПРИНЦИП ИЗОЛЯЦИИ

**АН Эва — полностью самостоятельный проект.**

Существующие сервисы на сервере — это продакшн, они работают и приносят пользу. Их нельзя трогать, ломать, останавливать или модифицировать.

| Сервис | Путь | Порт | Статус |
|--------|------|------|--------|
| Sofia-GPT | `/opt/sofia-gpt/` | — | 🔒 НЕ ТРОГАТЬ |
| RIZALTA Telegram Bot PROD | `/opt/bot/` | 8000 | 🔒 НЕ ТРОГАТЬ |
| RIZALTA Telegram Bot DEV | `/opt/bot-dev/` | 8002 | 🔒 НЕ ТРОГАТЬ |
| RIZALTA WebChat (текущая Маргарита) | `/opt/rizalta-webchat/` | 8001 | 🔒 НЕ ТРОГАТЬ (до замены) |
| WebApp PROD | — | 8003 | 🔒 НЕ ТРОГАТЬ |
| WebApp DEV | — | 8004 | 🔒 НЕ ТРОГАТЬ |

**Правила:**
1. Код из Софьи и RIZALTA-бота — **копируем**, не импортируем и не ссылаемся
2. Данные (properties.db, RAG-примеры, knowledge) — **копируем** в свой проект
3. Свой порт: **8005** (dev) → **8001** (prod, только после остановки старой Маргариты)
4. Свой путь: `/opt/an-eva/`
5. Свой systemd сервис: `an-eva`
6. Свой Cloudflare tunnel (или переключение существующего при замене)
7. Разработка в **1Code на MacBook** → деплой на сервер через git

---

## 2. ЦЕЛЕВОЙ РЕЗУЛЬТАТ

Клиент заходит на rizaltabelokurikha.ru → видит виджет → открывает чат → Маргарита:
1. Приветствует, спрашивает цель (инвестиция / для себя / подарок)
2. Квалифицирует: цель → бюджет → способ оплаты (макс 3 вопроса)
3. Даёт ценность: конкретные лоты, расчёт ROI, сравнение с депозитом
4. Отрабатывает возражения экспертно (не соглашаясь, а аргументируя)
5. Предлагает выбор: «материалы или онлайн-показ?»
6. Собирает контакт (@telegram или телефон) → [END] → лид в CRM

**KPI:** время первого ответа <3 сек (стриминг), полный ответ <15 сек, конверсия виджет→контакт — отслеживается.

---

## 3. ЧТО ОТКУДА БЕРЁМ

### Из Sofia-GPT (копируем код и паттерны)

| Компонент | Что копируем | Файл-источник (read-only) |
|-----------|-------------|--------------------------|
| **Extractor** | Лёгкий NLU, ~10 полей, Responses API, effort:medium | `/opt/sofia-gpt/extractor.py` |
| **State Manager** | Состояние клиента, confirmed/mentioned, qualification score | `/opt/sofia-gpt/state_manager.py` |
| **Message Processor** | Единый пайплайн Extractor→State→Signals | `/opt/sofia-gpt/message_processor.py` |
| **LLM-Analyzer** | Определение этапа + rag_query через LLM (вместо planner) | Inline в `bot_server.py` / `web_api.py` |
| **RAG Module** | ChromaDB + text-embedding-3-small, поиск по stage+query | `/opt/sofia-gpt/rag_module.py` |
| **Generator** | gpt-5.2, Responses API, reasoning:high, max_output_tokens:4000 | Inline в `bot_server.py` / `web_api.py` |
| **Техники продаж** | Квалификация, правило двух попыток, работа с возражениями | `/opt/sofia-gpt/sofia_prompt_v2.py` |
| **Веб-стратегия** | Макс 3 вопроса, ценность сразу, сбор контакта, [END] маркер | Inline в `web_api.py` |
| **Bitrix интеграция** | send_lead_to_bitrix(), extract_phone, extract_telegram | `/opt/sofia-gpt/web_api.py` |
| **Session persistence** | web_sessions таблица, localStorage, /api/session/resume | `/opt/sofia-gpt/web_api.py` |

⚠️ Все файлы читаем как референс. Код копируем в `/opt/an-eva/` и адаптируем. Оригиналы не меняем.

### Из RIZALTA Telegram Bot (копируем данные)

| Компонент | Что копируем | Источник (read-only) |
|-----------|-------------|---------------------|
| **База лотов** | 348 лотов (Family 255 + Business 103) | `/opt/bot-dev/properties.db` → копия в `/opt/an-eva/data/` |
| **Корпус 3 Digital** | 128 available / 154 sold (whitelist) | `/opt/bot-dev/corp3_units.json` → копия |
| **Калькулятор ROI** | Расчёт доходности инвестиций | `/opt/bot-dev/services/` → копия в `/opt/an-eva/services/` |
| **Калькулятор рассрочки** | Варианты оплаты | `/opt/bot-dev/services/` → копия |
| **PDF-генератор КП** | Коммерческие предложения | `/opt/bot-dev/handlers/kp.py` → копия |
| **База знаний** | Всё о RIZALTA Resort Belokurikha | `/opt/bot-dev/docs/RIZALTA_KNOWLEDGE.md` → копия |

⚠️ Все данные копируются один раз при старте проекта. Обновления — вручную при необходимости.

### Из текущей Маргариты (копируем виджет)

| Компонент | Что копируем | Источник (read-only) |
|-----------|-------------|---------------------|
| **Виджет** | iframe chat-widget.html + chat-widget.js | `/opt/rizalta-webchat/widget/` → копия |
| **Персона** | Промпт Маргариты | `/opt/rizalta-webchat/rizalta_prompt.py` → копия |
| **RAG примеры** | 50 текущих примеров | `/opt/rizalta-webchat/rag_data/` → копия |

⚠️ Текущая Маргарита продолжает работать на порту 8001 пока АН Эва не будет готова к замене.

---

## 4. ДАННЫЕ ОБ ОБЪЕКТЕ

### RIZALTA Resort Belokurikha
- **Локация:** Белокуриха, Алтайский край
- **Тип:** Курортный комплекс, 5 корпусов, 1300 номеров, 7 Га
- **Корпуса:** Family, Business, Digital, Legend, Wellness
- **Застройщик:** ООО СЗ «Строительная инициатива» (ГК «Жилищная инициатива»)
- **Объём инвестиций:** >20 млрд ₽
- **Архитектура:** PERGAEV bureau, стиль метамодерн
- **Площади:** 20–120 м²
- **Защита:** 214-ФЗ, эскроу-счета
- **Оператор:** ZONT HOTEL GROUP

### Финансовые показатели
- **Доход:** >2 млн ₽/год чистыми (загрузка 70%)
- **Окупаемость:** ~6 лет
- **Капитализация:** +20%/год
- **Рассрочка:** 0% на 12 мес, 6% на 24 мес
- **Ипотека:** от 4.4%

### Актуальные цены
⚠️ **Требуется актуализация.** Взять из `properties.db` при старте проекта. Включить диапазоны по корпусам и типам номеров.

### Финансовая экспертиза (адаптировать из Софии)
- Ключевая ставка ЦБ: 15.5% (февраль 2026), прогноз снижения
- Сравнение: инвестиция в RIZALTA vs депозит на горизонте 5-6 лет
- Аргументы: депозит теряет доходность при снижении ставки, недвижимость — двойной доход (рост + аренда)
- Конкретные цифры: подставить из калькулятора ROI бота

---

## 5. ПЕРСОНА МАРГАРИТА

### Характер
- Премиум-консультант, уверенная, статусная
- Вежливая но не заискивающая
- Эксперт, а не обслуга (принцип из Софии)
- Женский род: «Поняла», «Записала», «Подготовлю»

### Правила общения (из Софии, адаптировать)
1. **Короткие сообщения** — 1-3 предложения, не стена текста
2. **Правило двух попыток** — не переспрашивать одно и то же >2 раз
3. **Макс 3 вопроса** за весь диалог (цель / бюджет / оплата)
4. **Ценность сразу** — конкретные цифры, лоты, расчёты, не «расскажу на созвоне»
5. **Работа с возражениями** — формула: прими эмоцию → контраргумент → покажи выгоду → оставь выбор
6. «)» вместо эмодзи (или адаптировать под стиль Маргариты)

### Сбор контакта
- Предлагать ВЫБОР: «Могу отправить презентацию или организовать онлайн-показ — как удобнее?»
- Материалы → @username в Telegram
- Онлайн-показ → номер телефона
- Получила контакт → немедленно [END]
- НЕ спрашивать «WhatsApp или Telegram?» — только Telegram и телефон

### Возражения по RIZALTA (специфичные)
- «Белокуриха — это далеко» → доступность, аэропорт, трансфер, аргументы про туристический поток
- «Алтай — это не море» → круглогодичный курорт, зима+лето, термальные источники
- «Дорого» → расчёт ROI, окупаемость 6 лет, сравнение с депозитом
- «Стройка, ждать» → 214-ФЗ, эскроу, рост на стройке +20%/год
- «Кто будет управлять?» → ZONT HOTEL GROUP, всё берут на себя

---

## 6. АРХИТЕКТУРА

### Целевой пайплайн

```
Клиент на rizaltabelokurikha.ru → виджет Маргариты
        ↓
[ТРАНСПОРТ] FastAPI (порт 8005 dev / 8001 prod)
        ↓
[1. EXTRACTOR] — gpt-5.2, Responses API, effort: medium
    Вход: сообщение + 6 последних сообщений
    Выход: JSON ~10 полей (goal, budget, payment_type, objection, sentiment, signals)
    Референс: /opt/sofia-gpt/extractor.py
        ↓
[2. STATE MANAGER] — SQLite (aiosqlite, connection pool)
    Обновляет состояние клиента
    confirmed перезаписывает mentioned, не наоборот
    Формирует state_summary
    Референс: /opt/sofia-gpt/state_manager.py
        ↓
[3. LLM-ANALYZER] — gpt-5.2, Responses API, effort: medium
    Вход: история (20 последних) + state + сообщение
    Выход: stage + rag_query (JSON)
    Этапы: GREETING / QUALIFICATION / PRESENTATION / MEETING / OBJECTION / CLOSING
    Референс: analyzer_prompt в /opt/sofia-gpt/web_api.py
        ↓
[4. RAG] — ChromaDB + text-embedding-3-small
    Вход: stage + rag_query
    Выход: 7-10 примеров из успешных продаж RIZALTA
    Начальная база: 50 примеров (текущие) → расширять до 500+
    Референс: /opt/sofia-gpt/rag_module.py
        ↓
[5. GENERATOR] — gpt-5.2, Responses API, reasoning: high
    Вход: system_prompt (Маргарита) + state_summary + RIZALTA-контекст + RAG + история + сообщение
    Выход: ответ клиенту (СТРИМИНГ через EventSource) + возможный [END]
    max_output_tokens: 4000
        ↓
[6. POST-PROCESSING]
    Проверка [END] → если есть:
      - Убирает маркер из текста
      - Отправляет лид в CRM (Bitrix или другая)
      - Ставит dialog_finished = 1
        ↓
Ответ клиенту (посимвольный стриминг)
```

### Структура промпта (два уровня, как у Софии)

**Базовый промпт (rizalta_prompt_v2.py):**
- Персона Маргариты
- Техники продаж и квалификации (из sofia_prompt_v2.py)
- Правила общения
- Работа с возражениями (специфичные для RIZALTA)
- Финансовая экспертиза (ставка ЦБ, сравнение с депозитом)
- Особые случаи завершения

**Объектный контекст (rizalta_context.py):**
- Данные RIZALTA Resort: корпуса, цены, площади
- Калькулятор ROI (формулы или готовые расчёты)
- Условия рассрочки и ипотеки
- Стратегия веб-чата
- Сбор контакта

---

## 7. СТРИМИНГ

### Почему критично
Текущая Маргарита: клиент ждёт 6-15 секунд полного ответа → на 4-5 сообщении таймаут → чат ломается. Стриминг решает: первые слова через 1-2 сек, клиент видит что бот «печатает».

### Реализация
- **Бэкенд:** `POST /api/chat/stream` → `StreamingResponse` (FastAPI) → SSE (Server-Sent Events)
- **Фронтенд:** виджет подключается через `EventSource` или `fetch` + `ReadableStream`
- **Формат:** `data: {"token": "слово"}\n\n` → при завершении `data: {"done": true}\n\n`
- **Responses API:** OpenAI поддерживает streaming нативно

### Референс
В Sofia-GPT bot_server.py стриминг реализован для Telegram (`send_chat_action` + посимвольная отправка). Для веб нужен SSE — это проще.

---

## 8. ИНФРАСТРУКТУРА

### Сервер
- **IP:** 72.56.64.91, SSH порт 2222
- **OS:** Ubuntu, Python 3.12
- **Проект АН Эва:** `/opt/an-eva/` (НОВЫЙ путь, изолирован)

### Карта портов (все сервисы)
| Порт | Сервис | Статус |
|------|--------|--------|
| 8000 | RIZALTA Telegram Bot PROD | 🔒 Занят |
| 8001 | RIZALTA WebChat (текущая Маргарита) | 🔒 Занят → освободится при замене |
| 8002 | RIZALTA Telegram Bot DEV | 🔒 Занят |
| 8003 | WebApp PROD | 🔒 Занят |
| 8004 | WebApp DEV | 🔒 Занят |
| **8005** | **АН Эва DEV** | ✅ Свободен |
| **8001** | **АН Эва PROD** (после замены) | После остановки старой Маргариты |

### Домены
| Домен | Что | Маршрут |
|-------|-----|---------|
| `rizaltabelokurikha.ru` | Лендинг с виджетом | REG.ru ISPmanager |
| `webchat.rizaltaservice.ru` | Сейчас → :8001 (старая). После замены → :8001 (АН Эва) |
| `eva-dev.rizaltaservice.ru` | DEV API АН Эвы (новый tunnel → :8005) |

### Внешние сервисы
| Сервис | Назначение |
|--------|------------|
| OpenAI gpt-5.2 | LLM (Responses API) |
| ChromaDB | RAG (локально, своя копия в `/opt/an-eva/data/chroma_db/`) |
| Bitrix24 / другая CRM | Лиды (⚠️ уточнить какая CRM у RIZALTA) |

---

## 9. БАЗА ДАННЫХ

### Путь: `/opt/an-eva/db/an_eva.db` (своя БД, не трогает чужие)

### Таблицы (по образцу Софии + специфика RIZALTA)

**client_state** — состояние клиента:
- goal, goal_confidence (investment / personal)
- budget, budget_confidence
- payment_type, payment_type_confidence (full / mortgage / installment)
- preferred_corpus (family / business / digital)
- preferred_area_range (20-40 / 40-60 / 60-120)
- meeting_agreed, dialog_finished, finish_type
- friction, call_readiness, engagement, urgency
- materials_request_count, call_proposal_count

**messages** — история сообщений:
- session_id, user_id, role, content, timestamp

**web_sessions** — маппинг сессий:
- session_id (UUID), user_id (auto-increment), created_at, last_active, page_url

**observer_topics** — мониторинг (если подключим Observer)

### SQLite улучшения
- **Connection pool** через aiosqlite (вместо 14+ соединений на запрос)
- **WAL mode** для конкурентного доступа
- **Единое подключение** — один объект connection на приложение

---

## 10. ЭНДПОИНТЫ API

| Метод | URL | Назначение |
|-------|-----|------------|
| GET | `/api/health` | Health check |
| POST | `/api/session` | Создать сессию (+ page_url, UTM) |
| POST | `/api/session/resume` | Восстановить сессию из localStorage |
| POST | `/api/chat` | Отправить сообщение (обычный ответ) |
| POST | `/api/chat/stream` | Отправить сообщение (стриминг SSE) |
| GET | `/api/history/{session_id}` | История переписки |

### CORS
```
https://rizaltabelokurikha.ru
http://rizaltabelokurikha.ru
https://www.rizaltabelokurikha.ru
http://www.rizaltabelokurikha.ru
http://localhost:3000
http://127.0.0.1:5500
```

---

## 11. СТРУКТУРА ФАЙЛОВ

```
/opt/an-eva/
├── main.py                    # FastAPI app, эндпоинты, lifespan
├── extractor.py               # NLU ~10 полей (скопировано из Софии, адаптировано)
├── state_manager.py           # SQLite + aiosqlite pool (скопировано из Софии, адаптировано)
├── message_processor.py       # Extractor → State → Signals (скопировано из Софии, адаптировано)
├── rag_module.py              # ChromaDB (скопировано из Софии, адаптировано)
├── generator.py               # LLM-Generator + стриминг
├── analyzer.py                # LLM-Analyzer (скопировано из Софии, адаптировано)
├── rizalta_prompt_v2.py       # Промпт Маргариты (техники из Софии + персона)
├── rizalta_context.py         # Объектный контекст RIZALTA (цены, лоты, расчёты)
├── bitrix_client.py           # CRM интеграция (скопировано из Софии, адаптировано)
├── observer.py                # Трансляция в Telegram-группу мониторинга
├── config.py                  # Настройки, пути, ключи
├── .env                       # Секреты (свой файл, не ссылка)
├── requirements.txt           # Зависимости
│
├── data/
│   ├── properties.db          # КОПИЯ базы лотов из /opt/bot-dev/
│   ├── corp3_units.json       # КОПИЯ данных корпуса Digital
│   ├── rizalta_knowledge.json # КОПИЯ базы знаний
│   ├── rag_training_data.json # RAG примеры (50 из старой Маргариты + новые)
│   └── chroma_db/             # Своя векторная БД ChromaDB
│
├── services/
│   ├── roi_calculator.py      # КОПИЯ калькулятора ROI из /opt/bot-dev/services/
│   ├── installment_calc.py    # КОПИЯ калькулятора рассрочки
│   └── pdf_generator.py       # КОПИЯ генератора КП (адаптировать)
│
├── widget/
│   ├── chat-widget.html       # Виджет (обновлённый: EventSource стриминг)
│   ├── chat-widget.js         # Загрузчик виджета (обновлённый: порт 8005 dev)
│   └── styles.css             # Стили
│
├── db/
│   └── an_eva.db              # Своя SQLite БД — сессии, состояния, сообщения
│
└── docs/
    ├── AN_EVA_PROJECT.md      # Этот документ
    └── CHANGELOG.md           # Лог изменений
```

---

## 12. РАЗРАБОТКА

### Среда разработки
- **IDE:** 1Code на MacBook Pro M1 Max
- **Репозиторий:** github.com/semiekhin/an-eva (создать новый, public)
- **Ветка:** main + worktrees через 1Code
- **Модель в 1Code:** Claude Opus 4.6, Agent mode, Worktree ON

### Workflow
```
1. Разработка в 1Code (MacBook)
   └── Код пишется локально в ~/Projects/an-eva/
   
2. Push в GitHub
   └── git push origin main

3. Pull на сервер
   └── ssh root@72.56.64.91 -p 2222
   └── cd /opt/an-eva && git pull

4. Перезапуск сервиса
   └── systemctl restart an-eva
```

### Первоначальная настройка на сервере
```bash
# Создать директорию проекта
mkdir -p /opt/an-eva

# Клонировать репо
cd /opt && git clone git@github.com:semiekhin/an-eva.git

# Скопировать данные из существующих проектов (однократно)
mkdir -p /opt/an-eva/data
cp /opt/bot-dev/properties.db /opt/an-eva/data/
cp /opt/bot-dev/corp3_units.json /opt/an-eva/data/
cp /opt/bot-dev/docs/RIZALTA_KNOWLEDGE.md /opt/an-eva/data/rizalta_knowledge.md
cp -r /opt/rizalta-webchat/rag_data/ /opt/an-eva/data/rag_training_data/

# Скопировать калькуляторы
mkdir -p /opt/an-eva/services
cp /opt/bot-dev/services/roi_calculator.py /opt/an-eva/services/  # если существует
cp /opt/bot-dev/services/installment_calc.py /opt/an-eva/services/  # если существует

# Создать .env
cp /opt/an-eva/.env.example /opt/an-eva/.env
# Заполнить OPENAI_API_KEY и другие секреты

# Установить зависимости
cd /opt/an-eva && pip install -r requirements.txt

# Создать systemd сервис
cat > /etc/systemd/system/an-eva.service << 'EOF'
[Unit]
Description=AN Eva - Margarita AI
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/an-eva
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable an-eva
systemctl start an-eva
```

### Настройка 1Code на MacBook
```bash
# Создать локальный репо
mkdir -p ~/Projects/an-eva
cd ~/Projects/an-eva
git init && git branch -M main

# Или клонировать после создания на GitHub
git clone git@github.com:semiekhin/an-eva.git ~/Projects/an-eva

# Запустить 1Code
cd ~/1code && bun run dev

# В 1Code: Select folder → ~/Projects/an-eva
# Agent mode, Opus 4.6, Worktree ON
```

---

## 13. ПЛАН РЕАЛИЗАЦИИ

### Фаза 0: Подготовка (перед кодом)
- [ ] Создать репо `github.com/semiekhin/an-eva` (public)
- [ ] Настроить 1Code: подключить папку `~/Projects/an-eva`
- [ ] На сервере: `mkdir -p /opt/an-eva` + клонировать репо
- [ ] Скопировать данные из существующих проектов (команды выше)
- [ ] Изучить (read-only!) код Софии: `extractor.py`, `state_manager.py`, `message_processor.py`, `rag_module.py`, `web_api.py`
- [ ] Изучить (read-only!) данные бота: `properties.db`, калькуляторы, `rizalta_knowledge.json`
- [ ] Изучить (read-only!) промпт текущей Маргариты: `rizalta_prompt.py`
- [ ] Изучить (read-only!) текущие RAG-примеры (50 шт)
- [ ] Определить CRM (Bitrix24 как у Софии или другая?)
- [ ] Собрать актуальные цены по всем корпусам

### Фаза 1: Ядро (Extractor + State + Analyzer)
- [ ] Написать `config.py` — порт 8005, пути к data/, db/
- [ ] Написать `extractor.py` по образцу Софии (~10 полей, Responses API)
- [ ] Написать `state_manager.py` по образцу Софии (aiosqlite, connection pool, WAL)
- [ ] Написать `message_processor.py` по образцу Софии (Extractor → State → Signals)
- [ ] Написать `analyzer.py` — LLM-Analyzer (этапы: GREETING/QUALIFICATION/PRESENTATION/MEETING/OBJECTION/CLOSING)
- [ ] Создать таблицы БД в `/opt/an-eva/db/an_eva.db`
- [ ] **Тест:** сообщение → extractor → state обновился → analyzer вернул stage + rag_query

### Фаза 2: RAG + Generator
- [ ] Написать `rag_module.py` по образцу Софии, пути к `/opt/an-eva/data/chroma_db/`
- [ ] Подготовить RAG-датасет: 50 текущих примеров + адаптировать часть из Софии (убрать Oazis, написать про RIZALTA)
- [ ] Написать `generator.py` — Responses API, reasoning:high, стриминг
- [ ] **Тест:** полный пайплайн message → extractor → state → analyzer → rag → generator → ответ

### Фаза 3: Промпт Маргариты
- [ ] Написать `rizalta_prompt_v2.py`:
  - Персона Маргариты (из текущего промпта)
  - Техники продаж (из sofia_prompt_v2.py)
  - Квалификация: цель → бюджет → оплата (макс 3 вопроса)
  - Правило двух попыток
  - Работа с возражениями (специфика RIZALTA + Алтай)
  - Финансовая экспертиза (ставка ЦБ, сравнение с депозитом, ROI)
  - Особые случаи завершения
- [ ] Написать `rizalta_context.py`:
  - Цены и планировки по корпусам
  - Условия рассрочки и ипотеки
  - Стратегия веб-чата
  - Правила сбора контакта
- [ ] **Тест:** диалог от начала до [END], проверить качество ответов

### Фаза 4: Веб-слой (API + виджет)
- [ ] Написать `main.py`:
  - FastAPI app с lifespan
  - Эндпоинты: /api/session, /api/session/resume, /api/chat, /api/chat/stream, /api/health
  - CORS для rizaltabelokurikha.ru + localhost
  - Session persistence (web_sessions, localStorage)
  - Приветствие по page_url
  - Порт 8005 (dev)
- [ ] Обновить виджет `chat-widget.html`:
  - EventSource для стриминга
  - localStorage session_id
  - Resume при открытии
  - Quick replies
  - Typing indicator (реальный, от стриминга)
  - API URL → `eva-dev.rizaltaservice.ru` (dev) / `webchat.rizaltaservice.ru` (prod)
- [ ] **Тест:** открыть виджет → создать сессию → написать → увидеть стриминг ответа → закрыть → открыть → resume

### Фаза 5: Данные RIZALTA
- [ ] Подключить `properties.db` (348 лотов) из `/opt/an-eva/data/`
- [ ] Адаптировать калькулятор ROI (`services/roi_calculator.py`)
- [ ] Адаптировать калькулятор рассрочки (`services/installment_calc.py`)
- [ ] Опционально: PDF-генератор КП
- [ ] **Тест:** клиент спрашивает «какие есть студии до 10 млн?» → Маргарита отвечает конкретными лотами

### Фаза 6: CRM + мониторинг
- [ ] Реализовать `bitrix_client.py` (или другую CRM):
  - send_lead(): extract_phone + extract_telegram из истории
  - Поля: имя, телефон, telegram, цель, бюджет, оплата, переписка
  - Вызов при [END]
- [ ] Реализовать `observer.py`:
  - Трансляция диалогов в Telegram-группу
  - Каждый клиент — отдельная тема
- [ ] **Тест:** довести диалог до [END] → проверить лид в CRM + сообщение в Observer

### Фаза 7: Деплой и замена
- [ ] Убедиться что АН Эва стабильно работает на порту 8005
- [ ] Провести smoke test: полный диалог с реального телефона через `eva-dev.rizaltaservice.ru`
- [ ] **Замена (одна операция):**
  ```bash
  # 1. Остановить старую Маргариту
  systemctl stop rizalta-webchat
  systemctl disable rizalta-webchat
  
  # 2. Переключить порт АН Эвы: 8005 → 8001
  # Изменить PORT в /opt/an-eva/.env
  
  # 3. Перезапустить АН Эву
  systemctl restart an-eva
  
  # 4. Проверить tunnel: webchat.rizaltaservice.ru → :8001
  curl -s https://webchat.rizaltaservice.ru/api/health
  
  # 5. Обновить виджет: API URL → webchat.rizaltaservice.ru
  
  # 6. Проверить на лендинге: rizaltabelokurikha.ru
  ```
- [ ] Мониторинг первые 24 часа через Observer

### Фаза 8: Оптимизация (после запуска)
- [ ] Расширение RAG до 500+ примеров (собирать из реальных диалогов)
- [ ] Тюнинг промпта по результатам реальных разговоров
- [ ] Таймаут: авто-лид в CRM если клиент ушёл
- [ ] Deep links в Telegram-бот: кнопка «Подробнее в Telegram» → @RealtMeAI_bot
- [ ] A/B тестирование приветствий и стратегий квалификации
- [ ] PDF-генерация КП прямо в чате (если нужно)

---

## 14. УРОКИ ИЗ СОФИИ (НЕ ПОВТОРЯТЬ ОШИБКИ)

1. **Объектный контекст — в отдельном файле** (`rizalta_context.py`), не inline в main.py.
2. **CRM интеграция — сразу.** Лиды не должны теряться.
3. **History limit — единый.** Задать один лимит (100) в конфиге.
4. **Стриминг — с первого дня.** Это решает проблему таймаутов.
5. **Greeting — в историю.** Сохранять greeting в messages при создании сессии.
6. **[END] при контакте — немедленно.** Получила контакт → ответь на вопрос → [END] в том же сообщении.
7. **State не должен быть пустым.** Extractor должен быть надёжнее.
8. **Один пайплайн.** Всё в одном main.py → при добавлении Telegram-канала вынести в message_processor.
9. **Бэкапы перед каждым изменением.** `cp file.py file.py.bak_$(date +%Y%m%d_%H%M%S)`.
10. **Мёртвые импорты — не оставлять.**

---

## 15. ОТКРЫТЫЕ ВОПРОСЫ

| # | Вопрос | Кто решает |
|---|--------|-----------|
| 1 | Какая CRM у RIZALTA? Bitrix24 или другая? | Sergio |
| 2 | Актуальные цены по корпусам — откуда брать? properties.db актуален? | Sergio |
| 3 | Observer — нужна отдельная Telegram-группа для Маргариты? | Sergio |
| 4 | Deep links в @RealtMeAI_bot — реализовывать сразу или после запуска? | Sergio |
| 5 | Корпус 3 (Digital, whitelist) — показывать в веб-чате или только в боте? | Sergio |
| 6 | PDF КП — нужно ли в веб-чате или только через бот? | Sergio |
| 7 | Текущие 50 RAG-примеров Маргариты — подходят по качеству или переписывать? | Изучить при старте |
| 8 | Промпт Маргариты — сохранять её характер или сделать ближе к Софии? | Sergio |

---

## 16. ФАЙЛЫ-РЕФЕРЕНСЫ (ЧТО ЧИТАТЬ, НЕ МЕНЯТЬ)

### Архитектура Софии (read-only, копировать паттерны)
```
/opt/sofia-gpt/extractor.py          # Extractor ~10 полей
/opt/sofia-gpt/state_manager.py      # State Manager
/opt/sofia-gpt/message_processor.py  # Единый процессор
/opt/sofia-gpt/rag_module.py         # RAG ChromaDB
/opt/sofia-gpt/sofia_prompt_v2.py    # Промпт (техники продаж)
/opt/sofia-gpt/web_api.py            # Web API + Bitrix + sessions
/opt/sofia-gpt/bot_server.py         # Telegram бот (LLM-Analyzer inline)
```

### Данные RIZALTA (read-only, копировать данные)
```
/opt/bot-dev/properties.db                # База лотов
/opt/bot-dev/corp3_units.json             # Корпус Digital
/opt/bot-dev/docs/RIZALTA_KNOWLEDGE.md    # База знаний
/opt/bot-dev/services/                    # Калькуляторы
/opt/bot-dev/handlers/kp.py              # PDF-генератор
```

### Текущая Маргарита (read-only, изучить перед заменой)
```
/opt/rizalta-webchat/main.py           # Текущий пайплайн
/opt/rizalta-webchat/extractor.py      # Тяжёлый extractor (30 полей)
/opt/rizalta-webchat/planner.py        # Детерминистический (29 actions)
/opt/rizalta-webchat/generator.py      # Без стриминга
/opt/rizalta-webchat/rizalta_prompt.py # Промпт Маргариты
/opt/rizalta-webchat/state_manager.py  # 14+ коннектов
/opt/rizalta-webchat/rag_module.py     # 50 примеров
/opt/rizalta-webchat/widget/           # Виджет
```

### Документация Софии
```
/opt/sofia-gpt/docs/SOFIA_PROJECT_MAP.md  # Карта проекта
```

---

## 17. ОРКЕСТРАЦИЯ РАЗРАБОТКИ

**Основной чат:** Claude.ai (этот проект) — формирование ТЗ и координация.
**Исполнитель:** 1Code (Claude Code) на MacBook — написание кода.
**Деплой:** git push → git pull на сервере → systemctl restart an-eva

**Порядок работы:**
1. Оркестратор (Claude.ai) формирует ТЗ на конкретную фазу/задачу
2. ТЗ передаётся в 1Code с контекстом (этот документ + нужные файлы)
3. 1Code выполняет, коммитит в git, отчитывается
4. Push на GitHub → Pull на сервер → тест
5. Оркестратор проверяет, даёт следующую задачу

**Правила для 1Code / Claude Code:**
- Код пишется ЛОКАЛЬНО в `~/Projects/an-eva/`
- На сервере — только `git pull` и `systemctl restart`
- Бэкап перед каждым изменением на сервере
- Один файл за раз, не менять несколько сразу
- После каждого файла — тест
- git commit после каждой значимой группы
- ⚠️ НИКАКИЕ файлы в `/opt/sofia-gpt/`, `/opt/bot/`, `/opt/bot-dev/`, `/opt/rizalta-webchat/` НЕ МЕНЯТЬ

---

## 18. БЫСТРЫЕ КОМАНДЫ

```bash
# === АН Эва ===
systemctl status an-eva
systemctl restart an-eva
journalctl -u an-eva -f

# Бэкап
cp -r /opt/an-eva /opt/an-eva.bak_$(date +%Y%m%d_%H%M%S)

# БД
sqlite3 /opt/an-eva/db/an_eva.db "SELECT * FROM web_sessions ORDER BY created_at DESC LIMIT 5;"

# Тест API (dev)
curl -s https://eva-dev.rizaltaservice.ru/api/health
# или напрямую
curl -s http://localhost:8005/api/health

# Git (на сервере — только pull)
cd /opt/an-eva && git pull

# Git (на MacBook — разработка)
cd ~/Projects/an-eva && git add -A && git commit -m "описание" && git push

# === Существующие сервисы (НЕ ТРОГАТЬ, только мониторинг) ===
systemctl status rizalta-webchat    # текущая Маргарита
systemctl status webapp-prod        # бот PROD
```
