"""Тесты message_processor.py — пайплайн без API (mock extractor)."""

import sys
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state_manager import StateManager
from message_processor import process_message


MOCK_EXTRACTION = {
    "answered_last_bot_question": "yes",
    "answer_mode": "value",
    "target_slot": "goal",
    "goal": "investment",
    "goal_confidence": "confirmed",
    "budget": 10_000_000,
    "budget_confidence": "confirmed",
    "payment_type": None,
    "payment_type_confidence": None,
    "preferred_corpus": "family",
    "preferred_area": None,
    "question_type": None,
    "objection": None,
    "wants_materials": False,
    "contact_given": False,
    "meeting_agreed": False,
    "mentioned_price": None,
    "sentiment": "positive",
    "signals": {
        "friction": 0.1,
        "call_readiness": 0.6,
        "engagement": "high",
        "urgency": "month",
    },
}


async def run_tests():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        sm = StateManager(db_path=db_path)
        await sm.init()

        # 1. Полный пайплайн с mock extractor
        with patch("message_processor.extract", new_callable=AsyncMock, return_value=MOCK_EXTRACTION):
            result = await process_message(
                user_id=1,
                message="Хочу инвестировать в Family до 10 млн",
                history=[],
                state_manager=sm,
            )

        state = result["client_state"]
        extraction = result["extraction"]

        assert state.goal == "investment"
        assert state.goal_confidence == "confirmed"
        assert state.budget == 10_000_000
        assert state.preferred_corpus == "family"
        assert extraction["sentiment"] == "positive"
        print("  PASS test_pipeline_basic")

        # 2. State persisted
        s = await sm.get_state(1)
        assert s.goal == "investment"
        assert s.budget == 10_000_000
        print("  PASS test_persistence")

        # 3. Qualification score updated
        assert s.qualification_score > 0.5
        print(f"  PASS test_score (score={s.qualification_score:.2f})")

        # 4. Signals updated
        s2 = await sm.get_state(1)
        assert s2.friction == 0.1
        assert s2.call_readiness == 0.6
        assert s2.engagement == "high"
        assert s2.urgency == "month"
        print("  PASS test_signals")

        # 5. Dialog finished reset
        await sm.update_state(1, {"dialog_finished": True, "finish_type": "contact"})
        with patch("message_processor.extract", new_callable=AsyncMock, return_value=MOCK_EXTRACTION):
            result2 = await process_message(
                user_id=1,
                message="Ещё один вопрос",
                history=[],
                state_manager=sm,
            )
        assert result2["client_state"].dialog_finished is False
        print("  PASS test_dialog_reset")

        # 6. Materials count increment
        mock_materials = {**MOCK_EXTRACTION, "wants_materials": True}
        with patch("message_processor.extract", new_callable=AsyncMock, return_value=mock_materials):
            await process_message(user_id=1, message="Скиньте КП", history=[], state_manager=sm)
        s3 = await sm.get_state(1)
        assert s3.materials_request_count >= 1
        print("  PASS test_materials_count")

        await sm.close()
        print(f"\n6/6 tests passed")

    finally:
        os.unlink(db_path)


if __name__ == "__main__":
    asyncio.run(run_tests())
