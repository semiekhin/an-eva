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
