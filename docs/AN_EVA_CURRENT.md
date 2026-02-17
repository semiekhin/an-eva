# Текущий статус АН Эва

📅 **Последняя сессия:** 16.02.2026, 22:20 MSK
**Фаза:** 0 — Подготовка (завершена на 90%)

## ✅ Что сделано в этой сессии
- Создан проектный документ AN_EVA_PROJECT.md (полное ТЗ: архитектура, план, изоляция)
- Создан репозиторий github.com/semiekhin/an-eva (public)
- Клонирован на MacBook ~/Projects/an-eva/ и на сервер /opt/an-eva/
- Скопированы данные из существующих проектов на сервер:
  - properties.db (348 лотов) ✅
  - corp3_units.json + units.json ✅
  - rizalta_knowledge.md ✅
  - rag_training_data/ (50 примеров + ChromaDB) ✅
  - Калькуляторы: investment_calc, installment_calculator, deposit_calculator, calculations ✅
- Создан systemd сервис an-eva (не запущен — main.py ещё нет)
- Настроен 1Code: проект an-eva, Agent mode, Opus 4.6, Worktree
- Создана система управления сессиями (AN_EVA_SESSIONS.md)

## 🔄 Текущее состояние
### Работает:
- Репо на GitHub ✅
- Данные скопированы на сервер в /opt/an-eva/data/ и /opt/an-eva/services/ ✅
- systemd сервис an-eva создан ✅
- 1Code настроен и подключен к проекту ✅
- Текущая Маргарита продолжает работать на :8001 ✅

### Не сделано:
- Референсные файлы Софии не скопированы в refs/sofia/ (прервались)
- Код проекта не начат (Фаза 1)
- .env не создан на сервере
- Cloudflare tunnel eva-dev.rizaltaservice.ru не настроен
- Промпт текущей Маргариты не скопирован в refs/margarita/

## 🔜 Следующий шаг
Завершить Фазу 0:
1. Скопировать референсные файлы Софии и текущей Маргариты в refs/
2. Push на GitHub, pull на MacBook
3. Начать Фазу 1 в 1Code: config.py → extractor.py → state_manager.py

## 📁 Структура на сервере
```
/opt/an-eva/
├── .git/
├── docs/
│   ├── AN_EVA_PROJECT.md      ✅ полное ТЗ
│   └── CHANGELOG.md           (пустой)
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
