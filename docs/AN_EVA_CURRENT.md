# Текущий статус АН Эва

📅 **Последняя сессия:** 17.02.2026, 12:20 MSK
**Фаза:** 4 — Веб-слой (завершена). Готовность к продакшну ~90%.

## ✅ Что сделано в этой сессии (17.02.2026)

### Код (Фазы 1-4 полностью)
- **Фаза 0:** Скопированы refs/sofia/ и refs/margarita/ на сервер, push в GitHub
- **Фаза 1 (Ядро):** config.py, extractor.py, state_manager.py, message_processor.py, analyzer.py — 41 тест
- **Фаза 2 (RAG + Generator):** rag_module.py, generator.py — 25 тестов
- **Фаза 3 (Промпт):** rizalta_prompt_v2.py, rizalta_context.py — 22 теста
- **Фаза 4 (Веб-слой):** main.py, widget/index.html, widget/chat.js — 21 тест
- **Итого:** 11 файлов, ~4000 строк, 109 тестов

### Деплой на сервер
- Код задеплоен в /opt/an-eva/ (merge из ветки functional-gopher-db8bc3)
- Зависимости установлены (pip --break-system-packages)
- systemd сервис an-eva обновлён (добавлен UTF-8: LC_ALL, LANG, PYTHONIOENCODING)
- .env создан с реальным OpenAI ключом
- **Сервер работает на порту 8005, отвечает на /api/health и /api/chat**
- **Smoke test пройден:** Маргарита отвечает конкретно, с цифрами, квалифицирует

### Подтверждённый ответ Маргариты (live test)
> Клиент: "Хочу инвестировать 7 миллионов"
> Маргарита: "На 7 млн обычно подбираем компактные апартаменты 20–40 м² в корпусах Digital или Family (цены от 5 млн); по модели с УК прогнозируемо более 2 млн руб/год при загрузке 70% плюс рост стоимости на стройке около 20% в год. Вам удобнее 100% оплата, рассрочка или ипотека?"

## 🔄 Текущее состояние

### Работает:
- FastAPI на порту 8005 ✅
- systemd сервис an-eva (active/running) ✅
- Endpoints: /api/health, /api/session, /api/session/resume, /api/chat, /api/history ✅
- Extractor + StateManager + Analyzer + Generator — полный пайплайн ✅
- Маргарита отвечает конкретно, квалифицирует, даёт цифры ✅

### Не работает / проблемы:
- **RAG: 0 примеров загружено** — ошибка кодировки при загрузке examples.json (ascii vs utf-8)
- **Нет внешнего доступа** — порт 8005 не открыт снаружи, нужен Cloudflare tunnel или настройка
- **OpenAI ключ скомпрометирован** — был показан в чате, НУЖНО ПЕРЕВЫПУСТИТЬ
- **1Code worktree-ветка** — код в ветке functional-gopher-db8bc3, нужен merge в main
- **Виджет не протестирован в браузере** — только curl-тесты

## 🔜 Следующий шаг
1. **⚠️ СРОЧНО: Перевыпустить OpenAI API ключ** → platform.openai.com → revoke → create new → обновить .env → restart an-eva
2. **Настроить внешний доступ** — Cloudflare tunnel на :8005 (eva-dev.rizaltaservice.ru) или переключить существующий. Вопрос к Sergio: как webchat.rizaltaservice.ru работает сейчас? Через Cloudflare tunnel?
3. **Починить RAG** — ошибка utf-8 при загрузке примеров
4. **Merge в main** — объединить ветку functional-gopher-db8bc3 в main
5. **Тест виджета в браузере** — открыть widget/index.html через внешний URL

## 📁 Структура кода
```
/opt/an-eva/
├── main.py                    ✅ FastAPI, 5 endpoints, SSE
├── config.py                  ✅ Порт, пути, модели, CORS
├── extractor.py               ✅ NLU ~10 полей, async
├── state_manager.py           ✅ aiosqlite, WAL, 3 таблицы
├── message_processor.py       ✅ Extractor → State → Signals
├── analyzer.py                ✅ LLM stage + rag_query
├── rag_module.py              ✅ ChromaDB (0 примеров — баг utf-8)
├── generator.py               ✅ Responses API, стриминг, [END]
├── rizalta_prompt_v2.py       ✅ Персона + техники + веб-стратегия
├── rizalta_context.py         ✅ 5 корпусов, цены, ROI
├── widget/
│   ├── index.html             ✅ Чат UI, RIZALTA design
│   └── chat.js                ✅ SSE, localStorage, resume
├── tests/                     ✅ 109 тестов
├── data/                      ✅ properties.db, RAG, knowledge
├── services/                  ✅ Калькуляторы
├── refs/                      ✅ Sofia + Margarita референсы
├── db/                        ✅ an_eva.db (создаётся автоматически)
├── docs/                      ✅ Проектная документация
└── .env                       ✅ API ключ (⚠️ перевыпустить!)
```

## ⚠️ Важный контекст для следующего чата
- **СРОЧНО:** Перевыпустить OpenAI ключ (скомпрометирован)
- Порт: 8005 (dev). Переход на 8001 (prod) — только после остановки старой Маргариты
- Код в ветке functional-gopher-db8bc3, нужен merge в main
- Все существующие сервисы НЕ ТРОГАТЬ
- Вопрос: как организован внешний доступ (Cloudflare tunnel? nginx?) для webchat.rizaltaservice.ru
- RAG не грузится из-за utf-8 ошибки — починить
- Фазы 5-6 (данные RIZALTA + CRM/Observer) — после стабилизации внешнего доступа
