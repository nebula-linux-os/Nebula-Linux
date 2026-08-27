# Nebula Agent Engine — Phase 5

Local-first agent engine for the planned Nebula Ubuntu · Agent Edition.
Runs entirely on your machine, powered by Ollama. No cloud, no telemetry.

## Quickstart

```bash
# 1. Install Ollama and pull a tool-calling model
ollama pull qwen2.5:7b

# 2. Install deps
pip install -r requirements.txt

# 3. Launch how you want:
python main.py --tray                # background daemon + tray icon
python main.py --web                 # web UI (foreground) — has voice toggle
python main.py                       # interactive CLI (REPL)
python main.py --voice "list files"  # CLI with spoken responses
```

## What Nova can do (19 tools)

**Files:** `read_file`, `write_file`, `edit_file`, `list_dir`, `find_files`
**Shell / System:** `run_command`, `system_info`, `install_package`
**Apps & Web:** `open_app`, `open_url`, `web_search`
**Screen & Clipboard:** `take_screenshot`, `read_clipboard`, `write_clipboard`
**Alerts:** `notify` (desktop notifications)
**Memory:** `save_memory`, `recall_memory`, `forget_memory`, `past_tasks`

Risky tools (`run_command`, `write_file`, `edit_file`, `install_package`,
`open_app`, `write_clipboard`) ask for confirmation before running.

## Modes

| Mode | Command | When to use |
|------|---------|-------------|
| **Tray** | `python main.py --tray` | Always-on background daemon with a taskbar icon. Right-click the icon → Open Nova to bring up the web UI. |
| **Web** | `python main.py --web` | Foreground web server at `http://127.0.0.1:5757`. Best for testing. |
| **REPL** | `python main.py` | Terminal chat with `/memory`, `/history`, `/models`, `/forget N`, `/help` commands. |
| **One-shot** | `python main.py "<task>"` | Fire-and-return for scripting. |

## Multi-model routing

The router auto-picks the best installed model per task:

| Category | Triggered by | Prefers |
|----------|-------------|---------|
| `coding` | write, build, refactor, debug | codellama, qwen2.5-coder |
| `system` | install, service, disk, network | qwen2.5 |
| `reasoning` | explain, analyze, compare | llama3.1, qwen2.5:14b |
| `quick` | list, read, check, find | qwen2.5:3b, gemma |
| `general` | everything else | qwen2.5:7b |

Override with `--model <name>`. Add a model to the router by editing
`agent/models.py`.

## Data locations

| Path | Contents |
|------|----------|
| `~/.nebula-agent/memory.db` | SQLite (memories + task history) |
| `~/.nebula-agent/sessions/` | JSON transcripts of every task |

## Web UI

- Streaming responses (token-by-token)
- Tool calls rendered as inline cards with pending → ok/error state
- Click-to-confirm risky actions
- Tabs: Chat, Memory, History, Models
- **Voice mode** — checkbox in sidebar activates a mic button (Web Speech
  API for input) and speaks responses aloud (SpeechSynthesis API for
  output). Works in Chrome/Edge. Zero server-side deps needed.

## Voice

| Where | Backend | How |
|-------|---------|-----|
| Web UI input | Browser Web Speech API | Toggle "Voice mode" in sidebar, click 🎤 to speak |
| Web UI output | Browser SpeechSynthesis | Auto-speaks each assistant reply when voice mode is on |
| CLI output | pyttsx3 (offline, OS voices) | `python main.py --voice "your task"` |

## Phase history

| Phase | Added |
|-------|-------|
| 0 | CLI PoC, 6 tools, confirmation gate |
| 1 | SQLite memory, REPL, streaming, session logs |
| 2 | Multi-model router, system_info, find_files, edit_file |
| 3 | Flask web UI, SSE streaming, chat/memory/history/models tabs |
| 4 | Desktop tools (open_app, screenshot, clipboard, notify, web_search), system tray |
| 5 | Voice input (browser Web Speech), voice output (browser TTS + CLI pyttsx3) |
