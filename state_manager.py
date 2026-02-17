"""
state_manager.py — управление состоянием клиента
=================================================
Адаптация Sofia-GPT StateManager для RIZALTA Resort Belokurikha.
- Один объект → нет location
- Добавлены preferred_corpus, preferred_area, contact_collected
- Async (aiosqlite), WAL mode
- Квалификация: goal → budget → payment_type (макс 3 вопроса)
"""

import aiosqlite
import json
from dataclasses import dataclass, field
from typing import Optional, Literal
from datetime import datetime

from config import DB_PATH, DB_DIR

ConfidenceLevel = Literal["confirmed", "mentioned"]


@dataclass
class ClientState:
    """Состояние клиента в диалоге."""

    user_id: int

    # Квалификация (3 ключевых поля)
    goal: Optional[str] = None                          # investment | personal
    goal_confidence: Optional[ConfidenceLevel] = None

    budget: Optional[int] = None                        # в рублях
    budget_confidence: Optional[ConfidenceLevel] = None

    payment_type: Optional[str] = None                  # full | mortgage | installment | any
    payment_type_confidence: Optional[ConfidenceLevel] = None

    # Предпочтения по объекту
    preferred_corpus: Optional[str] = None              # family | business | digital
    preferred_area: Optional[str] = None                # small | medium | large

    # Статус диалога
    meeting_agreed: bool = False
    contact_collected: bool = False
    call_refused: bool = False
    dialog_finished: bool = False
    finish_type: Optional[str] = None                   # meeting | materials | contact

    # Счётчики
    call_proposal_count: int = 0
    materials_request_count: int = 0

    # Временные флаги (сбрасываются после обработки)
    current_question_type: Optional[str] = None
    current_objection: Optional[str] = None
    wants_materials: bool = False

    # Упоминания
    mentioned_price: Optional[int] = None

    # Латентные метрики (signals)
    friction: float = 0.3
    call_readiness: float = 0.5
    engagement: str = "medium"                          # low | medium | high
    urgency: str = "unclear"                            # now | week | month | unclear

    # Мета
    qualification_score: float = 0.0
    updated_at: Optional[str] = None

    def is_qualified(self) -> bool:
        """Минимальная квалификация: goal + budget confirmed."""
        return (
            self.goal is not None and self.goal_confidence == "confirmed"
            and self.budget is not None and self.budget_confidence == "confirmed"
        )

    def get_missing_fields(self) -> list[str]:
        """Неподтверждённые обязательные поля."""
        missing = []
        if not self.goal or self.goal_confidence != "confirmed":
            missing.append("goal")
        if not self.budget or self.budget_confidence != "confirmed":
            missing.append("budget")
        if not self.payment_type or self.payment_type_confidence != "confirmed":
            missing.append("payment_type")
        return missing

    def calculate_qualification_score(self) -> float:
        """Скор квалификации 0.0 - 1.0."""
        fields = ("goal", "budget", "payment_type")
        confirmed = 0
        mentioned = 0
        for f in fields:
            conf = getattr(self, f"{f}_confidence", None)
            if conf == "confirmed":
                confirmed += 1
            elif conf == "mentioned":
                mentioned += 1
        return min((confirmed * 1.0 + mentioned * 0.3) / len(fields), 1.0)

    def to_dict(self) -> dict:
        """Конвертация в dict для логирования / промпта."""
        return {
            "goal": self.goal, "goal_confidence": self.goal_confidence,
            "budget": self.budget, "budget_confidence": self.budget_confidence,
            "payment_type": self.payment_type, "payment_type_confidence": self.payment_type_confidence,
            "preferred_corpus": self.preferred_corpus,
            "preferred_area": self.preferred_area,
            "meeting_agreed": self.meeting_agreed,
            "contact_collected": self.contact_collected,
            "qualification_score": self.qualification_score,
        }

    def summary(self) -> str:
        """Краткая сводка для промпта генератора."""
        parts = []
        if self.goal:
            parts.append(f"Цель: {self.goal} ({self.goal_confidence})")
        if self.budget:
            parts.append(f"Бюджет: {self.budget / 1_000_000:.1f} млн ({self.budget_confidence})")
        if self.payment_type:
            parts.append(f"Оплата: {self.payment_type} ({self.payment_type_confidence})")
        if self.preferred_corpus:
            parts.append(f"Корпус: {self.preferred_corpus}")
        if self.preferred_area:
            parts.append(f"Площадь: {self.preferred_area}")
        if self.meeting_agreed:
            parts.append("Показ: согласован")
        if self.contact_collected:
            parts.append("Контакт: получен")

        if not parts:
            return "Квалификация: не начата"

        return f"Квалификация ({self.qualification_score:.0%}): " + ", ".join(parts)


# ─── SQL ────────────────────────────────────────────────────────────────────

_CREATE_CLIENT_STATE = """
CREATE TABLE IF NOT EXISTS client_state (
    user_id INTEGER PRIMARY KEY,
    goal TEXT,
    goal_confidence TEXT,
    budget INTEGER,
    budget_confidence TEXT,
    payment_type TEXT,
    payment_type_confidence TEXT,
    preferred_corpus TEXT,
    preferred_area TEXT,
    meeting_agreed BOOLEAN DEFAULT 0,
    contact_collected BOOLEAN DEFAULT 0,
    call_refused BOOLEAN DEFAULT 0,
    dialog_finished BOOLEAN DEFAULT 0,
    finish_type TEXT,
    call_proposal_count INTEGER DEFAULT 0,
    materials_request_count INTEGER DEFAULT 0,
    current_question_type TEXT,
    current_objection TEXT,
    wants_materials BOOLEAN DEFAULT 0,
    mentioned_price INTEGER,
    friction REAL DEFAULT 0.3,
    call_readiness REAL DEFAULT 0.5,
    engagement TEXT DEFAULT 'medium',
    urgency TEXT DEFAULT 'unclear',
    qualification_score REAL DEFAULT 0.0,
    updated_at TEXT
)
"""

_CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now'))
)
"""

_CREATE_WEB_SESSIONS = """
CREATE TABLE IF NOT EXISTS web_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    last_active TEXT DEFAULT (datetime('now')),
    page_url TEXT
)
"""

_COLUMNS = [
    "user_id", "goal", "goal_confidence", "budget", "budget_confidence",
    "payment_type", "payment_type_confidence", "preferred_corpus", "preferred_area",
    "meeting_agreed", "contact_collected", "call_refused",
    "dialog_finished", "finish_type",
    "call_proposal_count", "materials_request_count",
    "current_question_type", "current_objection", "wants_materials",
    "mentioned_price",
    "friction", "call_readiness", "engagement", "urgency",
    "qualification_score", "updated_at",
]


class StateManager:
    """Async менеджер состояния клиентов с SQLite (aiosqlite, WAL)."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(DB_PATH)
        self._db: aiosqlite.Connection | None = None

    async def init(self):
        """Инициализация БД: создание таблиц, WAL mode."""
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute(_CREATE_CLIENT_STATE)
        await self._db.execute(_CREATE_MESSAGES)
        await self._db.execute(_CREATE_WEB_SESSIONS)
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
        )
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    # ─── Client State ───────────────────────────────────────────────────

    async def get_state(self, user_id: int) -> ClientState:
        """Получить состояние клиента (создаёт новое если нет)."""
        cursor = await self._db.execute(
            "SELECT * FROM client_state WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            return ClientState(user_id=user_id)

        return ClientState(
            user_id=row["user_id"],
            goal=row["goal"],
            goal_confidence=row["goal_confidence"],
            budget=row["budget"],
            budget_confidence=row["budget_confidence"],
            payment_type=row["payment_type"],
            payment_type_confidence=row["payment_type_confidence"],
            preferred_corpus=row["preferred_corpus"],
            preferred_area=row["preferred_area"],
            meeting_agreed=bool(row["meeting_agreed"]),
            contact_collected=bool(row["contact_collected"]),
            call_refused=bool(row["call_refused"]),
            dialog_finished=bool(row["dialog_finished"]),
            finish_type=row["finish_type"],
            call_proposal_count=row["call_proposal_count"] or 0,
            materials_request_count=row["materials_request_count"] or 0,
            current_question_type=row["current_question_type"],
            current_objection=row["current_objection"],
            wants_materials=bool(row["wants_materials"]),
            mentioned_price=row["mentioned_price"],
            friction=row["friction"] if row["friction"] is not None else 0.3,
            call_readiness=row["call_readiness"] if row["call_readiness"] is not None else 0.5,
            engagement=row["engagement"] or "medium",
            urgency=row["urgency"] or "unclear",
            qualification_score=row["qualification_score"] or 0.0,
            updated_at=row["updated_at"],
        )

    async def update_state(self, user_id: int, updates: dict) -> ClientState:
        """Обновить состояние клиента."""
        state = await self.get_state(user_id)

        skip = {
            "is_qualified", "get_missing_fields", "calculate_qualification_score",
            "to_dict", "summary",
        }

        for key, value in updates.items():
            if key in skip:
                continue
            if hasattr(state, key) and not callable(getattr(state, key)):
                setattr(state, key, value)

        state.qualification_score = state.calculate_qualification_score()
        state.updated_at = datetime.now().isoformat()

        await self._save_state(state)
        return state

    async def _save_state(self, state: ClientState):
        placeholders = ", ".join("?" * len(_COLUMNS))
        cols = ", ".join(_COLUMNS)
        values = tuple(getattr(state, c) for c in _COLUMNS)

        await self._db.execute(
            f"INSERT OR REPLACE INTO client_state ({cols}) VALUES ({placeholders})",
            values,
        )
        await self._db.commit()

    async def reset_state(self, user_id: int):
        await self._db.execute("DELETE FROM client_state WHERE user_id = ?", (user_id,))
        await self._db.commit()

    async def clear_temporary_flags(self, user_id: int):
        await self._db.execute("""
            UPDATE client_state
            SET current_question_type = NULL,
                current_objection = NULL,
                wants_materials = 0
            WHERE user_id = ?
        """, (user_id,))
        await self._db.commit()

    # ─── Messages ────────────────────────────────────────────────────────

    async def save_message(self, session_id: str, user_id: int, role: str, content: str):
        await self._db.execute(
            "INSERT INTO messages (session_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (session_id, user_id, role, content),
        )
        await self._db.commit()

    async def get_history(self, session_id: str, limit: int = 100) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = await cursor.fetchall()
        return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in reversed(rows)]

    # ─── Web Sessions ────────────────────────────────────────────────────

    async def create_session(self, session_id: str, user_id: int, page_url: str = None):
        await self._db.execute(
            "INSERT INTO web_sessions (session_id, user_id, page_url) VALUES (?, ?, ?)",
            (session_id, user_id, page_url),
        )
        await self._db.commit()

    async def get_session(self, session_id: str) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM web_sessions WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "created_at": row["created_at"],
            "last_active": row["last_active"],
            "page_url": row["page_url"],
        }

    async def touch_session(self, session_id: str):
        await self._db.execute(
            "UPDATE web_sessions SET last_active = datetime('now') WHERE session_id = ?",
            (session_id,),
        )
        await self._db.commit()
