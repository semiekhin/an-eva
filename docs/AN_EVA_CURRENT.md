# Текущий статус АН Эва

📅 **Последняя сессия:** 18.02.2026, 12:30 MSK
**Фаза:** MVP работает, готовимся к подключению на лендинг

## ✅ Что сделано 17-18.02.2026 (сессии 2-4)

### Сессия 2 (1Code):
- Написано ядро: 25 файлов, 2756 строк
- Полный пайплайн: extractor → state → analyzer → RAG → generator
- systemd сервис запущен на :8005
- RAG починен (ChromaDB 1.5.0)

### Сессия 3 (Claude.ai):
- SSE-эндпоинт `/api/chat/stream` с потоковой отдачей токенов
- `lead_notifier.py` — лиды в Telegram через @RIZALTAEVA_bot
- Фильтрация [END] в потоке (буферизация токенов)
- Обнаружена проблема: Cloudflare буферизует SSE

### Сессия 4 (Claude.ai):
- **Решена проблема Cloudflare:** nginx + Let's Encrypt вместо CF tunnel
  - A-запись eva-dev → 72.56.64.91 (DNS only, без proxy)
  - nginx reverse proxy с `proxy_buffering off`
  - SSL certbot автообновление
- Убран padding (8KB крестиков — костыль для CF)
- Полный цикл проверен в браузере: greeting → квалификация → контакт → лид ✅
- Extractor/Analyzer переключены на gpt-4o-mini (убран reasoning.effort для совместимости)
- Создан AN_EVA_CONTEXT.md — полная документация проекта
- Эндпоинт `/api/docs/context` — отдаёт контекст без кеша для новых чатов
- API ключ ротирован ✅
- Сценарии прогнаны в браузере ✅

## 🔄 Текущее состояние
### Работает:
- АН Эва на :8005 через systemd ✅
- eva-dev.rizaltaservice.ru — nginx + SSL (без Cloudflare) ✅
- SSE стриминг в браузере ✅
- Полный пайплайн: extractor (gpt-4o-mini) → state → analyzer (gpt-4o-mini) → RAG → generator (gpt-5.2) ✅
- Лиды → Telegram при [END] ✅
- /api/docs/context — актуальный контекст для новых чатов ✅
- GitHub синхронизирован ✅
- Старая Маргарита на :8001 — работает параллельно ✅

### Не сделано:
- Подключение виджета к лендингу rizaltabelokurikha.ru (P3 — следующий шаг)
- Оптимизация скорости (~11 сек до первого токена) — отложена
- Observer (мониторинг в Telegram)

## 🔜 Следующие задачи (приоритет)
1. **P3 (следующая сессия):** Подключить виджет к лендингу rizaltabelokurikha.ru
   - Лендинг на reg.ru (IP: 31.31.196.78, другой сервер)
   - Нужно посмотреть HTML лендинга — как подключена старая Маргарита
   - Заменить ссылку/iframe на АН Эву
2. **P1 (отложена):** Оптимизация скорости — объединить extractor+analyzer в один вызов, или оптимизировать промпт
3. **P4:** Observer, deep links, расширение RAG, замена старой Маргариты

## ⚠️ Важный контекст
- Порт: 8005 (dev), 8001 только после замены старой Маргариты
- Путь: /opt/an-eva/
- Все существующие сервисы НЕ ТРОГАТЬ
- Процесс: 1Code → merge+push → pull+restart на сервере
- Лиды отправлять Sergio лично в Telegram, НЕ в Bitrix CRM
- nginx конфиг: /etc/nginx/sites-enabled/eva-dev
- Контекст для нового чата: https://eva-dev.rizaltaservice.ru/api/docs/context
