#!/usr/bin/env pwsh
# SGU Admission Counselor - Startup Script (PowerShell)
# This script starts both backend (Flask) and frontend (React) servers

$ErrorActionPreference = "Continue"
Write-Host "`n======================================" -ForegroundColor Green
Write-Host "  SGU Admission Counselor System" -ForegroundColor Green
Write-Host "  Starting Backend & Frontend..." -ForegroundColor Green
Write-Host "======================================`n" -ForegroundColor Green

# Get the root directory (parent of scripts folder)
$RootDir = Split-Path -Parent $PSScriptRoot

# Check if .venv exists
if (-not (Test-Path "$RootDir\.venv")) {
    Write-Host "Error: Python virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if frontend dependencies are installed
if (-not (Test-Path "$RootDir\chat-ui\node_modules")) {
    Write-Host "Warning: Frontend dependencies not installed" -ForegroundColor Yellow
    Write-Host "Installing npm packages..." -ForegroundColor Cyan
    Set-Location "$RootDir\chat-ui"
    & npm install
    Set-Location $RootDir
}

Write-Host "[1/2] Starting Flask Backend (Port 5000)..." -ForegroundColor Cyan

# Start API server in background process
$apiProcess = Start-Process `
    -FilePath "$RootDir\.venv\Scripts\python.exe" `
    -ArgumentList "api_server.py" `
    -WorkingDirectory $RootDir `
    -NoNewWindow `
    -PassThru

Write-Host "[OK] Backend PID: $($apiProcess.Id)" -ForegroundColor Green

# Wait for API to initialize
Write-Host "Waiting for API to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "`n[2/2] Starting React Frontend (Port 3000)..." -ForegroundColor Cyan

# Start React frontend in background process
$reactProcess = Start-Process `
    -FilePath "npm" `
    -ArgumentList "run dev" `
    -WorkingDirectory "$RootDir\chat-ui" `
    -NoNewWindow `
    -PassThru

Write-Host "[OK] Frontend PID: $($reactProcess.Id)" -ForegroundColor Green

Write-Host "`n======================================" -ForegroundColor Green
Write-Host "  [OK] System Started Successfully!" -ForegroundColor Green
Write-Host "======================================`n" -ForegroundColor Green

Write-Host "Backend:  " -ForegroundColor Cyan -NoNewline
Write-Host "http://localhost:5000" -ForegroundColor Yellow

Write-Host "Frontend: " -ForegroundColor Cyan -NoNewline
Write-Host "http://localhost:3000" -ForegroundColor Yellow

Write-Host "`nOpening browser in 2 seconds..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"

Write-Host "`nPress Ctrl+C to stop all services`n" -ForegroundColor Magenta

# Keep window open and monitor processes
try {
    while ($true) {
        Start-Sleep -Seconds 2
        
        if (-not (Get-Process -Id $apiProcess.Id -ErrorAction SilentlyContinue)) {
            Write-Host "`n[WARN] API Server stopped" -ForegroundColor Yellow
            break
        }
        
        if (-not (Get-Process -Id $reactProcess.Id -ErrorAction SilentlyContinue)) {
            Write-Host "`n[WARN] React Frontend stopped" -ForegroundColor Yellow
            break
        }
    }
}
catch {
    # User pressed Ctrl+C
    Write-Host "`n`nShutting down services..." -ForegroundColor Yellow
    Stop-Process -Id $apiProcess.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $reactProcess.Id -ErrorAction SilentlyContinue
    Write-Host "[OK] All services stopped." -ForegroundColor Green
}
