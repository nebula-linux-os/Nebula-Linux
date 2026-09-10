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

C_CYAN=$'\033[36m'
C_YELLOW=$'\033[33m'
C_RED=$'\033[31m'
C_GREEN=$'\033[32m'
C_OFF=$'\033[0m'
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

# 4. Dependencies
step "Installing Python dependencies..."
(cd "$AGENT_DIR" && "$PYTHON" -m pip install --quiet --disable-pip-version-check -r requirements.txt)
echo "    Dependencies installed."

# 5. First-run setup
step "Running first-run setup..."
(cd "$AGENT_DIR" && "$PYTHON" install.py)

echo
ok "=== Setup complete ==="
echo
echo "Launch Nova:"
echo "  cd \"$AGENT_DIR\""
echo "  $PYTHON main.py --tray     # background daemon + tray icon"
echo "  $PYTHON main.py --web      # foreground web UI at :5757"
echo "  $PYTHON main.py            # interactive REPL"
echo
