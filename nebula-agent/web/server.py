"""Flask web server for the Nebula agent engine.

Serves a single-page chat UI and streams agent events over SSE.
Confirmations for risky tools are handled via a pending-approval queue:
the SSE stream emits `tool_awaiting_confirm`, the client posts to
/approve/<task_id> with yes/no, and the server passes it back to the
agent loop.
"""
from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from agent.events import run_task_events
from agent.memory import MemoryStore
from agent.models import ModelRouter

app = Flask(__name__, static_folder=None)
STATIC_DIR = Path(__file__).parent / "static"

_memory = MemoryStore()
_router = ModelRouter()
_pending: dict[str, queue.Queue] = {}


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route("/api/memory", methods=["GET"])
def api_memory():
    return jsonify(_memory.recall(limit=50))


@app.route("/api/memory/<int:memory_id>", methods=["DELETE"])
def api_forget(memory_id: int):
    ok = _memory.forget(memory_id)
    return jsonify({"deleted": ok})


@app.route("/api/history", methods=["GET"])
def api_history():
    return jsonify(_memory.recent_tasks(limit=20))


@app.route("/api/models", methods=["GET"])
def api_models():
    return jsonify(_router.list_available())


@app.route("/api/approve/<task_id>", methods=["POST"])
def api_approve(task_id: str):
    body = request.get_json() or {}
    allowed = bool(body.get("allowed"))
    if task_id in _pending:
        _pending[task_id].put(allowed)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "no pending confirmation"}), 404


@app.route("/api/chat", methods=["POST"])
def api_chat():
    body = request.get_json() or {}
    task = (body.get("task") or "").strip()
    model = body.get("model") or None
    auto_approve = bool(body.get("auto_approve"))
    if not task:
        return jsonify({"error": "task is required"}), 400

    task_id = uuid.uuid4().hex[:12]
    approval_q: queue.Queue = queue.Queue()
    _pending[task_id] = approval_q

    def confirm_fn(name: str, args: dict) -> bool:
        try:
            return bool(approval_q.get(timeout=300))
        except queue.Empty:
            return False

    def event_stream():
        yield f"data: {json.dumps({'type': 'task_id', 'task_id': task_id})}\n\n"
        try:
            for event in run_task_events(
                task, model=model, auto_approve=auto_approve,
                confirm_fn=confirm_fn, memory=_memory, router=_router,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            _pending.pop(task_id, None)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def start(host: str = "127.0.0.1", port: int = 5757) -> None:
    print(f"Nova web UI at http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)
