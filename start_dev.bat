@echo off
setlocal EnableDelayedExpansion

REM Get this bat file's directory (works from any location)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

title Inner Citadel - Starting...

echo.
echo ================================================
echo  THE INNER CITADEL - Starting Up
echo  Intel CPU  30GB RAM  No GPU Required
echo ================================================
echo.

REM Check .env exists in the project root
if not exist "%ROOT%\.env" (
    echo Copying .env from template...
    copy "%ROOT%\.env.example" "%ROOT%\.env" >nul 2>&1
    echo .env created.
) else (
    echo [OK] .env found with all API keys.
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not installed.
    echo Download from: https://python.org/downloads/
    echo Make sure to tick "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo [OK] Python found.

REM Check FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] FFmpeg not found. Run this then restart:
    echo    winget install ffmpeg
    echo.
    pause
    exit /b 1
)
echo [OK] FFmpeg found.

REM Install Python packages only on first run
if not exist "%ROOT%\backend\.deps_installed" (
    echo.
    echo [....] Installing Python packages - takes 5-15 mins on first run...
    echo        Please wait, do NOT close this window.
    echo.
    pip install -r "%ROOT%\backend\requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Package install failed. Check internet connection.
        pause
        exit /b 1
    )
    echo installed > "%ROOT%\backend\.deps_installed"
    echo [OK] Python packages installed.
)

REM Install Node packages only on first run
if not exist "%ROOT%\frontend\node_modules" (
    echo [....] Installing frontend packages...
    pushd "%ROOT%\frontend"
    npm install --silent
    popd
    echo [OK] Frontend packages installed.
)

echo.
echo ================================================
echo  Launching services...
echo ================================================
echo.

REM Service 1: FastAPI backend
REM IMPORTANT: cd into backend dir so uvicorn finds main.py
echo [1/3] Backend API on http://localhost:8000
start "Inner Citadel - Backend" cmd /k "cd /d %ROOT%\backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info"

echo Waiting for backend to start...
timeout /t 4 /nobreak >nul

REM Service 2: Ngrok tunnel
echo [2/3] Ngrok tunnel (Vercel to your PC)
start "Inner Citadel - Ngrok" cmd /k "cd /d %ROOT%\backend && python ngrok_tunnel.py"

timeout /t 3 /nobreak >nul

REM Service 3: Next.js frontend
echo [3/3] Frontend on http://localhost:3000
start "Inner Citadel - Frontend" cmd /k "cd /d %ROOT%\frontend && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ================================================
echo  ALL SERVICES LAUNCHED!
echo.
echo  Frontend : http://localhost:3000
echo  Backend  : http://localhost:8000
echo  API Docs : http://localhost:8000/docs
echo.
echo  Check the "Ngrok" window for your public URL.
echo  Copy it to Vercel as NEXT_PUBLIC_BACKEND_URL
echo ================================================
echo.

start "" "http://localhost:3000"
echo Press any key to close this launcher window.
pause >nul
