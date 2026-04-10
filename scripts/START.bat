@echo off
REM SGU Admission Counselor - Startup Script (Windows Batch)
REM This script starts both backend (Flask) and frontend (React) servers

title SGU Admission Counselor System
color 0A

echo.
echo ======================================
echo   SGU Admission Counselor System
echo   Starting Backend ^& Frontend...
echo ======================================
echo.

REM Get the directory where this script is located
setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0..

REM Change to root directory
cd /d "%SCRIPT_DIR%"

REM Check if .venv exists
if not exist ".venv" (
    echo Error: Python virtual environment not found!
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

REM Check backend dependencies and auto-install if missing
echo Checking backend dependencies...
".venv\Scripts\python.exe" -c "import flask, flask_cors, google.genai, sentence_transformers, numpy" >nul 2>&1
if errorlevel 1 (
    echo Backend dependencies missing. Installing from backend\requirements.txt...
    ".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install backend dependencies.
        pause
        exit /b 1
    )
)

REM Check if frontend dependencies are installed
if not exist "chat-ui\node_modules" (
    echo Warning: Frontend dependencies not installed
    echo Installing npm packages...
    cd chat-ui
    call npm install
    cd ..
)

REM Start Backend (Flask) in new window only if not already running
echo [1/2] Starting Flask Backend (Port 5000)...
netstat -ano | findstr /R /C:":5000 .*LISTENING" >nul
if not errorlevel 1 (
    echo [INFO] Backend already running on port 5000.
) else (
    start "SGU Backend" cmd /k "cd /d ""!SCRIPT_DIR!"" && .venv\Scripts\python.exe api_server.py"
)

REM Wait for backend health endpoint (up to ~90s; first run can be slow)
set BACKEND_READY=0
for /L %%I in (1,1,45) do (
    curl --silent --output NUL --max-time 2 http://localhost:5000/api/health >nul 2>&1
    if not errorlevel 1 (
        set BACKEND_READY=1
        goto :backend_up
    )
    timeout /t 2 /nobreak >nul
)

:backend_up
if "%BACKEND_READY%"=="0" (
    echo.
    echo [WARN] Backend did not become healthy in time.
    echo        It may still be initializing models. Check "SGU Backend" window for exact status/error.
    echo.
) else (
    echo [OK] Backend is healthy at http://localhost:5000
)

REM Start Frontend (React) in new window only if not already running
echo [2/2] Starting React Frontend (Port 3000)...
netstat -ano | findstr /R /C:":3000 .*LISTENING" >nul
if not errorlevel 1 (
    echo [INFO] Frontend already running on port 3000.
) else (
    start "SGU Frontend" cmd /k "cd /d ""!SCRIPT_DIR!\chat-ui"" && npm run dev"
)

REM Wait for user
timeout /t 2 /nobreak

echo.
echo ======================================
echo   [OK] System Started Successfully!
echo ======================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:3000
echo.
echo Close either window to stop that service
echo.

REM Open the correct frontend URL in default browser.
start "" "http://localhost:3000"
