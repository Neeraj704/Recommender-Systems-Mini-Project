#!/usr/bin/env bash
# ==============================================================================
# 1-Click All-in-One Launcher for Spotify Music Recommendation System
# Automatically creates virtualenv, installs dependencies, and starts server.
# ==============================================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "🎵 Spotify Music Recommendation System — 1-Click Launcher"
echo "=========================================================="

# 1. Detect Python
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "❌ Error: Python is not installed or not in PATH."
    echo "Please install Python 3.9+ from https://www.python.org/"
    exit 1
fi

# 2. Check / Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment in .venv..."
    $PY_CMD -m venv .venv
    echo "✅ Virtual environment created."
fi

# Determine python and pip executables
VENV_PY=".venv/bin/python"
VENV_PIP=".venv/bin/pip"

# Fallback for Windows Git Bash / MSYS if .venv/Scripts exists
if [ -f ".venv/Scripts/python.exe" ]; then
    VENV_PY=".venv/Scripts/python.exe"
    VENV_PIP=".venv/Scripts/pip.exe"
fi

# 3. Verify / Auto-Install Dependencies
if ! $VENV_PY -c "import starlette, uvicorn, sklearn, pandas, numpy" &>/dev/null; then
    echo "⏳ Installing required dependencies from requirements.txt (first run only)..."
    $VENV_PIP install --upgrade pip
    $VENV_PIP install -r requirements.txt
    echo "✅ Dependencies installed successfully!"
fi

# 4. Auto-open browser in background after server boots
(
    sleep 2
    URL="http://localhost:8000"
    if command -v xdg-open &>/dev/null; then
        xdg-open "$URL" &>/dev/null || true
    elif command -v open &>/dev/null; then
        open "$URL" &>/dev/null || true
    fi
) &

# 5. Launch Server
echo "🚀 Launching Recommendation Server at http://localhost:8000 ..."
$VENV_PY server.py
