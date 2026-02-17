# АН Эва — База знаний

## 16.02.2026: corp3_units.json находится в /opt/bot-dev/data/, не в корне
**Проблема:** `cp /opt/bot-dev/corp3_units.json` → файл не найден
**Решение:** Правильный путь `/opt/bot-dev/data/corp3_units.json`
**Почему:** Данные бота лежат в подпапке `data/`, не в корне проекта

## 16.02.2026: Калькуляторы бота — 4 файла
**Что скопировано:** investment_calc.py, installment_calculator.py, deposit_calculator.py, calculations.py
**Откуда:** /opt/bot-dev/services/
**Куда:** /opt/an-eva/services/
**Почему:** В services/ бота ~30 файлов, но для АН Эвы нужны только калькуляторы. Остальное (kp_pdf, secretary, monitoring) — если понадобится, скопируем позже

## 16.02.2026: GitHub приватный репо — raw ссылки не работают
**Проблема:** Claude.ai не может fetch'ить файлы из приватных репо через raw.githubusercontent.com
**Решение:** Сделать репо public (как rizalta-webchat)
**Почему:** GitHub CDN отдаёт 404 для приватных репо без авторизации

## 16.02.2026: GitHub CDN кеширует 404
**Проблема:** Файлы запушены, но raw.githubusercontent.com отдаёт 404 ещё 5-10 минут
**Решение:** Подождать или использовать `cat` на сервере для срочных случаев
**Почему:** CDN кеширует negative responses

## 16.02.2026: 1Code dev-режим
**Проблема:** Собранный билд 1Code глючит (no such table: anthropic_accounts)
**Решение:** Запускать через `cd ~/1code && bun run dev`
**Почему:** dev-режим корректно инициализирует БД, билд — нет

## 17.02.2026: Система сессий — GitHub как источник правды
**Решение:** Документация хранится в GitHub, обновляется через git. В Project Knowledge Claude.ai — только AN_EVA_PROJECT.md. AN_EVA_CURRENT.md fetch'ится из GitHub в начале каждого чата.
**Почему:** Меньше ручных шагов, один источник правды, не нужно каждый раз обновлять Project Knowledge

## 17.02.2026: SSH рвётся при длинных сессиях
**Проблема:** Connection reset by peer при длительном бездействии SSH
**Решение:** Переподключиться. Можно добавить в ~/.ssh/config: `ServerAliveInterval 60`

## 17.02.2026: pip --break-system-packages на сервере
**Проблема:** `pip install` отказывается ставить пакеты — externally-managed-environment (Ubuntu 24)
**Решение:** `pip install <pkg> --break-system-packages`
**Почему:** PEP 668, системный Python защищён. Альтернатива — venv, но для простоты пока --break-system-packages

## 17.02.2026: chromadb конфликт с jsonschema
**Проблема:** `pip install chromadb` падает — Cannot uninstall jsonschema 4.10.3, RECORD file not found
**Решение:** `pip install chromadb --break-system-packages --ignore-installed jsonschema`
**Почему:** Системный jsonschema установлен через apt, pip не может его удалить

## 17.02.2026: ASCII ошибка при работе с русским текстом на сервере
**Проблема:** `'ascii' codec can't encode characters` — Extractor, Analyzer, RAG, Generator падают
**Решение:** Добавить в systemd сервис: `Environment=LC_ALL=C.UTF-8`, `Environment=LANG=C.UTF-8`, `Environment=PYTHONIOENCODING=utf-8`
**Почему:** Сервер по умолчанию использует ASCII locale, русский текст не проходит

## 17.02.2026: main.py — запускать из WorkingDirectory
**Проблема:** `RuntimeError: Directory 'widget' does not exist` при запуске main.py
**Решение:** `cd /opt/an-eva && python3 main.py` или WorkingDirectory в systemd
**Почему:** StaticFiles("widget") ищет относительно CWD, не относительно файла

## 17.02.2026: 1Code worktree — код в отдельной ветке
**Проблема:** 1Code создал ветку functional-gopher-db8bc3, код не попал в main
**Решение:** `git fetch origin && git merge origin/functional-gopher-db8bc3` на сервере
**Почему:** 1Code с Worktree ON создаёт изолированные ветки. Нужно мержить в main после завершения
**На будущее:** После работы в 1Code — всегда мержить worktree-ветку в main

## 17.02.2026: RAG 0 примеров — utf-8 ошибка при загрузке
**Проблема:** `[rag] loaded: 0 examples` + `[rag] init error: 'ascii' codec can't encode`
**Решение:** НЕ ПОЧИНЕНО. Нужно: либо исправить locale при запуске ChromaDB, либо перекодировать examples.json
**Статус:** Система работает без RAG (примеры не подгружаются)

## 17.02.2026: OpenAI ключ скомпрометирован
**Проблема:** API ключ был показан в чате Claude.ai
**Решение:** Перевыпустить на platform.openai.com → API keys → revoke → create new
**Статус:** НЕ СДЕЛАНО — критично, сделать первым делом
