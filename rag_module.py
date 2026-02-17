"""
rag_module.py — векторный RAG для АН Эва
==========================================
ChromaDB + OpenAI text-embedding-3-small.
Адаптация Sofia-GPT rag_module.py для RIZALTA.
Данные: data/rag_training_data/examples.json (50 примеров).
Индекс: data/chroma_db/ (создаётся при первом запуске).
"""

import json
import logging
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from config import (
    OPENAI_API_KEY, DATA_DIR,
    RAG_COLLECTION, RAG_TOP_K, RAG_EMBEDDING_MODEL,
)

log = logging.getLogger(__name__)

RAG_DATA_PATH = DATA_DIR / "rag_training_data" / "examples.json"
CHROMA_PATH = DATA_DIR / "chroma_db"

_collection = None


def _get_embedding_fn():
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name=RAG_EMBEDDING_MODEL,
    )


def init_rag() -> bool:
    """
    Инициализация ChromaDB. Вызывать один раз при старте.
    Если коллекция уже существует — открывает. Иначе создаёт и индексирует.
    """
    global _collection

    if not OPENAI_API_KEY:
        log.error("[rag] OPENAI_API_KEY not set")
        return False

    try:
        ef = _get_embedding_fn()
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))

        _collection = client.get_or_create_collection(
            name=RAG_COLLECTION,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )

        if _collection.count() > 0:
            log.info(f"[rag] loaded: {_collection.count()} examples")
            return True

        # Индексируем

        examples = _load_examples()
        if not examples:
            log.warning("[rag] no examples to index")
            return False

        documents = []
        metadatas = []
        ids = []

        for i, ex in enumerate(examples):
            documents.append(f"Клиент: {ex.get('client_message', '')}")
            metadatas.append({
                "stage": ex.get("stage", "UNKNOWN"),
                "quality": ex.get("quality", "good"),
                "bot_message": ex.get("bot_message", "")[:1000],
            })
            ids.append(f"ex_{i}")

        # Батчами по 100
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            _collection.add(
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
                ids=ids[i:i + batch_size],
            )

        log.info(f"[rag] indexed {len(documents)} examples")
        return True

    except Exception as e:
        log.error(f"[rag] init error: {e}")
        return False


def _load_examples() -> list[dict]:
    """Загружает примеры из JSON."""
    try:
        with open(RAG_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("examples", [])
    except FileNotFoundError:
        log.warning(f"[rag] file not found: {RAG_DATA_PATH}")
        return []
    except json.JSONDecodeError as e:
        log.error(f"[rag] JSON parse error: {e}")
        return []


def search_examples(
    stage: str,
    query: str,
    limit: int | None = None,
) -> list[dict]:
    """
    Поиск примеров по stage + query.

    Args:
        stage: этап диалога (GREETING, QUALIFICATION, ...)
        query: текст для семантического поиска
        limit: кол-во результатов (default: RAG_TOP_K из config)

    Returns:
        list of {"stage", "client", "manager", "quality", "similarity"}
    """
    global _collection

    if limit is None:
        limit = RAG_TOP_K

    if _collection is None:
        if not init_rag():
            return []

    try:
        query_text = f"Клиент: {query}"

        # Сначала ищем по stage + quality
        results = _collection.query(
            query_texts=[query_text],
            n_results=limit * 2,
            where={
                "$and": [
                    {"stage": {"$eq": stage}},
                    {"quality": {"$in": ["excellent", "good"]}},
                ]
            },
            include=["metadatas", "documents", "distances"],
        )

        # Fallback: если мало по stage — ищем без фильтра этапа
        if not results["ids"][0]:
            results = _collection.query(
                query_texts=[query_text],
                n_results=limit,
                where={"quality": {"$in": ["excellent", "good"]}},
                include=["metadatas", "documents", "distances"],
            )

        examples = []
        for i, doc_id in enumerate(results["ids"][0][:limit]):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i] if results.get("distances") else 0

            examples.append({
                "stage": meta.get("stage", ""),
                "client": results["documents"][0][i].replace("Клиент: ", ""),
                "manager": meta.get("bot_message", ""),
                "quality": meta.get("quality", ""),
                "similarity": round(1 - dist, 3),
            })

        log.info(f"[rag] search '{query[:30]}' stage={stage}: {len(examples)} results")
        return examples

    except Exception as e:
        log.error(f"[rag] search error: {e}")
        return []


def format_examples_for_prompt(examples: list[dict]) -> str:
    """Форматирует примеры для системного промпта генератора."""
    if not examples:
        return ""

    lines = ["ПРИМЕРЫ УСПЕШНЫХ ДИАЛОГОВ НА ЭТОМ ЭТАПЕ:", ""]

    for i, ex in enumerate(examples, 1):
        sim = ex.get("similarity", "")
        sim_str = f" (сходство: {sim})" if sim else ""
        lines.append(f"Пример {i}{sim_str}:")
        lines.append(f"  Клиент: \u00ab{ex.get('client', '')}\u00bb")
        lines.append(f"  Менеджер: \u00ab{ex.get('manager', '')}\u00bb")
        lines.append("")

    return "\n".join(lines)


def get_stats() -> dict:
    """Статистика коллекции."""
    if _collection is None:
        return {"status": "not_initialized", "count": 0}

    try:
        count = _collection.count()
        all_items = _collection.get(include=["metadatas"])
        stages = {}
        for meta in all_items["metadatas"]:
            s = meta.get("stage", "UNKNOWN")
            stages[s] = stages.get(s, 0) + 1
        return {"status": "ready", "count": count, "stages": stages}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def rebuild_index() -> bool:
    """Пересоздаёт индекс (после обновления examples.json)."""
    global _collection
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        try:
            client.delete_collection(RAG_COLLECTION)
        except Exception:
            pass
        _collection = None
        return init_rag()
    except Exception as e:
        log.error(f"[rag] rebuild error: {e}")
        return False
