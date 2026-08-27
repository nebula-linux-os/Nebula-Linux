# Nebula Agent Engine — Phase 2

Local-first agent engine for the planned Nebula Ubuntu · Agent Edition.

## How it works

```
your task (text)
   -> router classifies the task (coding / system / reasoning / quick)
   -> picks the best installed model that fits in RAM
   -> planner streams it + tools + saved memories to Ollama
   -> model returns tool_calls (never runs anything itself)
   -> executor validates + runs each one (confirming risky ones)
   -> result goes back to the model
   -> repeat until the model reports the task done
   -> session transcript + task outcome saved to ~/.nebula-agent/
```

## Setup

1. Install [Ollama](https://ollama.com) and make sure it's running.
2. Pull one or more tool-calling models:
   ```bash
   ollama pull qwen2.5:7b
   ```
   The router auto-picks the best model per task. Pull more for better routing:
   ```bash
   ollama pull qwen2.5:3b       # fast, for simple lookups
   ollama pull codellama:7b      # coding tasks
   ollama pull qwen2.5:14b       # complex reasoning (needs ~10 GB RAM)
   ```
3. Install Python deps:
   ```bash
   pip install -r requirements.txt
   ```

## Run it

**Single-shot** (auto-routed):
```bash
python main.py "create a python web server in ./demo"
python main.py "what OS am I running?"
```

**Force a specific model:**
```bash
python main.py --model codellama:7b "refactor this function"
```

**Interactive mode** (omit the task):
```bash
python main.py
```

### REPL commands

| Command | What it does |
|---------|-------------|
| `/memory` | List all saved memories |
| `/history` | Show recent task history with model used |
| `/models` | Show available models, routing profiles, and RAM fit |
| `/forget N` | Delete a memory by ID |
| `/help` | Show available commands |
| `quit` | Exit |

## Tools (13 total)

| Tool | Risk | Description |
|------|------|-------------|
| `run_command` | risky | Run a shell command |
| `write_file` | risky | Create or overwrite a file |
| `edit_file` | risky | Replace a specific section of a file (safer than full rewrite) |
| `install_package` | risky | Install via winget/pacman/apt/brew |
| `read_file` | safe | Read a file's contents |
| `list_dir` | safe | List directory contents |
| `find_files` | safe | Recursive glob search (skips .git, node_modules, etc.) |
| `system_info` | safe | OS, RAM, disk, CPU, installed tools |
| `open_url` | safe | Open a URL in the default browser |
| `save_memory` | safe | Save a fact to persistent memory |
| `recall_memory` | safe | Search saved memories |
| `forget_memory` | safe | Delete a memory by ID |
| `past_tasks` | safe | Review recent task history |

Risky tools ask for `[y/N]` confirmation unless you pass `--yes`.

## Multi-model routing

The router classifies each task into a category and picks the best
model that's (a) installed locally and (b) fits in ~80% of system RAM.

| Category | Triggered by | Best models |
|----------|-------------|-------------|
| `coding` | create, build, code, refactor, debug | codellama:7b, qwen2.5:7b/14b |
| `system` | install, update, service, disk, network | qwen2.5:7b/14b |
| `reasoning` | explain, why, analyze, compare | llama3.1:8b, qwen2.5:14b |
| `quick` | list, show, read, check, find | qwen2.5:3b |
| `general` | everything else | qwen2.5:7b |

Override with `--model <name>` to force a specific model.

## Data locations

| Path | Contents |
|------|----------|
| `~/.nebula-agent/memory.db` | SQLite database (memories + task history) |
| `~/.nebula-agent/sessions/` | JSON session transcripts |

## Phase history

| Phase | What it added |
|-------|--------------|
| 0 | CLI proof-of-concept, 6 tools, confirmation gate, verification |
| 1 | Persistent memory (SQLite), interactive REPL, streaming, session logging |
| 2 | Multi-model routing, expanded tools (system_info, find_files, edit_file) |
