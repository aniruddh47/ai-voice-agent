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

REM Check if frontend dependencies are installed
if not exist "chat-ui\node_modules" (
    echo Warning: Frontend dependencies not installed
    echo Installing npm packages...
    cd chat-ui
    call npm install
    cd ..
)

REM Start Backend (Flask) in new window
echo [1/2] Starting Flask Backend (Port 5000)...
start "SGU Backend" cmd /k "!SCRIPT_DIR!\.venv\Scripts\activate.bat && python api_server.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak

REM Start Frontend (React) in new window
echo [2/2] Starting React Frontend (Port 5173)...
start "SGU Frontend" cmd /k "cd chat-ui && npm run dev"

REM Wait for user
timeout /t 2 /nobreak

echo.
echo ======================================
echo   ✅ System Started Successfully!
echo ======================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5173
echo.
echo Close either window to stop that service
echo.
