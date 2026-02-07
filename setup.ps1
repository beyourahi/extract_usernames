# Instagram Username Extractor - Modern Setup Script
# One-command installation with pip install -e .

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Instagram Username Extractor - Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -ge 3 -and $minor -ge 9) {
            Write-Host "  ✅ Python $pythonVersion" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Python 3.9+ required" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "  ❌ Python not found" -ForegroundColor Red
    Write-Host "  Install: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Install package
Write-Host "`n[2/4] Installing package..." -ForegroundColor Yellow
try {
    python -m pip install -e . --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Package installed" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Installation failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ❌ Installation failed" -ForegroundColor Red
    exit 1
}

# Check Ollama
Write-Host "`n[3/4] Checking Ollama..." -ForegroundColor Yellow
$ollamaOk = $false
try {
    $ollamaVersion = ollama --version 2>&1
    if ($ollamaVersion) {
        Write-Host "  ✅ Ollama installed" -ForegroundColor Green
        $ollamaOk = $true
        
        # Pull GLM-OCR model
        Write-Host "  Downloading GLM-OCR model (~2.2GB)..." -ForegroundColor Cyan
        ollama pull glm-ocr:bf16 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Model ready" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Model download incomplete" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  ⚠️  Ollama not found (VLM mode unavailable)" -ForegroundColor Yellow
    Write-Host "  Install: https://ollama.com/download" -ForegroundColor Yellow
}

# Validate
Write-Host "`n[4/4] Validating..." -ForegroundColor Yellow
try {
    $version = extract-usernames --version 2>&1
    if ($version) {
        Write-Host "  ✅ CLI ready" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Validation failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ❌ Validation failed" -ForegroundColor Red
    exit 1
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Quick Start:" -ForegroundColor Cyan
Write-Host "  1. Place screenshots on your Desktop" -ForegroundColor White
Write-Host "  2. Run: extract-usernames" -ForegroundColor Green
Write-Host "  3. Follow interactive prompts" -ForegroundColor White

Write-Host "`nOr use flags:" -ForegroundColor Cyan
Write-Host "  extract-usernames --input my_screenshots --output results" -ForegroundColor Green

if (-not $ollamaOk) {
    Write-Host "`n💡 For best accuracy, install Ollama:" -ForegroundColor Yellow
    Write-Host "  https://ollama.com/download" -ForegroundColor Gray
    Write-Host "  ollama pull glm-ocr:bf16" -ForegroundColor Gray
}

Write-Host "`nDocumentation: https://github.com/beyourahi/extract_usernames`n" -ForegroundColor Cyan
