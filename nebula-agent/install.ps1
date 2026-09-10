<#
.SYNOPSIS
    One-line installer for Nova (Nebula Agent Engine) on Windows.

.DESCRIPTION
    Checks for Python + Ollama, clones the repo (or uses the local copy),
    installs Python deps, and runs first-run setup.

.EXAMPLE
    iwr -useb https://raw.githubusercontent.com/nebula-linux-os/Nebula-Linux/main/nebula-agent/install.ps1 | iex

.EXAMPLE
    # Local (from a cloned repo):
    .\install.ps1
#>
$ErrorActionPreference = "Stop"

$Repo    = "nebula-linux-os/Nebula-Linux"
$Branch  = "main"
$AppName = "nebula-agent"
$InstallDir = Join-Path $env:LOCALAPPDATA "NebulaAgent"

function Write-Step   { param($m) Write-Host "[+] $m" -ForegroundColor Cyan }
function Write-Warn   { param($m) Write-Host "[!] $m" -ForegroundColor Yellow }
function Write-ErrMsg { param($m) Write-Host "[x] $m" -ForegroundColor Red }

Write-Host ""
Write-Host "=== Nova · Nebula Agent Engine installer ===" -ForegroundColor White
Write-Host ""

# 1. Python check
Write-Step "Checking Python..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-ErrMsg "Python not found on PATH."
    Write-Host "    Install Python 3.10+ from https://www.python.org/downloads/"
    Write-Host "    (Tick 'Add Python to PATH' during install)"
    exit 1
}
$version = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "    Python $version at $($python.Source)"

# 2. Ollama check
Write-Step "Checking Ollama..."
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Warn "Ollama not found."
    $reply = Read-Host "    Open the Ollama download page in your browser? [Y/n]"
    if ($reply -ne "n" -and $reply -ne "N") {
        Start-Process "https://ollama.com/download/windows"
    }
    Write-Host "    Install Ollama, then re-run this installer."
    exit 1
}
Write-Host "    Ollama found at $($ollama.Source)"

# 3. Source code
Write-Step "Preparing $AppName source..."
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$sourceMain = Join-Path $scriptDir "main.py"

if (Test-Path $sourceMain) {
    Write-Host "    Using local copy at $scriptDir"
    $agentDir = $scriptDir
} else {
    if (Test-Path $InstallDir) {
        Write-Host "    Updating existing install at $InstallDir"
        Push-Location $InstallDir
        try { git pull --ff-only 2>&1 | Out-Null } catch { Write-Warn "git pull failed; continuing with local copy" }
        Pop-Location
    } else {
        Write-Host "    Cloning to $InstallDir"
        $git = Get-Command git -ErrorAction SilentlyContinue
        if (-not $git) {
            Write-ErrMsg "git not found — install from https://git-scm.com/ or download the repo as ZIP."
            exit 1
        }
        $parent = Split-Path $InstallDir
        if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        & $git.Source clone --depth 1 --branch $Branch "https://github.com/$Repo.git" $InstallDir | Out-Null
    }
    $agentDir = Join-Path $InstallDir $AppName
}

# 4. Dependencies
Write-Step "Installing Python dependencies..."
Push-Location $agentDir
try {
    & $python.Source -m pip install --quiet --disable-pip-version-check -r requirements.txt
    Write-Host "    Dependencies installed."
} finally {
    Pop-Location
}

# 5. First-run setup
Write-Step "Running first-run setup..."
Push-Location $agentDir
try {
    & $python.Source install.py
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Launch Nova:"
Write-Host "  cd `"$agentDir`""
Write-Host "  python main.py --tray     # background daemon + tray icon"
Write-Host "  python main.py --web      # foreground web UI at :5757"
Write-Host "  python main.py            # interactive REPL"
Write-Host ""
