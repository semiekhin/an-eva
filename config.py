"""
config.py — настройки проекта АН Эва
=====================================
Все конфигурационные параметры в одном месте.
Секреты загружаются из .env, остальное — константы.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === Пути ===
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "an_eva.db"

# === Сервер ===
PORT = int(os.getenv("PORT", "8005"))
HOST = os.getenv("HOST", "0.0.0.0")

# === CORS ===
CORS_ORIGINS = [
    "https://rizaltabelokurikha.ru",
    "http://rizaltabelokurikha.ru",
    "https://www.rizaltabelokurikha.ru",
    "http://www.rizaltabelokurikha.ru",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "https://eva-dev.rizaltaservice.ru",
    "http://eva-dev.rizaltaservice.ru",
]

# === OpenAI ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = "gpt-5.2"

# Extractor: быстрый NLU, ~10 полей
EXTRACTOR_MODEL = LLM_MODEL
EXTRACTOR_MAX_TOKENS = 500
EXTRACTOR_HISTORY_LIMIT = 6  # последних сообщений для контекста

# Analyzer: определяет stage + rag_query
ANALYZER_MODEL = LLM_MODEL
ANALYZER_MAX_TOKENS = 300
ANALYZER_HISTORY_LIMIT = 20

# Generator: финальный ответ клиенту
GENERATOR_MODEL = LLM_MODEL
GENERATOR_MAX_TOKENS = 4000
GENERATOR_HISTORY_LIMIT = 100  # единый лимит (урок из Софии)

# === Этапы диалога ===
STAGES = [
    "GREETING",
    "QUALIFICATION",
    "PRESENTATION",
    "MEETING",
    "OBJECTION",
    "CLOSING",
]

# === RAG ===
RAG_COLLECTION = "rizalta_sales"
RAG_TOP_K = 7
RAG_EMBEDDING_MODEL = "text-embedding-3-small"

# === CRM ===
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "")

# === Observer ===
OBSERVER_BOT_TOKEN = os.getenv("OBSERVER_BOT_TOKEN", "")
OBSERVER_CHAT_ID = os.getenv("OBSERVER_CHAT_ID", "")

# === Telegram Leads ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_NOTIFY_CHAT_ID = os.getenv("TELEGRAM_NOTIFY_CHAT_ID", "")
