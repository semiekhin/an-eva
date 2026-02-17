"""Тесты main.py — endpoints, session management, pipeline (mock LLM)."""

import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock init_rag before import
with patch("rag_module.init_rag", return_value=True):
    pass

from httpx import AsyncClient, ASGITransport
from main import app, state_manager, GREETING


async def setup():
    """Init state_manager with temp DB."""
    import tempfile, os
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    state_manager.db_path = db_path
    await state_manager.init()
    return db_path


async def teardown(db_path):
    import os
    await state_manager.close()
    os.unlink(db_path)


async def run_tests():
    db_path = await setup()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # 1. Health
        r = await client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        print("  PASS test_health")

        # 2. Create session
        r = await client.post("/api/session", json={"page_url": "https://rizaltabelokurikha.ru"})
        assert r.status_code == 200
        data = r.json()
        assert "session_id" in data
        assert data["greeting"] == GREETING
        session_id = data["session_id"]
        print("  PASS test_create_session")

        # 3. Resume session
        r = await client.post("/api/session/resume", json={"session_id": session_id, "message": ""})
        assert r.status_code == 200
        data = r.json()
        assert len(data["history"]) >= 1  # greeting saved
        assert data["history"][0]["role"] == "assistant"
        print("  PASS test_resume_session")

        # 4. Resume non-existent session
        r = await client.post("/api/session/resume", json={"session_id": "fake-id", "message": ""})
        assert r.status_code == 404
        print("  PASS test_resume_404")

        # 5. Chat — empty message
        r = await client.post("/api/chat", json={"session_id": session_id, "message": ""})
        assert r.status_code == 400
        print("  PASS test_chat_empty")

        # 6. Chat — too long
        r = await client.post("/api/chat", json={"session_id": session_id, "message": "x" * 2001})
        assert r.status_code == 400
        print("  PASS test_chat_too_long")

        # 7. Chat — full pipeline (mock LLM calls)
        mock_extraction = {
            "goal": "investment", "goal_confidence": "confirmed",
            "budget": None, "budget_confidence": None,
            "payment_type": None, "payment_type_confidence": None,
            "preferred_corpus": None, "preferred_area": None,
            "question_type": None, "objection": None,
            "wants_materials": False, "contact_given": False,
            "meeting_agreed": False, "mentioned_price": None,
            "sentiment": "positive",
            "signals": {"friction": 0.2, "call_readiness": 0.5, "engagement": "high", "urgency": "month"},
        }
        mock_analysis = {"stage": "QUALIFICATION", "rag_query": "инвестиция курортная недвижимость", "client_intent": "хочет инвестировать"}
        mock_gen = {"answer": "Отличный выбор! На какой бюджет ориентируетесь?", "ended": False, "finish_type": None}

        with patch("main.process_message", new_callable=AsyncMock) as mock_pm, \
             patch("main.analyze", new_callable=AsyncMock, return_value=mock_analysis), \
             patch("main.search_examples", return_value=[]), \
             patch("main.generate", new_callable=AsyncMock, return_value=mock_gen):

            mock_pm.return_value = {
                "client_state": (await state_manager.get_state(9_000_001)),
                "extraction": mock_extraction,
            }

            r = await client.post("/api/chat", json={
                "session_id": session_id,
                "message": "Хочу инвестировать",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["session_id"] == session_id
            assert "бюджет" in data["reply"].lower() or "Отличный" in data["reply"]
            assert "timestamp" in data
            print("  PASS test_chat_pipeline")

        # 8. History endpoint
        r = await client.get(f"/api/history/{session_id}")
        assert r.status_code == 200
        data = r.json()
        assert len(data["messages"]) >= 2  # greeting + user msg + bot reply
        print(f"  PASS test_history ({len(data['messages'])} messages)")

        # 9. History 404
        r = await client.get("/api/history/fake-session")
        assert r.status_code == 404
        print("  PASS test_history_404")

        # 10. GET /api/docs/current — returns AN_EVA_CURRENT.md as plain text
        r = await client.get("/api/docs/current")
        if r.status_code == 200:
            assert "text/plain" in r.headers["content-type"]
            assert r.headers["cache-control"] == "no-cache"
            assert len(r.text) > 0
            print("  PASS test_docs_current")
        else:
            # File may not exist in test env — just check it's 404
            assert r.status_code == 404
            print("  PASS test_docs_current (404 — file absent)")

    await teardown(db_path)
    print(f"\n10/10 tests passed")


if __name__ == "__main__":
    asyncio.run(run_tests())
