"""Тесты widget/ — статика отдаётся, HTML/JS корректны."""

import sys
import asyncio
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import AsyncClient, ASGITransport

WIDGET_DIR = Path(__file__).resolve().parent.parent / "widget"


def test_widget_files_exist():
    assert (WIDGET_DIR / "index.html").exists()
    assert (WIDGET_DIR / "chat.js").exists()
    print("  PASS test_widget_files_exist")


def test_html_structure():
    html = (WIDGET_DIR / "index.html").read_text(encoding="utf-8")
    assert "rizalta-chat-widget" in html
    assert "rzChatBtn" in html
    assert "rzChatWindow" in html
    assert "rzMessages" in html
    assert "rzInput" in html
    assert "Маргарита" in html
    assert "RIZALTA Resort Belokurikha" in html
    assert "chat.js" in html
    print("  PASS test_html_structure")


def test_html_mobile_responsive():
    html = (WIDGET_DIR / "index.html").read_text(encoding="utf-8")
    assert "@media (max-width: 480px)" in html
    assert "width: 100%" in html
    print("  PASS test_html_mobile_responsive")


def test_html_design_tokens():
    html = (WIDGET_DIR / "index.html").read_text(encoding="utf-8")
    assert "--rz-gold: #c9a54a" in html
    assert "--rz-bg: #060b06" in html
    assert "Raleway" in html
    print("  PASS test_html_design_tokens")


def test_js_structure():
    js = (WIDGET_DIR / "chat.js").read_text(encoding="utf-8")
    assert "RIZALTA_CHAT_API" in js
    assert "/api/session" in js
    assert "/api/chat" in js
    assert "/api/session/resume" in js
    assert "rz_session_id" in js
    assert "localStorage" in js
    assert "sessionStorage" in js
    print("  PASS test_js_structure")


def test_js_session_management():
    js = (WIDGET_DIR / "chat.js").read_text(encoding="utf-8")
    assert "createSession" in js
    assert "resumeSession" in js
    assert "sendMessage" in js
    print("  PASS test_js_session_management")


def test_js_error_handling():
    js = (WIDGET_DIR / "chat.js").read_text(encoding="utf-8")
    assert "AbortError" in js
    assert "AbortController" in js
    assert "связь подвисла" in js
    print("  PASS test_js_error_handling")


def test_js_auto_open():
    js = (WIDGET_DIR / "chat.js").read_text(encoding="utf-8")
    assert "AUTO_OPEN_DELAY" in js
    assert "30000" in js
    assert "rz_chat_opened" in js
    print("  PASS test_js_auto_open")


def test_js_quick_replies():
    js = (WIDGET_DIR / "chat.js").read_text(encoding="utf-8")
    assert "showQuickReplies" in js
    assert "rz-quick-btn" in js
    print("  PASS test_js_quick_replies")


def test_js_escapes_html():
    js = (WIDGET_DIR / "chat.js").read_text(encoding="utf-8")
    assert "escapeHtml" in js
    print("  PASS test_js_escapes_html")


async def test_static_serving():
    """Проверяем что FastAPI отдаёт статику виджета."""
    from main import app, state_manager
    import tempfile, os

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    state_manager.db_path = db_path
    await state_manager.init()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/widget/")
        assert r.status_code == 200
        assert "rizalta-chat-widget" in r.text
        print("  PASS test_static_serving (index.html)")

        r = await client.get("/widget/chat.js")
        assert r.status_code == 200
        assert "RIZALTA_CHAT_API" in r.text
        print("  PASS test_static_serving (chat.js)")

    await state_manager.close()
    os.unlink(db_path)


if __name__ == "__main__":
    sync_tests = [
        test_widget_files_exist,
        test_html_structure,
        test_html_mobile_responsive,
        test_html_design_tokens,
        test_js_structure,
        test_js_session_management,
        test_js_error_handling,
        test_js_auto_open,
        test_js_quick_replies,
        test_js_escapes_html,
    ]
    passed = 0
    for t in sync_tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")

    asyncio.run(test_static_serving())
    passed += 2

    print(f"\n{passed}/{len(sync_tests) + 2} tests passed")
