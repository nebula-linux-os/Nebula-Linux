"""Memory-related tools exposed to the LLM.

These let the model save facts it learns, recall them later, and check
what tasks have been run before. They are non-risky (no filesystem or
shell side-effects beyond the SQLite database).
"""
from __future__ import annotations

from .memory import MemoryStore

_store: MemoryStore | None = None


def _get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


def set_store(store: MemoryStore) -> None:
    global _store
    _store = store


def save_memory(category: str, content: str) -> dict:
    mem_id = _get_store().save(category, content)
    return {"saved": True, "id": mem_id, "category": category}


def recall_memory(query: str = "", category: str = "") -> dict:
    results = _get_store().recall(query=query, category=category)
    return {"count": len(results), "memories": results}


def forget_memory(memory_id: int) -> dict:
    ok = _get_store().forget(memory_id)
    return {"deleted": ok, "id": memory_id}


def past_tasks(limit: int = 5) -> dict:
    tasks = _get_store().recent_tasks(limit=limit)
    return {"count": len(tasks), "tasks": tasks}


MEMORY_TOOL_FUNCTIONS = {
    "save_memory": save_memory,
    "recall_memory": recall_memory,
    "forget_memory": forget_memory,
    "past_tasks": past_tasks,
}

MEMORY_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save a fact, preference, or observation to persistent memory so you can recall it in future sessions. Use categories like 'user_pref', 'project', 'learned', 'shortcut'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Memory category (user_pref, project, learned, shortcut)"},
                    "content": {"type": "string", "description": "The fact or observation to remember"},
                },
                "required": ["category", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Search your saved memories. Use this at the start of a task to check if you already know something relevant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for in memories (substring match)"},
                    "category": {"type": "string", "description": "Filter by category"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_memory",
            "description": "Delete a memory by its ID. Use if the user says something you remembered is wrong or outdated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "integer", "description": "ID of the memory to delete"},
                },
                "required": ["memory_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "past_tasks",
            "description": "Review your recent task history — what you were asked to do, whether it succeeded, and how long it took.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "How many recent tasks to return (default 5)"},
                },
                "required": [],
            },
        },
    },
]
