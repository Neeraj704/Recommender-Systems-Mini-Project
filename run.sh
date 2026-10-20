#!/usr/bin/env bash
# Quick launcher for Spotify Music Recommendation System Web App
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "🎵 Starting Spotify Music Recommendation System..."
if [ -d ".venv" ]; then
    PYTHON_EXEC=".venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

$PYTHON_EXEC server.py
