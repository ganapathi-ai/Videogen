@echo off
setlocal EnableDelayedExpansion

REM Always work from this bat file's directory
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM Keep window open even on error
if "%1"=="__CHILD__" goto :MAIN

REM Relaunch this bat in a NEW visible window that stays open
start "Inner Citadel Launcher" cmd /k ""%~f0" __CHILD__"
exit /b 0

:MAIN
title Inner Citadel - Starting Up
color 0A

echo.
echo ================================================
echo  THE INNER CITADEL - Starting Up
echo  Python 3.13  Intel CPU  30GB RAM  No GPU
echo ================================================
echo.

REM Check .env
if not exist "%ROOT%\.env" (
    echo Copying .env from template...
    copy "%ROOT%\.env.example" "%ROOT%\.env" >nul 2>&1
    echo .env created with saved API keys.
) else (
    echo [OK] .env found.
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Download: https://python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i found.

REM Check FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] FFmpeg not found. Run: winget install ffmpeg
    pause
    exit /b 1
)
echo [OK] FFmpeg found.

REM Install packages only on first run
if not exist "%ROOT%\backend\.deps_installed" (
    echo.
    echo ================================================
    echo  FIRST TIME SETUP - Installing packages
    echo  This takes 10-20 mins. Window stays open.
    echo ================================================
    echo.

    echo [1/3] Installing PyTorch CPU first...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    if errorlevel 1 (
        echo [WARNING] PyTorch install had issues - continuing...
    ) else (
        echo [OK] PyTorch CPU done.
    )

    echo.
    echo [2/3] Installing all other packages...
    pip install -r "%ROOT%\backend\requirements.txt"
    if errorlevel 1 (
        echo.
        echo [ERROR] Package install failed. See error above.
        echo Fix the error then delete this file and retry:
        echo   %ROOT%\backend\.deps_installed
        pause
        exit /b 1
    )
    echo [OK] All packages installed.

    echo installed > "%ROOT%\backend\.deps_installed"
    echo [3/3] First-time setup complete!
    echo.
)

REM Frontend packages
if not exist "%ROOT%\frontend\node_modules" (
    echo [....] Installing frontend packages...
    pushd "%ROOT%\frontend"
    npm install
    popd
    echo [OK] Frontend packages done.
)

echo.
echo ================================================
echo  Starting 3 services now...
echo ================================================
echo.

echo [1/3] Starting Backend on http://localhost:8000
start "Inner Citadel - Backend" cmd /k "title Backend API && cd /d %ROOT%\backend && echo. && echo Backend: http://localhost:8000 && echo Docs:    http://localhost:8000/docs && echo. && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 4 /nobreak >nul

echo [2/3] Starting Ngrok tunnel
start "Inner Citadel - Ngrok" cmd /k "title Ngrok Tunnel && cd /d %ROOT%\backend && python ngrok_tunnel.py"

timeout /t 3 /nobreak >nul

echo [3/3] Starting Frontend on http://localhost:3000
start "Inner Citadel - Frontend" cmd /k "title Frontend && cd /d %ROOT%\frontend && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ================================================
echo  ALL SERVICES RUNNING!
echo.
echo  Frontend: http://localhost:3000
echo  Backend : http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo.
echo  Check the NGROK window for your public URL
echo  Copy it to Vercel as NEXT_PUBLIC_BACKEND_URL
echo ================================================
echo.
start "" "http://localhost:3000"

echo This window can be closed now.
echo Press any key to close.
pause >nul
