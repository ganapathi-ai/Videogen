@echo off
setlocal EnableDelayedExpansion
title THE INNER CITADEL — Intel CPU Mode

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   THE INNER CITADEL — One-Click Startup      ║
echo  ║   Intel CPU Mode  ^|  30GB RAM  ^|  No GPU     ║
echo  ╚══════════════════════════════════════════════╝
echo.

REM ── Check .env ───────────────────────────────────────────────
if not exist ".env" (
    echo  Copying .env template...
    copy ".env.example" ".env" >nul
    echo  [!] .env created — please open it and add your API keys.
    echo      See CREDENTIALS_SETUP.md for instructions.
    echo.
    start notepad ".env"
    echo  Press any key after adding your keys...
    pause >nul
)

REM ── Check Python ─────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

REM ── Check FFmpeg ─────────────────────────────────────────────
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] FFmpeg not found.
    echo  Install with: winget install ffmpeg
    echo  Then restart this script.
    pause
    exit /b 1
)

echo  [OK] Python and FFmpeg found.

REM ── Install Python deps (first time) ─────────────────────────
if not exist "backend\.deps_installed" (
    echo.
    echo  [..] Installing Python dependencies (first time ~10 mins)...
    echo       This downloads: FastAPI, Kokoro TTS, sentence-transformers, etc.
    echo.
    pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo  [ERROR] pip install failed. Check internet connection.
        pause
        exit /b 1
    )
    echo. > backend\.deps_installed
    echo  [OK] Dependencies installed.
)

REM ── Install Node deps (first time) ───────────────────────────
if not exist "frontend\node_modules" (
    echo.
    echo  [..] Installing frontend dependencies...
    pushd frontend
    npm install --silent
    popd
    echo  [OK] Frontend dependencies installed.
)

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   Launching 3 Services                       ║
echo  ╚══════════════════════════════════════════════╝
echo.

REM ── 1. FastAPI Backend ───────────────────────────────────────
echo  [1/3] Starting FastAPI backend on :8000 ...
start "Inner Citadel — Backend API" cmd /k ^
  "cd /d %~dp0backend && echo. && echo  [Backend] http://localhost:8000 && echo  [API Docs] http://localhost:8000/docs && echo. && uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level warning"

timeout /t 3 /nobreak >nul

REM ── 2. Ngrok Tunnel (for Vercel) ─────────────────────────────
echo  [2/3] Starting Ngrok tunnel (connects Vercel to your PC)...
start "Inner Citadel — Ngrok Tunnel" cmd /k ^
  "cd /d %~dp0backend && echo. && python ngrok_tunnel.py"

timeout /t 5 /nobreak >nul

REM ── 3. Next.js Frontend ──────────────────────────────────────
echo  [3/3] Starting Next.js frontend on :3000 ...
start "Inner Citadel — Frontend" cmd /k ^
  "cd /d %~dp0frontend && echo. && echo  [Frontend] http://localhost:3000 && echo. && npm run dev"

timeout /t 4 /nobreak >nul

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   ALL SERVICES RUNNING!                      ║
echo  ╠══════════════════════════════════════════════╣
echo  ║   Frontend:  http://localhost:3000            ║
echo  ║   Backend:   http://localhost:8000            ║
echo  ║   API Docs:  http://localhost:8000/docs       ║
echo  ║                                              ║
echo  ║   For Vercel: Copy Ngrok URL from            ║
echo  ║   the "Ngrok Tunnel" terminal window.        ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Press any key to open http://localhost:3000 ...
pause >nul
start "" "http://localhost:3000"
