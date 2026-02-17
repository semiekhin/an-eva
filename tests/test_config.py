"""Тесты config.py — проверка что все настройки корректны."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    BASE_DIR, DATA_DIR, DB_DIR, DB_PATH,
    PORT, HOST, CORS_ORIGINS,
    LLM_MODEL, EXTRACTOR_MODEL, ANALYZER_MODEL, GENERATOR_MODEL,
    EXTRACTOR_MAX_TOKENS, EXTRACTOR_HISTORY_LIMIT,
    ANALYZER_HISTORY_LIMIT, GENERATOR_MAX_TOKENS, GENERATOR_HISTORY_LIMIT,
    STAGES, RAG_COLLECTION, RAG_TOP_K, RAG_EMBEDDING_MODEL,
)


def test_paths():
    assert BASE_DIR.exists(), f"BASE_DIR не существует: {BASE_DIR}"
    assert DATA_DIR.exists(), f"DATA_DIR не существует: {DATA_DIR}"
    assert str(DB_PATH).endswith("an_eva.db")
    print(f"  BASE_DIR: {BASE_DIR}")
    print(f"  DATA_DIR: {DATA_DIR}")
    print(f"  DB_PATH:  {DB_PATH}")


def test_server():
    assert PORT == 8005, f"PORT должен быть 8005, получено {PORT}"
    assert HOST == "0.0.0.0"


def test_cors():
    assert len(CORS_ORIGINS) == 6
    assert "https://rizaltabelokurikha.ru" in CORS_ORIGINS
    assert "http://localhost:3000" in CORS_ORIGINS


def test_models():
    assert LLM_MODEL == "gpt-5.2"
    assert EXTRACTOR_MODEL == LLM_MODEL
    assert ANALYZER_MODEL == LLM_MODEL
    assert GENERATOR_MODEL == LLM_MODEL


def test_limits():
    assert EXTRACTOR_MAX_TOKENS == 500
    assert EXTRACTOR_HISTORY_LIMIT == 6
    assert ANALYZER_HISTORY_LIMIT == 20
    assert GENERATOR_MAX_TOKENS == 4000
    assert GENERATOR_HISTORY_LIMIT == 100


def test_stages():
    assert len(STAGES) == 6
    assert "GREETING" in STAGES
    assert "CLOSING" in STAGES


def test_rag():
    assert RAG_COLLECTION == "rizalta_sales"
    assert RAG_TOP_K == 7
    assert RAG_EMBEDDING_MODEL == "text-embedding-3-small"


if __name__ == "__main__":
    tests = [test_paths, test_server, test_cors, test_models, test_limits, test_stages, test_rag]
    passed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"  PASS {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
        except Exception as e:
            print(f"  ERROR {name}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
