# Changelog

All notable changes to the Nebula Agent Engine. Dates use the commit
day; version numbers follow SemVer.

## [0.8.0] — 2026-09-10

Local RAG. The agent can index folders of code or docs and answer
questions grounded in the actual content.

**Added**
- `agent/rag.py` — SQLite-backed RAG store at `~/.nebula-agent/rag.db`
  with three tables (collections / files / chunks). Cosine similarity
  in numpy at query time. No FAISS, no Chroma, no LangChain.
- Five new tools: `index_folder`, `search_docs`, `list_collections`,
  `forget_collection`, `rag_info`.
- Auto-detects an installed embedding model — `nomic-embed-text`
  preferred, then `mxbai-embed-large`, `all-minilm`, `snowflake-arctic-embed`.
- Web UI sidebar shows a 📚 badge for embed model status.
- `/api/rag/collections` endpoint.
- `numpy>=1.24` added to requirements.

**Changed**
- `forget_collection` is a RISKY_TOOL (destructive).
- Total tool count: 29 (was 24).

## [0.7.1] — 2026-09-10

Web reading + one-line installers for Windows/macOS/Linux.

**Added**
- `fetch_page(url)` — HTTP GET, strip scripts/style/nav, extract
  readable text, capped at 12k chars.
- `fetch_json(url)` — GET a JSON API and parse.
- `install.ps1` — Windows PowerShell one-liner installer.
- `install.sh` — macOS + Linux one-liner installer.
- Both installers detect Python, detect Ollama, clone repo to a
  per-OS user data directory, install deps, run first-run setup.

## [0.7.0] — 2026-09-10

Vision. The agent can see screenshots and image files.

**Added**
- Three new tools: `see_screen` (capture desktop + describe),
  `describe_image` (any image file), `vision_info` (probe available
  vision model).
- `agent/vision.py` — auto-picks any installed multimodal Ollama
  model (llama3.2-vision, qwen2-vl, gemma3, moondream, llava…).
- Primary planner model stays text-only; vision runs as a sub-request
  via `/api/generate`.
- `NOVA_VISION_MODEL` env var to force a specific model.
- Web UI sidebar shows a 👁 badge for vision model status.

## [0.6.0] — 2026-08-28

Packaging + autostart + self-update + first-run installer.

**Added**
- `install.py` — interactive first-run setup (Ollama check, offer
  model pull, enable autostart, all idempotent).
- `build.py` — PyInstaller wrapper. Produces single-file or folder
  standalone binary.
- `agent/autostart.py` — cross-platform login autostart (Startup
  folder on Windows, `~/.config/autostart` on Linux, LaunchAgents
  on macOS).
- `agent/updater.py` — GitHub Releases API check.
- `agent/version.py` — single source of truth.
- Web UI: "Start on login" checkbox + version display + update banner.

## Phases 4–5 — 2026-08-28

**Added** in v0.5.x work:
- Six desktop tools: `open_app`, `take_screenshot`, `read_clipboard`,
  `write_clipboard`, `notify` (native toast/osascript/notify-send),
  `web_search` (DuckDuckGo Instant Answer).
- System tray (pystray) — background daemon with "Open Nova" and
  "Quit" menu items.
- Voice input (browser Web Speech API) and voice output (browser
  SpeechSynthesis + CLI pyttsx3).
- Explicit tool-selection guidance in the system prompt ("open <app>"
  → open_app, not run_command).

## Phases 1–3 — 2026-08-27

Foundation: memory, routing, streaming, and the web UI.

**Added**
- Persistent memory (SQLite) — `save_memory`, `recall_memory`,
  `forget_memory`, `past_tasks` tools. Relevant memories auto-injected
  into the system prompt.
- Interactive REPL mode with `/memory`, `/history`, `/models`, `/help`.
- Streaming Ollama output — tokens appear as the model generates.
- Session logs (JSON transcripts under `~/.nebula-agent/sessions/`).
- Multi-model router — classifies each task (coding/system/reasoning/
  quick/general) and picks the best installed model that fits in RAM.
- Three new tools: `system_info`, `find_files`, `edit_file`.
- Flask web UI with SSE streaming (`/api/chat`).
- Chat / Memory / History / Models tabs.
- Click-to-confirm risky tool gate in the browser.

## Phase 0 — 2026-08-27

Proof of concept. Standalone CLI, 6 tools, confirmation gate,
post-action verification, up to 12 planner steps.
