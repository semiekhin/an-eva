# АН Эва — Лог изменений

## 16.02.2026
- Создан проект АН Эва (проектный документ, репо, инфраструктура)
- Репо: github.com/semiekhin/an-eva (public)
- Скопированы данные на сервер: properties.db, corp3_units.json, units.json, rizalta_knowledge.md, RAG-примеры, калькуляторы
- Создан systemd сервис an-eva (порт 8005)
- Настроен 1Code (Agent, Opus 4.6, Worktree)
- Создана система управления сессиями

## 17.02.2026
- Обновлён AN_EVA_PROJECT.md: изоляция, свой путь /opt/an-eva/, порт 8005
- Создана система управления сессиями (SESSION_END_TEMPLATE.md)
- Решено: источник правды — GitHub, CURRENT.md fetch'ится из GitHub

## 17.02.2026 — Фазы 1-4, первый деплой
- Фаза 0 завершена: refs/sofia/ и refs/margarita/ скопированы
- Фаза 1: config.py, extractor.py, state_manager.py, message_processor.py, analyzer.py (41 тест)
- Фаза 2: rag_module.py, generator.py (25 тестов)
- Фаза 3: rizalta_prompt_v2.py, rizalta_context.py (22 теста)
- Фаза 4: main.py, widget/index.html, widget/chat.js (21 тест)
- Итого: 11 файлов, ~4000 строк, 109 тестов
- Деплой на сервер: merge ветки, установка зависимостей, systemd с UTF-8
- Smoke test пройден: Маргарита отвечает на /api/chat, квалифицирует клиента
- Проблемы: RAG 0 примеров (utf-8), нет внешнего доступа, ключ скомпрометирован

## 17.02.2026 — Сессия 2
- Merge functional-gopher-db8bc3 → main (25 файлов, 3975 строк кода)
- Cloudflare tunnel: eva-dev.rizaltaservice.ru → :8005
- RAG fix: list_collections() → get_or_create_collection (ChromaDB 1.5.0)
- .env создан, systemd сервис запущен и включен
- Полный пайплайн протестирован через curl
- Зафиксирован процесс разработки (1Code → merge → push → pull)
