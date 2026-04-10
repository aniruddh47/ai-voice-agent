#!/usr/bin/env pwsh
# SGU Admission Counselor - Setup Verification Script
# Checks if the project is properly configured and ready to run

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Project Setup Verification" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$allGood = $true
$warnings = @()
$errors = @()

# Check 1: Python Virtual Environment
Write-Host "1) Checking Python virtual environment..." -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\python.exe") {
    Write-Host "   [OK] Virtual environment found" -ForegroundColor Green
    $pythonPath = ".\.venv\Scripts\python.exe"
    $version = & $pythonPath --version 2>&1
    Write-Host "   -> $version" -ForegroundColor Gray
} else {
    Write-Host "   [ERROR] Virtual environment NOT found" -ForegroundColor Red
    $errors += "Create venv: python -m venv .venv"
    $allGood = $false
}

# Check 2: Python Dependencies
Write-Host "`n2) Checking Python dependencies..." -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\python.exe") {
    $deps = @(
        @{ Name = "flask"; ImportName = "flask" },
        @{ Name = "flask-cors"; ImportName = "flask_cors" },
        @{ Name = "google-genai"; ImportName = "google.genai" },
        @{ Name = "sentence-transformers"; ImportName = "sentence_transformers" },
        @{ Name = "numpy"; ImportName = "numpy" }
    )
    foreach ($dep in $deps) {
        $result = & ".\.venv\Scripts\python.exe" -c "import $($dep.ImportName)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   [OK] $($dep.Name)" -ForegroundColor Green
        } else {
            Write-Host "   [WARN] $($dep.Name) not found" -ForegroundColor Yellow
            $warnings += "Missing: $($dep.Name) (run: pip install -r backend/requirements.txt)"
        }
    }
} else {
    Write-Host "   Skipped (no venv)" -ForegroundColor Gray
}

# Check 3: .env File
Write-Host "`n3) Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".\.env") {
    Write-Host "   [OK] .env file found" -ForegroundColor Green
    $envContent = Get-Content .\.env | Select-String "GEMINI_API_KEY"
    if ($envContent) {
        Write-Host "   [OK] GEMINI_API_KEY configured" -ForegroundColor Green
    } else {
        Write-Host "   [ERROR] GEMINI_API_KEY not set in .env" -ForegroundColor Red
        $errors += "Set GEMINI_API_KEY in .env file"
        $allGood = $false
    }
} else {
    Write-Host "   [WARN] .env not found" -ForegroundColor Yellow
    Write-Host "   -> Copy from .env.example first" -ForegroundColor Gray
    $warnings += "Create .env from .env.example and set GEMINI_API_KEY"
}

# Check 4: Backend Structure
Write-Host "`n4) Checking backend structure..." -ForegroundColor Yellow
$backendFiles = @(
    "main.py",
    "api_server.py",
    "backend\requirements.txt",
    "backend\data\college_info.json"
)
foreach ($file in $backendFiles) {
    if (Test-Path $file) {
        Write-Host "   [OK] $file" -ForegroundColor Green
    } else {
        Write-Host "   [ERROR] $file missing" -ForegroundColor Red
        $allGood = $false
    }
}

# Check 5: Frontend Structure
Write-Host "`n5) Checking frontend structure..." -ForegroundColor Yellow
if (Test-Path "chat-ui\package.json") {
    Write-Host "   [OK] package.json found" -ForegroundColor Green
    if (Test-Path "chat-ui\node_modules") {
        Write-Host "   [OK] node_modules installed" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] node_modules not installed" -ForegroundColor Yellow
        $warnings += "Run: cd chat-ui && npm install"
    }
} else {
    Write-Host "   [ERROR] chat-ui/package.json not found" -ForegroundColor Red
    $allGood = $false
}

# Check 6: Frontend Components
Write-Host "`n6) Checking frontend components..." -ForegroundColor Yellow
$components = @(
    "chat-ui\src\App.jsx",
    "chat-ui\src\components\ChatInterface.jsx",
    "chat-ui\src\components\VoicePanel.jsx"
)
foreach ($component in $components) {
    if (Test-Path $component) {
        Write-Host "   [OK] $([System.IO.Path]::GetFileName($component))" -ForegroundColor Green
    } else {
        Write-Host "   [ERROR] $component missing" -ForegroundColor Red
    }
}

# Check 7: Documentation
Write-Host "`n7) Checking documentation..." -ForegroundColor Yellow
$docs = @("README.md", "docs\PROJECT_STRUCTURE.md", ".env.example")
foreach ($doc in $docs) {
    if (Test-Path $doc) {
        Write-Host "   [OK] $doc" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] $doc not found" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan

if ($allGood -and $errors.Count -eq 0) {
    Write-Host "  [OK] All checks passed!" -ForegroundColor Green
    Write-Host "  Your project is ready to run." -ForegroundColor Green
} else {
    if ($errors.Count -gt 0) {
        Write-Host "  [ERROR] Errors found:" -ForegroundColor Red
        foreach ($error in $errors) {
            Write-Host "     * $error" -ForegroundColor Red
        }
    }
    if ($warnings.Count -gt 0) {
        Write-Host "`n  [WARN] Warnings/Suggestions:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "     * $warning" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "`nSetup Guide: Read docs/QUICK_START.md" -ForegroundColor Cyan
Write-Host "Structure:   Read docs/PROJECT_STRUCTURE.md" -ForegroundColor Cyan
Write-Host "`n========================================`n" -ForegroundColor Cyan

# Pause before closing
if (-not $allGood) {
    Write-Host "Press Enter to exit..." -ForegroundColor Yellow
    Read-Host
}
