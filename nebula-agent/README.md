# Nebula Agent Engine — v0.7.0

Local-first agent engine for the planned Nebula Ubuntu · Agent Edition.
Runs entirely on your machine, powered by Ollama. No cloud, no telemetry.

## Install

### One-line install (recommended)

**Windows** (PowerShell):
```powershell
iwr -useb https://raw.githubusercontent.com/nebula-linux-os/Nebula-Linux/main/nebula-agent/install.ps1 | iex
```

**macOS / Linux** (bash):
```bash
curl -fsSL https://raw.githubusercontent.com/nebula-linux-os/Nebula-Linux/main/nebula-agent/install.sh | sh
```

Both scripts check for Python 3.10+ and Ollama, clone the repo, install
Python deps, and run first-run setup.

### Manual install

```bash
# 1. Install Ollama from https://ollama.com and pull a model
ollama pull qwen2.5:7b

# 2. Clone + install deps
git clone https://github.com/nebula-linux-os/Nebula-Linux.git
cd Nebula-Linux/nebula-agent
pip install -r requirements.txt

# 3. First-run setup (autostart, model check)
python install.py

# 4. Launch
python main.py --tray                # background daemon + tray icon
python main.py --web                 # foreground web UI at :5757
python main.py                       # interactive REPL
python main.py --voice "list files"  # CLI + spoken response
```

## What Nova can do (24 tools)

**Files:** `read_file`, `write_file`, `edit_file`, `list_dir`, `find_files`
**Shell / System:** `run_command`, `system_info`, `install_package`
**Apps & Web:** `open_app`, `open_url`, `web_search`, `fetch_page`, `fetch_json`
**Screen & Vision:** `take_screenshot`, `see_screen`, `describe_image`, `vision_info`
**Clipboard:** `read_clipboard`, `write_clipboard`
**Alerts:** `notify` (desktop notifications)
**Memory:** `save_memory`, `recall_memory`, `forget_memory`, `past_tasks`

Risky tools ask for confirmation before running (bypass with `--yes` or
the auto-approve checkbox in the web UI).

## Launch modes

| Mode | Command | When to use |
|------|---------|-------------|
| **Tray** | `python main.py --tray` | Always-on background daemon with a taskbar icon |
| **Web** | `python main.py --web` | Foreground web server at `http://127.0.0.1:5757` — voice, chat, memory, history, models tabs |
| **REPL** | `python main.py` | Terminal chat with `/memory`, `/history`, `/models`, `/forget N`, `/help` |
| **One-shot** | `python main.py "task"` | Fire-and-return for scripting; add `--voice` for spoken output |

## Multi-model routing

The router auto-picks the best installed model per task:

| Category | Triggered by | Prefers |
|----------|-------------|---------|
| `coding` | write, build, refactor, debug | codellama, qwen2.5-coder |
| `system` | install, service, disk, network | qwen2.5 |
| `reasoning` | explain, analyze, compare | llama3.1, qwen2.5:14b |
| `quick` | list, read, check, find | qwen2.5:3b, gemma |
| `general` | everything else | qwen2.5:7b |

Override with `--model <name>`. Add a model by editing `agent/models.py`.

## Vision

The agent can see screenshots and images. Pull any vision-capable Ollama
model — Nova auto-detects and uses the first one it finds:

```bash
ollama pull llama3.2-vision       # ~7.9 GB, best all-round
ollama pull moondream             # ~1.7 GB, lightweight
ollama pull llava                 # ~4.7 GB
```

The main planner model stays text-only. When the agent calls `see_screen`
or `describe_image`, Nova runs a separate one-shot request to the
vision model and returns the description to the planner — so vision
works on top of any base model.

Vision status appears in the sidebar (👁 badge). Set `NOVA_VISION_MODEL`
env var to force a specific one.

## Voice

| Where | Backend | How |
|-------|---------|-----|
| Web input | Browser Web Speech API | Toggle "Voice mode", click 🎤 to speak |
| Web output | Browser SpeechSynthesis | Assistant replies get spoken aloud |
| CLI output | pyttsx3 (offline, OS voices) | `python main.py --voice "your task"` |

## Autostart

Enable Nova to launch on login (system-tray mode):

- **Web UI:** toggle "Start on login" in the sidebar
- **CLI:** `python install.py` (interactive), or programmatically:
  ```python
  from agent import autostart
  autostart.enable()
  ```

Windows uses the Startup folder, Linux uses `~/.config/autostart/`,
macOS uses `~/Library/LaunchAgents/`.

## Updates

Nova checks GitHub Releases for a newer version on every web UI load. A
banner appears in the sidebar when an update is available. Check
manually:

```bash
python install.py --update
```

## Packaging (build a standalone binary)

```bash
pip install pyinstaller
python build.py             # produces dist/nova.exe (or dist/nova)
python build.py --onedir    # folder distribution — faster startup
```

## Data locations

| Path | Contents |
|------|----------|
| `~/.nebula-agent/memory.db` | SQLite (memories + task history) |
| `~/.nebula-agent/sessions/` | JSON transcripts of every task |

## Phase history

| Phase | Added |
|-------|-------|
| 0 | CLI PoC, 6 tools, confirmation gate |
| 1 | SQLite memory, REPL, streaming, session logs |
| 2 | Multi-model router, `system_info`, `find_files`, `edit_file` |
| 3 | Flask web UI, SSE streaming, chat/memory/history/models tabs |
| 4 | Desktop tools (`open_app`, `screenshot`, `clipboard`, `notify`, `web_search`), system tray |
| 5 | Voice input (browser Web Speech), voice output (browser TTS + CLI pyttsx3) |
| 6 | Packaging (PyInstaller build), autostart, self-update check, first-run installer |
| 7 | Vision — see_screen, describe_image, vision_info; auto-picks any installed multimodal Ollama model |
| 7.1 | Web reading — fetch_page (URL → readable text), fetch_json (URL → parsed JSON); one-line installers for Windows/Mac/Linux |
