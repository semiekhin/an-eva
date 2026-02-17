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
