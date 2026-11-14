#!/usr/bin/env bash
# One-line installer for Nova (Nebula Agent Engine) on macOS and Linux.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/nebula-linux-os/Nebula-Linux/main/nebula-agent/install.sh | sh
#
# Or, from a cloned repo:
#   ./install.sh

set -eu

REPO="nebula-linux-os/Nebula-Linux"
BRANCH="main"
APP_NAME="nebula-agent"

case "$(uname -s)" in
    Darwin*) INSTALL_DIR="$HOME/Library/Application Support/NebulaAgent" ;;
    Linux*)  INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/nebula-agent" ;;
    *)       echo "[x] Unsupported OS: $(uname -s)"; exit 1 ;;
esac

# POSIX-safe colours: the one-liner pipes this into `sh` (dash on Debian),
# which doesn't understand bash's $'...' quoting.
C_CYAN=$(printf '\033[36m')
C_YELLOW=$(printf '\033[33m')
C_RED=$(printf '\033[31m')
C_GREEN=$(printf '\033[32m')
C_OFF=$(printf '\033[0m')
step()   { printf "%s[+]%s %s\n"  "$C_CYAN"   "$C_OFF" "$1"; }
warn()   { printf "%s[!]%s %s\n"  "$C_YELLOW" "$C_OFF" "$1"; }
errmsg() { printf "%s[x]%s %s\n"  "$C_RED"    "$C_OFF" "$1"; }
ok()     { printf "%s[+]%s %s\n"  "$C_GREEN"  "$C_OFF" "$1"; }

echo
echo "=== Nova · Nebula Agent Engine installer ==="
echo

# 1. Python
step "Checking Python..."
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"; break
    fi
done
if [ -z "$PYTHON" ]; then
    errmsg "Python not found."
    case "$(uname -s)" in
        Darwin*) echo "    Install: brew install python  (or from https://www.python.org/downloads/)" ;;
        Linux*)  echo "    Install with your package manager, e.g. sudo apt install python3 python3-pip" ;;
    esac
    exit 1
fi
VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "    Python $VERSION at $(command -v "$PYTHON")"

# 2. Ollama
step "Checking Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
    warn "Ollama not found."
    case "$(uname -s)" in
        Darwin*) echo "    Install: brew install ollama  (or download from https://ollama.com/download/mac)" ;;
        Linux*)  echo "    Install: curl -fsSL https://ollama.com/install.sh | sh" ;;
    esac
    echo "    Install Ollama, start it (ollama serve), then re-run this installer."
    exit 1
fi
echo "    Ollama at $(command -v ollama)"

# 3. Source code
step "Preparing $APP_NAME source..."
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || SCRIPT_DIR=""
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/main.py" ]; then
    echo "    Using local copy at $SCRIPT_DIR"
    AGENT_DIR="$SCRIPT_DIR"
else
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "    Updating existing install at $INSTALL_DIR"
        (cd "$INSTALL_DIR" && git pull --ff-only >/dev/null 2>&1) || warn "git pull failed; continuing"
    else
        if ! command -v git >/dev/null 2>&1; then
            errmsg "git not found — install with your package manager."
            exit 1
        fi
        echo "    Cloning to $INSTALL_DIR"
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" "$INSTALL_DIR" >/dev/null 2>&1
    fi
    AGENT_DIR="$INSTALL_DIR/$APP_NAME"
fi

# 4. Dependencies — into a private venv. Arch, Debian 12+, Ubuntu 23.04+
# and Homebrew Python refuse system-wide pip installs (PEP 668,
# "externally-managed-environment").
step "Installing Python dependencies..."
VENV_DIR="$AGENT_DIR/.venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "    Creating virtual environment at $VENV_DIR"
    if ! "$PYTHON" -m venv "$VENV_DIR"; then
        rm -rf "$VENV_DIR"
        errmsg "Could not create a Python virtual environment."
        case "$(uname -s)" in
            Linux*) echo "    On Debian/Ubuntu: sudo apt install python3-venv  — then re-run." ;;
        esac
        exit 1
    fi
fi
VPY="$VENV_DIR/bin/python"
"$VPY" -m pip install --quiet --disable-pip-version-check --upgrade pip
(cd "$AGENT_DIR" && "$VPY" -m pip install --quiet --disable-pip-version-check -r requirements.txt)
echo "    Dependencies installed."

# 5. First-run setup. When run as `curl ... | sh`, stdin is this script,
# so install.py's prompts would swallow the rest of it — read from the
# terminal instead, or accept defaults if there isn't one.
step "Running first-run setup..."
if [ -t 0 ]; then
    (cd "$AGENT_DIR" && "$VPY" install.py)
elif (: </dev/tty) 2>/dev/null; then
    (cd "$AGENT_DIR" && "$VPY" install.py </dev/tty)
else
    (cd "$AGENT_DIR" && "$VPY" install.py </dev/null)
fi

echo
ok "=== Setup complete ==="
echo
echo "Launch Nova:"
echo "  cd \"$AGENT_DIR\""
echo "  .venv/bin/python main.py --tray     # background daemon + tray icon"
echo "  .venv/bin/python main.py --web      # foreground web UI at :5757"
echo "  .venv/bin/python main.py            # interactive REPL"
echo
