#!/usr/bin/env pwsh
# SGU Admission Counselor - Resilient backend launcher
# Keeps restarting the backend if it exits unexpectedly.

param(
    [int]$RestartDelaySeconds = 3,
    [int]$MaxRestarts = 100,
    [int]$Port = 5000
)

$ErrorActionPreference = "Continue"
$RootDir = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"
$ApiScript = Join-Path $RootDir "api_server.py"
$restartCount = 0

if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python venv not found at: $PythonExe" -ForegroundColor Red
    Write-Host "Create it with: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $ApiScript)) {
    Write-Host "[ERROR] api_server.py not found at: $ApiScript" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Resilient backend launcher started" -ForegroundColor Cyan
Write-Host "[INFO] Max restarts: $MaxRestarts | Delay: $RestartDelaySeconds sec" -ForegroundColor Cyan

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existing) {
    Write-Host "[INFO] Backend already listening on port $Port (PID $($existing.OwningProcess))." -ForegroundColor Yellow
    Write-Host "[INFO] Not starting another backend instance." -ForegroundColor Yellow
    exit 0
}

while ($true) {
    Write-Host "`n[INFO] Starting backend (attempt $($restartCount + 1))..." -ForegroundColor Green

    Push-Location $RootDir
    & $PythonExe $ApiScript
    $exitCode = $LASTEXITCODE
    Pop-Location

    if ($exitCode -eq 0) {
        Write-Host "[INFO] Backend exited cleanly (code 0). Stopping launcher." -ForegroundColor Yellow
        break
    }

    $restartCount += 1
    Write-Host "[WARN] Backend exited with code $exitCode." -ForegroundColor Yellow

    if ($restartCount -ge $MaxRestarts) {
        Write-Host "[ERROR] Reached MaxRestarts=$MaxRestarts. Stopping launcher." -ForegroundColor Red
        exit 1
    }

    Write-Host "[INFO] Restarting in $RestartDelaySeconds seconds..." -ForegroundColor Cyan
    Start-Sleep -Seconds $RestartDelaySeconds
}
