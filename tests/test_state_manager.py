"""Тесты state_manager.py — async StateManager + ClientState."""

import sys
import asyncio
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state_manager import StateManager, ClientState


async def run_tests():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        sm = StateManager(db_path=db_path)
        await sm.init()

        # 1. Новый клиент — пустое состояние
        state = await sm.get_state(1)
        assert state.user_id == 1
        assert state.goal is None
        assert state.is_qualified() is False
        print("  PASS test_new_client")

        # 2. Обновление полей
        state = await sm.update_state(1, {
            "goal": "investment", "goal_confidence": "confirmed",
            "budget": 10_000_000, "budget_confidence": "mentioned",
        })
        assert state.goal == "investment"
        assert state.goal_confidence == "confirmed"
        assert state.budget == 10_000_000
        assert state.budget_confidence == "mentioned"
        print("  PASS test_update")

        # 3. Персистентность — перечитываем из БД
        state2 = await sm.get_state(1)
        assert state2.goal == "investment"
        assert state2.budget == 10_000_000
        print("  PASS test_persistence")

        # 4. Квалификация: goal confirmed + budget confirmed = qualified
        await sm.update_state(1, {"budget_confidence": "confirmed"})
        state3 = await sm.get_state(1)
        assert state3.is_qualified() is True
        print("  PASS test_qualified")

        # 5. Missing fields
        missing = state3.get_missing_fields()
        assert "payment_type" in missing
        assert "goal" not in missing
        print("  PASS test_missing_fields")

        # 6. Qualification score
        score = state3.calculate_qualification_score()
        assert score > 0.5
        print(f"  PASS test_score (score={score:.2f})")

        # 7. Summary
        summary = state3.summary()
        assert "investment" in summary
        assert "10.0 млн" in summary
        print(f"  PASS test_summary")

        # 8. Clear temporary flags
        await sm.update_state(1, {
            "current_question_type": "price",
            "current_objection": "expensive",
            "wants_materials": True,
        })
        s = await sm.get_state(1)
        assert s.current_question_type == "price"
        await sm.clear_temporary_flags(1)
        s2 = await sm.get_state(1)
        assert s2.current_question_type is None
        assert s2.wants_materials is False
        print("  PASS test_clear_flags")

        # 9. Messages
        await sm.save_message("sess-1", 1, "user", "Привет")
        await sm.save_message("sess-1", 1, "assistant", "Здравствуйте!")
        history = await sm.get_history("sess-1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["content"] == "Здравствуйте!"
        print("  PASS test_messages")

        # 10. Web sessions
        await sm.create_session("sess-1", 1, "https://rizaltabelokurikha.ru")
        sess = await sm.get_session("sess-1")
        assert sess is not None
        assert sess["user_id"] == 1
        assert sess["page_url"] == "https://rizaltabelokurikha.ru"
        await sm.touch_session("sess-1")
        print("  PASS test_web_sessions")

        # 11. Reset state
        await sm.reset_state(1)
        s_reset = await sm.get_state(1)
        assert s_reset.goal is None
        print("  PASS test_reset")

        # 12. ClientState.to_dict
        cs = ClientState(user_id=99, goal="personal", goal_confidence="confirmed",
                         budget=5_000_000, budget_confidence="confirmed")
        d = cs.to_dict()
        assert d["goal"] == "personal"
        assert d["budget"] == 5_000_000
        print("  PASS test_to_dict")

        await sm.close()
        print(f"\n12/12 tests passed")

    finally:
        os.unlink(db_path)


if __name__ == "__main__":
    asyncio.run(run_tests())
