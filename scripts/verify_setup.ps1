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
Write-Host "1️⃣  Checking Python virtual environment..." -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\python.exe") {
    Write-Host "   ✅ Virtual environment found" -ForegroundColor Green
    $pythonPath = ".\.venv\Scripts\python.exe"
    $version = & $pythonPath --version 2>&1
    Write-Host "   → $version" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Virtual environment NOT found" -ForegroundColor Red
    $errors += "Create venv: python -m venv .venv"
    $allGood = $false
}

# Check 2: Python Dependencies
Write-Host "`n2️⃣  Checking Python dependencies..." -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\python.exe") {
    $deps = @("flask", "flask_cors", "google-genai", "sentence_transformers", "numpy")
    foreach ($dep in $deps) {
        $result = & ".\.venv\Scripts\python.exe" -c "import $dep" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ $dep" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  $dep not found" -ForegroundColor Yellow
            $warnings += "Missing: $dep (run: pip install -r backend/requirements.txt)"
        }
    }
} else {
    Write-Host "   ⏭️  Skipped (no venv)" -ForegroundColor Gray
}

# Check 3: .env File
Write-Host "`n3️⃣  Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".\.env") {
    Write-Host "   ✅ .env file found" -ForegroundColor Green
    $envContent = Get-Content .\.env | Select-String "GEMINI_API_KEY"
    if ($envContent) {
        Write-Host "   ✅ GEMINI_API_KEY configured" -ForegroundColor Green
    } else {
        Write-Host "   ❌ GEMINI_API_KEY not set in .env" -ForegroundColor Red
        $errors += "Set GEMINI_API_KEY in .env file"
        $allGood = $false
    }
} else {
    Write-Host "   ⚠️  .env not found" -ForegroundColor Yellow
    Write-Host "   → Copy from .env.example first" -ForegroundColor Gray
    $warnings += "Create .env from .env.example and set GEMINI_API_KEY"
}

# Check 4: Backend Structure
Write-Host "`n4️⃣  Checking backend structure..." -ForegroundColor Yellow
$backendFiles = @(
    "backend\main.py",
    "backend\api_server.py",
    "backend\requirements.txt",
    "backend\data\college_info.json"
)
foreach ($file in $backendFiles) {
    if (Test-Path $file) {
        Write-Host "   ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $file missing" -ForegroundColor Red
        $allGood = $false
    }
}

# Check 5: Frontend Structure
Write-Host "`n5️⃣  Checking frontend structure..." -ForegroundColor Yellow
if (Test-Path "frontend\package.json") {
    Write-Host "   ✅ package.json found" -ForegroundColor Green
    if (Test-Path "frontend\node_modules") {
        Write-Host "   ✅ node_modules installed" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  node_modules not installed" -ForegroundColor Yellow
        $warnings += "Run: cd frontend && npm install"
    }
} else {
    Write-Host "   ❌ frontend/package.json not found" -ForegroundColor Red
    $allGood = $false
}

# Check 6: Frontend Components
Write-Host "`n6️⃣  Checking frontend components..." -ForegroundColor Yellow
$components = @(
    "frontend\src\App.jsx",
    "frontend\src\components\ChatInterface.jsx",
    "frontend\src\components\VoicePanel.jsx"
)
foreach ($component in $components) {
    if (Test-Path $component) {
        Write-Host "   ✅ $([System.IO.Path]::GetFileName($component))" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $component missing" -ForegroundColor Red
    }
}

# Check 7: Documentation
Write-Host "`n7️⃣  Checking documentation..." -ForegroundColor Yellow
$docs = @("README.md", "docs\PROJECT_STRUCTURE.md", ".env.example")
foreach ($doc in $docs) {
    if (Test-Path $doc) {
        Write-Host "   ✅ $doc" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  $doc not found" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan

if ($allGood -and $errors.Count -eq 0) {
    Write-Host "  ✅ All checks passed!" -ForegroundColor Green
    Write-Host "  Your project is ready to run." -ForegroundColor Green
} else {
    if ($errors.Count -gt 0) {
        Write-Host "  ❌ Errors found:" -ForegroundColor Red
        foreach ($error in $errors) {
            Write-Host "     • $error" -ForegroundColor Red
        }
    }
    if ($warnings.Count -gt 0) {
        Write-Host "`n  ⚠️  Warnings/Suggestions:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "     • $warning" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "`n📖 Setup Guide: Read docs/QUICK_START.md" -ForegroundColor Cyan
Write-Host "📁 Structure:   Read docs/PROJECT_STRUCTURE.md" -ForegroundColor Cyan
Write-Host "`n========================================`n" -ForegroundColor Cyan

# Pause before closing
if (-not $allGood) {
    Write-Host "Press Enter to exit..." -ForegroundColor Yellow
    Read-Host
}
