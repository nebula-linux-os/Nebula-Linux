"""Persistent memory store backed by SQLite.

The agent can save and recall facts across sessions — things like user
preferences, project paths, past task outcomes, and learned shortcuts.
Memories are short text entries tagged with a category and timestamp.
Relevant memories are injected into the system prompt so the model has
context without the user repeating themselves.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

_DB_LOCK = threading.Lock()

DEFAULT_DB = Path.home() / ".nebula-agent" / "memory.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at REAL NOT NULL,
            last_used REAL,
            use_count INTEGER DEFAULT 0
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            model TEXT NOT NULL,
            steps INTEGER NOT NULL,
            outcome TEXT NOT NULL,
            duration_s REAL NOT NULL,
            created_at REAL NOT NULL
        )"""
    )
    conn.commit()
    return conn


class MemoryStore:
    def __init__(self, db_path: Path = DEFAULT_DB) -> None:
        self.conn = _connect(db_path)

    def save(self, category: str, content: str) -> int:
        with _DB_LOCK:
            cur = self.conn.execute(
                "INSERT INTO memories (category, content, created_at) VALUES (?, ?, ?)",
                (category, content, time.time()),
            )
            self.conn.commit()
            return cur.lastrowid

    def recall(self, query: str = "", category: str = "", limit: int = 20) -> list[dict]:
        conditions = []
        params: list = []
        if query:
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")
        if category:
            conditions.append("category = ?")
            params.append(category)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = self.conn.execute(
            f"SELECT id, category, content, created_at, use_count FROM memories{where} "
            f"ORDER BY last_used DESC NULLS LAST, created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [
            {"id": r[0], "category": r[1], "content": r[2], "created_at": r[3], "use_count": r[4]}
            for r in rows
        ]

    def touch(self, memory_id: int) -> None:
        self.conn.execute(
            "UPDATE memories SET last_used = ?, use_count = use_count + 1 WHERE id = ?",
            (time.time(), memory_id),
        )
        self.conn.commit()

    def forget(self, memory_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def log_task(self, task: str, model: str, steps: int, outcome: str, duration_s: float) -> None:
        self.conn.execute(
            "INSERT INTO task_history (task, model, steps, outcome, duration_s, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (task, model, steps, outcome, duration_s, time.time()),
        )
        self.conn.commit()

    def recent_tasks(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT task, model, steps, outcome, duration_s, created_at "
            "FROM task_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"task": r[0], "model": r[1], "steps": r[2], "outcome": r[3],
             "duration_s": r[4], "created_at": r[5]}
            for r in rows
        ]

    def format_for_prompt(self, limit: int = 10) -> str:
        memories = self.recall(limit=limit)
        if not memories:
            return ""
        lines = ["Here are things you remember from previous sessions:"]
        for m in memories:
            lines.append(f"- [{m['category']}] {m['content']}")
            self.touch(m["id"])
        return "\n".join(lines)

    def close(self) -> None:
        self.conn.close()
