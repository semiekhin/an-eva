# Текущий статус АН Эва

📅 **Последняя сессия:** 17.02.2026, 01:45 MSK
**Фаза:** 0 — Подготовка (завершена на 95%)

## ✅ Что сделано в этой сессии (17.02.2026)
- Обсуждено объединение трёх проектов (Софья + RIZALTA-бот + WebChat)
- Обновлён AN_EVA_PROJECT.md: принцип изоляции, свой путь /opt/an-eva/, порт 8005
- Создан репозиторий github.com/semiekhin/an-eva (public)
- Клонирован на MacBook ~/Projects/an-eva/ и на сервер /opt/an-eva/
- Скопированы данные на сервер:
  - properties.db (348 лотов) ✅
  - corp3_units.json + units.json ✅
  - rizalta_knowledge.md ✅
  - rag_training_data/ (50 примеров + ChromaDB) ✅
  - Калькуляторы: investment_calc, installment_calculator, deposit_calculator, calculations ✅
- Создан systemd сервис an-eva (не запущен — main.py ещё нет)
- Настроен 1Code: проект an-eva, Agent mode, Opus 4.6, Worktree
- Создана система управления сессиями (SESSION_END_TEMPLATE.md)
- Решено: источник правды — GitHub, документация обновляется через git

## 🔄 Текущее состояние
### Работает:
- Репо на GitHub: github.com/semiekhin/an-eva ✅
- Данные скопированы на сервер в /opt/an-eva/data/ и /opt/an-eva/services/ ✅
- systemd сервис an-eva создан ✅
- 1Code настроен и подключен к проекту ✅
- Текущая Маргарита продолжает работать на :8001 ✅

### Не сделано:
- Референсные файлы Софии НЕ скопированы в refs/sofia/ (SSH упал)
- Промпт текущей Маргариты НЕ скопирован в refs/margarita/
- Код проекта не начат (Фаза 1)
- .env не создан на сервере
- Cloudflare tunnel eva-dev.rizaltaservice.ru не настроен

## 🔜 Следующий шаг
1. SSH на сервер → скопировать refs/sofia/ и refs/margarita/ (команда ниже)
2. git push → git pull на MacBook
3. В 1Code начать Фазу 1: config.py → extractor.py → state_manager.py → analyzer.py

## 📁 Структура на сервере
```
/opt/an-eva/
├── .git/
├── docs/
│   ├── AN_EVA_PROJECT.md      ✅ полное ТЗ с изоляцией
│   ├── AN_EVA_CURRENT.md      ✅ этот файл
│   ├── AN_EVA_KNOWLEDGE.md    ✅ база знаний
│   ├── CHANGELOG.md           ✅ лог изменений
│   └── SESSION_END_TEMPLATE.md ✅ инструкция завершения сессии
├── data/
│   ├── properties.db          ✅ 348 лотов
│   ├── corp3_units.json       ✅ корпус Digital
│   ├── units.json             ✅ все юниты
│   ├── rizalta_knowledge.md   ✅ база знаний
│   └── rag_training_data/     ✅ 50 примеров + ChromaDB
├── services/
│   ├── investment_calc.py     ✅
│   ├── installment_calculator.py ✅
│   ├── deposit_calculator.py  ✅
│   └── calculations.py        ✅
├── db/                        (пусто)
├── widget/                    (пусто)
└── .gitignore                 ✅
```

## ⚠️ Важный контекст для следующего чата
- Порт АН Эвы: 8005 (dev), 8001 только после замены старой Маргариты
- Путь: /opt/an-eva/ (НЕ /opt/rizalta-webchat/)
- Все существующие сервисы НЕ ТРОГАТЬ
- Разработка в 1Code на MacBook → push → pull на сервер
- Открытые вопросы (секция 15 в PROJECT.md): CRM, цены, Observer, Deep links

## 📋 Невыполненная команда (запустить первой в следующей сессии)
```bash
ssh root@72.56.64.91 -p 2222

mkdir -p /opt/an-eva/refs/sofia
cp /opt/sofia-gpt/extractor.py /opt/an-eva/refs/sofia/
cp /opt/sofia-gpt/state_manager.py /opt/an-eva/refs/sofia/
cp /opt/sofia-gpt/message_processor.py /opt/an-eva/refs/sofia/
cp /opt/sofia-gpt/rag_module.py /opt/an-eva/refs/sofia/
cp /opt/sofia-gpt/sofia_prompt_v2.py /opt/an-eva/refs/sofia/
cp /opt/sofia-gpt/web_api.py /opt/an-eva/refs/sofia/
cp /opt/sofia-gpt/bot_server.py /opt/an-eva/refs/sofia/

mkdir -p /opt/an-eva/refs/margarita
cp /opt/rizalta-webchat/rizalta_prompt.py /opt/an-eva/refs/margarita/
cp /opt/rizalta-webchat/widget/chat-widget.html /opt/an-eva/refs/margarita/
cp /opt/rizalta-webchat/widget/chat-widget.js /opt/an-eva/refs/margarita/

cd /opt/an-eva
git add -A && git commit -m "refs: Sofia + Margarita source files" && git push
```
Затем на MacBook:
```bash
cd ~/Projects/an-eva && git pull
```
