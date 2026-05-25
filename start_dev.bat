@echo off
setlocal EnableDelayedExpansion

REM Always work from this bat file's directory
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

title Inner Citadel - Starting Up

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
    echo Tick "Add Python to PATH" during install.
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

REM Install packages only on first run
if not exist "%ROOT%\backend\.deps_installed" (
    echo.
    echo ================================================
    echo  Installing packages - first time only ~10 mins
    echo  Please wait. Do NOT close this window.
    echo ================================================
    echo.

    REM STEP 1: PyTorch CPU FIRST (required before sentence-transformers)
    echo [1/3] Installing PyTorch CPU (required for sentence-transformers)...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
    if errorlevel 1 (
        echo [WARNING] PyTorch CPU install had issues. Continuing...
    ) else (
        echo [OK] PyTorch CPU installed.
    )

    REM STEP 2: Install all other requirements
    echo [2/3] Installing all other packages...
    pip install -r "%ROOT%\backend\requirements.txt"
    if errorlevel 1 (
        echo.
        echo [ERROR] Package install failed.
        echo Check your internet connection and try again.
        pause
        exit /b 1
    )
    echo [OK] All packages installed.

    REM STEP 3: Mark as done
    echo installed > "%ROOT%\backend\.deps_installed"
    echo [3/3] Setup complete.
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
echo  Launching 3 services...
echo ================================================
echo.

REM Service 1: FastAPI backend (cd into backend so uvicorn finds main.py)
echo [1/3] Backend API - http://localhost:8000
start "Inner Citadel - Backend" cmd /k "cd /d %ROOT%\backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info"

echo Waiting for backend to start...
timeout /t 4 /nobreak >nul

REM Service 2: Ngrok tunnel
echo [2/3] Ngrok tunnel (connects Vercel to your PC)
start "Inner Citadel - Ngrok" cmd /k "cd /d %ROOT%\backend && python ngrok_tunnel.py"

timeout /t 3 /nobreak >nul

REM Service 3: Next.js frontend
echo [3/3] Frontend - http://localhost:3000
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
echo  IMPORTANT: Copy the URL from the Ngrok window
echo  and paste it into Vercel as NEXT_PUBLIC_BACKEND_URL
echo ================================================
echo.
start "" "http://localhost:3000"
echo Press any key to close this launcher.
pause >nul
