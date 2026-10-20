@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo Spotify Music Recommendation System - 1-Click Launcher
echo ==========================================================

REM 1. Detect Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

REM 2. Check / Create Virtual Environment
if not exist ".venv" (
    echo [*] Creating virtual environment in .venv...
    python -m venv .venv
    echo [OK] Virtual environment created.
)

REM 3. Verify / Auto-Install Dependencies
.venv\Scripts\python.exe -c "import starlette, uvicorn, sklearn, pandas, numpy" >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing required dependencies from requirements.txt (first run only)...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\pip.exe install -r requirements.txt
    echo [OK] Dependencies installed successfully!
)

REM 4. Launch Browser
start http://localhost:8000

REM 5. Launch Server
echo [*] Launching Recommendation Server at http://localhost:8000 ...
.venv\Scripts\python.exe server.py
pause
