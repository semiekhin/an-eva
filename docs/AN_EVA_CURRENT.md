# Текущий статус АН Эва

📅 **Последняя сессия:** 17.02.2026, 21:30 MSK
**Фаза:** MVP работает

## ✅ Что сделано 17.02.2026

### Сессия 2 (1Code):
- Написано ядро: 25 файлов, 2756 строк
- Полный пайплайн: extractor → state → analyzer → RAG → generator
- systemd сервис запущен на :8005
- Cloudflare tunnel eva-dev настроен
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
- Убран padding (8KB крестиков — был костылём для CF)
- **Полный цикл проверен в браузере:** greeting → квалификация → контакт → лид в Telegram

## 🔄 Текущее состояние
### Работает:
- АН Эва на :8005 через systemd ✅
- eva-dev.rizaltaservice.ru — nginx + SSL ✅
- SSE стриминг в браузере ✅
- Полный пайплайн: extractor → state → analyzer → RAG → generator ✅
- Лиды → Telegram при [END] ✅
- GitHub синхронизирован ✅
- Старая Маргарита на :8001 — работает параллельно ✅

### Не сделано:
- Параллельные вызовы extractor + analyzer (7-10 сек до первого токена)
- Быстрая модель для extractor/analyzer (gpt-4o-mini)
- Ротация OpenAI API ключа
- Подключение виджета к лендингу rizaltabelokurikha.ru
- Observer (мониторинг в Telegram)

## 🔜 Следующие задачи (приоритет)
1. **P1:** asyncio.gather(extractor, analyzer) + gpt-4o-mini → цель < 5 сек
2. **P2:** Прогнать сценарии, ротировать API ключ
3. **P3:** Подключить виджет к лендингу, мобильное тестирование
4. **P4:** Observer, deep links, расширение RAG

## ⚠️ Важный контекст
- Порт: 8005 (dev), 8001 только после замены старой Маргариты
- Путь: /opt/an-eva/
- Все существующие сервисы НЕ ТРОГАТЬ
- Процесс: 1Code → merge+push → pull+restart на сервере
- Лиды отправлять Sergio лично в Telegram, НЕ в Bitrix CRM
- nginx конфиг: /etc/nginx/sites-enabled/eva-dev
