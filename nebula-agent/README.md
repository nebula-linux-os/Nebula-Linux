# Nebula Agent Engine — v0.6.0

Local-first agent engine for the planned Nebula Ubuntu · Agent Edition.
Runs entirely on your machine, powered by Ollama. No cloud, no telemetry.

## Quickstart

```bash
# 1. Install Ollama and pull a tool-calling model
ollama pull qwen2.5:7b

# 2. Install Python deps
pip install -r requirements.txt

# 3. First-run setup (checks Ollama, pulls model, enables autostart)
python install.py

# 4. Launch how you want:
python main.py --tray                # background daemon + tray icon
python main.py --web                 # foreground web UI (voice available)
python main.py                       # interactive REPL
python main.py --voice "list files"  # CLI + spoken response
```

## What Nova can do (19 tools)

**Files:** `read_file`, `write_file`, `edit_file`, `list_dir`, `find_files`
**Shell / System:** `run_command`, `system_info`, `install_package`
**Apps & Web:** `open_app`, `open_url`, `web_search`
**Screen & Clipboard:** `take_screenshot`, `read_clipboard`, `write_clipboard`
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
