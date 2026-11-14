"""Flask web server for the Nebula agent engine.

Serves a single-page chat UI and streams agent events over SSE.
Confirmations for risky tools are handled via a pending-approval queue:
the SSE stream emits `tool_awaiting_confirm`, the client posts to
/approve/<task_id> with yes/no, and the server passes it back to the
agent loop.
"""
from __future__ import annotations

import itertools
import json
import os
import queue
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from agent import autostart
from agent.events import run_task_events
from agent.memory import MemoryStore
from agent.models import ModelRouter
from agent.updater import check_for_update
from agent.version import __version__
from agent.vision import VISION_MODEL_CANDIDATES, pick_vision_model
from agent.rag import pick_embed_model as pick_rag_model
from agent.tools_rag import list_collections as rag_list_collections

app = Flask(__name__, static_folder=None)
STATIC_DIR = Path(__file__).parent / "static"

_memory = MemoryStore()
_router = ModelRouter()
_pending: dict[str, queue.Queue] = {}

# Hostnames the UI may be reached under. Anything else is rejected, which
# defeats DNS rebinding (attacker.example resolving to 127.0.0.1 would
# otherwise be "same-origin" with this server and could drive /api/chat).
# Extra names (e.g. a LAN IP when started with --host 0.0.0.0) can be
# added via NOVA_ALLOWED_HOSTS=host1,host2.
_ALLOWED_HOSTS: set[str] = {"127.0.0.1", "localhost", "::1"}
_ALLOWED_HOSTS.update(
    h.strip().lower() for h in os.environ.get("NOVA_ALLOWED_HOSTS", "").split(",") if h.strip()
)


def _hostname(value: str) -> str:
    """Hostname part of a Host header or Origin URL, lowercased, no port."""
    if "://" not in value:
        value = "//" + value
    return (urlsplit(value).hostname or "").lower()


@app.before_request
def _check_origin():
    if _hostname(request.host) not in _ALLOWED_HOSTS:
        abort(403)
    # Browsers send Origin on cross-site requests and on every POST/DELETE.
    # A foreign Origin means another site is trying to use this API.
    origin = request.headers.get("Origin")
    if origin and origin != "null" and _hostname(origin) not in _ALLOWED_HOSTS:
        abort(403)
    if origin == "null" and request.method not in ("GET", "HEAD"):
        abort(403)


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


@app.route("/api/status", methods=["GET"])
def api_status():
    vision = pick_vision_model()
    embed = pick_rag_model()
    return jsonify({
        "version": __version__,
        "autostart": autostart.is_enabled(),
        "vision_model": vision,
        "vision_candidates": VISION_MODEL_CANDIDATES,
        "embed_model": embed,
    })


@app.route("/api/rag/collections", methods=["GET"])
def api_rag_collections():
    return jsonify(rag_list_collections())


@app.route("/api/autostart", methods=["POST"])
def api_autostart():
    body = request.get_json() or {}
    if body.get("enabled"):
        return jsonify(autostart.enable())
    return jsonify(autostart.disable())


@app.route("/api/update-check", methods=["GET"])
def api_update_check():
    return jsonify(check_for_update())


@app.route("/api/approve/<task_id>", methods=["POST"])
def api_approve(task_id: str):
    body = request.get_json() or {}
    allowed = bool(body.get("allowed"))
    confirm_id = body.get("confirm_id")
    if not isinstance(confirm_id, int):
        return jsonify({"ok": False, "error": "confirm_id is required"}), 400
    if task_id in _pending:
        _pending[task_id].put((confirm_id, allowed))
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
    # Each confirmation prompt gets its own id so a late click on a prompt
    # that already timed out can't approve the *next* risky tool.
    confirm_ids = itertools.count(1)
    current = {"id": 0}

    def confirm_fn(name: str, args: dict) -> bool:
        deadline = time.monotonic() + 300
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            try:
                cid, allowed = approval_q.get(timeout=remaining)
            except queue.Empty:
                return False
            if cid == current["id"]:
                return bool(allowed)
            # stale answer for an earlier prompt: ignore it

    def event_stream():
        yield f"data: {json.dumps({'type': 'task_id', 'task_id': task_id})}\n\n"
        try:
            for event in run_task_events(
                task, model=model, auto_approve=auto_approve,
                confirm_fn=confirm_fn, memory=_memory, router=_router,
            ):
                if event.get("type") == "tool_awaiting_confirm":
                    current["id"] = next(confirm_ids)
                    event = {**event, "confirm_id": current["id"]}
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
    if host not in ("0.0.0.0", "::", ""):
        _ALLOWED_HOSTS.add(_hostname(host if ":" not in host else f"[{host}]"))
    print(f"Nova web UI at http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)
