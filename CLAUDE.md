# Nebula Linux — project context for Claude

This repo holds **two related projects**:

1. **Nebula Linux** — an Arch-based Linux distribution (edition: `Arch · Dank Edition`, using [niri](https://github.com/YaLTeR/niri) + [DankMaterialShell](https://github.com/AvengeMedia/DankMaterialShell)). Currently at **Beta 1.0**, ISO shipped on SourceForge.
2. **Nebula Agent Engine** (`nebula-agent/`) — a local-first LLM agent framework powered by Ollama, intended to eventually ship as the "Agent Edition" (planned Ubuntu-based distro). Currently at **v0.6.0**, six-phase roadmap complete, not yet tagged.

The user is a solo developer building both. Bias toward practical, ship-oriented advice. They test on Windows 11 + VirtualBox, deploy via Docker builds. No corporate constraints, no team — this is a personal project.

---

## Repo layout

```
D:\Project\LinuX Distro\
├── docs/                       # Website — GitHub Pages, live
│   ├── index.html              # Landing page (Arch-only, no Debian mentions)
│   ├── docs.html               # Install guide + keybinds
│   └── script.js
├── nebula-agent/               # The agent engine (v0.6.0)
│   ├── main.py                 # CLI entry: --tray | --web | --voice | REPL | one-shot
│   ├── install.py              # First-run installer (Ollama check, autostart, model pull)
│   ├── build.py                # PyInstaller build script
│   ├── tray.py                 # System tray launcher
│   ├── requirements.txt
│   ├── agent/
│   │   ├── planner.py          # CLI Ollama loop (streaming, memory injection)
│   │   ├── events.py           # Event-based loop (used by web UI)
│   │   ├── executor.py         # Confirmation gate + post-action verify
│   │   ├── tools.py            # 6 core tools + RISKY_TOOLS set
│   │   ├── tools_extended.py   # system_info, find_files, edit_file
│   │   ├── tools_desktop.py    # open_app, screenshot, clipboard, notify, web_search
│   │   ├── memory_tools.py     # save/recall/forget/past_tasks tools
│   │   ├── memory.py           # SQLite store (thread-safe via lock + check_same_thread=False)
│   │   ├── session.py          # JSON session transcripts
│   │   ├── models.py           # ModelRouter + task classifier
│   │   ├── voice.py            # pyttsx3 TTS (optional)
│   │   ├── autostart.py        # Cross-platform login autostart
│   │   ├── updater.py          # GitHub Releases API check
│   │   └── version.py          # Single source of truth for version
│   └── web/
│       ├── server.py           # Flask + SSE streaming
│       └── static/             # index.html, style.css, app.js
├── profile/                    # archiso profile for building the Arch ISO
├── docker_build.sh             # Docker-based ISO build entry
├── Dockerfile
├── .gitattributes              # * text=auto eol=lf (CRITICAL — see below)
└── CLAUDE.md                   # ← this file
```

Untracked in repo (deliberately, decide later): `Wallpaper/`, `assets/`, `graphify-out/`.

---

## Current state

### Nebula Linux (distro)
- Beta 1.0 ISO on SourceForge, download link is in `docs/index.html`.
- Website has been stripped of all dual-edition (Debian/KDE) framing — Arch-only. **Do not re-introduce Debian references** on the website.
- The old Debian/KDE work is parked on branch `Debian_Edition` with a stash `debian-edition-theming-wip`. User decided to focus on Arch only.
- Path to stable 1.0: real-hardware testing, installer polish, curated defaults, docs (see todo in memory).

### Nebula Agent Engine (v0.6.0)
- **All 6 phases done** and pushed to `main`:
  - Phase 0: CLI PoC + 6 tools + confirmation gate
  - Phase 1: SQLite memory + REPL + streaming + session logs
  - Phase 2: Multi-model router + `system_info` / `find_files` / `edit_file`
  - Phase 3: Flask web UI + SSE streaming + tabs (Chat/Memory/History/Models)
  - Phase 4: Desktop tools (`open_app`, screenshot, clipboard, notify, `web_search`) + system tray
  - Phase 5: Voice input (browser Web Speech) + output (SpeechSynthesis + pyttsx3)
  - Phase 6: PyInstaller build + autostart + self-update + first-run installer
- **19 tools total.** 6 are marked `RISKY_TOOLS` and prompt for `[y/N]` confirmation.
- **Not yet released** — needs `git tag v0.6.0 && git push --tags` + a GitHub Release for the updater to have something to compare against.
- Verified working on the user's Windows machine: screenshot (Pillow), clipboard read, DDG web search, tool-calling with `gemma4:e2b` model.

### Website
- Live on GitHub Pages at the repo default URL.
- No donation button yet — user is considering Ko-fi or GitHub Sponsors (NOT Patreon).
- No custom domain yet — user is waiting until public beta gets real users.

---

## Non-obvious conventions and gotchas

1. **Line endings — CRITICAL.** `.gitattributes` enforces `* text=auto eol=lf`. On Windows, `core.autocrlf=true` will silently break shell scripts (`docker_build.sh` etc.) inside Docker builds. If you ever touch shell scripts, verify LF endings.

2. **Docker mount paths and spaces.** The repo path `D:\Project\LinuX Distro` has a space. Docker `-v` bind mounts silently fail with that space on Windows. Workaround is `docker cp` from the stopped container.

3. **matugen quirks** (only relevant if theming work resumes):
   - Requires `prefer = "closest-to-fallback"` + `fallback_color` in `config.toml` or it drops into an interactive TUI and hangs non-interactive callers.
   - `{{scheme}}` is NOT a valid template keyword. Using it causes `ResolveError` that aborts the whole render.
   - The v4.1.0 binary needs GLIBC ≥ 2.39 — won't run in `debian:bookworm` (glibc 2.36) build containers.

4. **Agent engine — model support.** Not every Ollama model supports tool calling. Confirmed working: `qwen2.5:7b`, `llama3.1:8b`. User has `gemma4:e2b` installed and it works for basic tool calls. If a model just returns text with no `[step 1]` line, it can't do tool calls.

5. **Agent engine — memory store threading.** `sqlite3.connect(..., check_same_thread=False)` + a module-level `threading.Lock()` around writes. Flask is threaded; do NOT remove the lock.

6. **Agent engine — session cwd.** When running the agent's own tools like `run_command`, they execute on the user's real machine, not a sandbox. Confirmation gate is the only guard.

7. **Website — no Debian.** The site is deliberately Arch-only. Don't add Debian screenshots, comparisons, or "which edition" copy. That was removed on purpose.

8. **Commit style.** Look at recent `git log`. Concise summary line, blank line, prose body explaining why. Co-authored-by trailer is expected on Claude-assisted commits.

---

## Common tasks

### Build the ISO
```bash
docker build -t nebula-build .
docker run --rm -it -v "//d/Project/LinuX Distro:/build" nebula-build
# Or use docker_build.sh from inside the container
```

### Run the agent engine
```bash
cd nebula-agent
pip install -r requirements.txt
python install.py                  # First-run setup
python main.py --tray              # Background daemon + tray icon
python main.py --web               # Foreground web UI at :5757
python main.py "task"              # One-shot CLI
python main.py                     # Interactive REPL
```

### Build the standalone agent binary
```bash
cd nebula-agent
pip install pyinstaller
python build.py                    # dist/nova.exe (single file)
```

### Website changes
Just edit files under `docs/`. GitHub Pages auto-deploys on push to `main`.

---

## Open work (as of 2026-09-09)

**Agent engine — ship v0.6.0**
- Tag and publish `v0.6.0` GitHub release
- Run `python build.py` end-to-end at least once, verify the produced binary works
- Add more models to `agent/models.py` if user pulls new ones

**Nebula Linux (distro) — path to stable 1.0**
- Set up somewhere to receive Beta 1.0 bug reports (GitHub Issues templates, Discord, or similar)
- Bare-metal testing (UEFI + BIOS, NVIDIA + Intel/AMD)
- Installer polish (NVIDIA auto-config, dual-boot detection, progress %)
- Curate default apps and wallpapers
- Screenshots for install docs (currently text-only)

**Website**
- Donation section (Ko-fi or GitHub Sponsors)
- Landing section for Agent Edition once it becomes real

**Housekeeping**
- Decide fate of untracked `Wallpaper/`, `assets/`, `graphify-out/` — commit, move, or `.gitignore`
- Archive or delete `Debian_Edition` branch and its stash
- Add top-level `LICENSE` if missing

---

## Communication style the user prefers

- **Terse.** Direct answers, no preamble like "I'll help you with…". They'll ask for more detail if they want it.
- **Honest recommendations over hedging.** When asked "should I buy this domain / use Patreon / build feature X" — pick a side, give one reason, one counter-signal.
- **Ship first, polish later.** Build the smallest working thing, verify it, then iterate.
- **Commit style:** don't commit unless asked. When committing, follow the repo's `git log` style.
- **No emojis** in code, commits, or writing unless the user asks.
- **Do not use `run_command` or destructive git operations** without confirmation — the agent-engine conventions carry over here too.
