# Instagram Username Extractor - Windows Setup Script
# PowerShell script for automated installation on Windows

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Instagram Username Extractor - Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check Python installation
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -ge 3 -and $minor -ge 9) {
            Write-Host "  ✅ Found $pythonVersion" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Python 3.9+ required, found $pythonVersion" -ForegroundColor Red
            Write-Host "  Please install Python 3.11+ from https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
    }
} catch {
    Write-Host "  ❌ Python not found in PATH" -ForegroundColor Red
    Write-Host "  Please install Python 3.11+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    exit 1
}

# Install Python dependencies
Write-Host "`n[2/5] Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "  This may take 5-10 minutes (downloading ~2-3GB)..." -ForegroundColor Gray
try {
    python -m pip install --upgrade pip --quiet
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Dependencies installed successfully" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Some dependencies failed to install" -ForegroundColor Yellow
        Write-Host "  Try running: pip install --user -r requirements.txt" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ❌ Failed to install dependencies" -ForegroundColor Red
    Write-Host "  Try: pip install --user -r requirements.txt" -ForegroundColor Yellow
    Write-Host "  Or create a virtual environment first" -ForegroundColor Yellow
}

# Check Ollama installation
Write-Host "`n[3/5] Checking Ollama installation..." -ForegroundColor Yellow
try {
    $ollamaVersion = ollama --version 2>&1
    if ($ollamaVersion) {
        Write-Host "  ✅ Ollama is installed" -ForegroundColor Green
        
        # Check if Ollama service is running
        Write-Host "  Checking Ollama service..." -ForegroundColor Gray
        try {
            $ollamaList = ollama list 2>&1
            Write-Host "  ✅ Ollama service is running" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️  Ollama service not running" -ForegroundColor Yellow
            Write-Host "  Starting Ollama service..." -ForegroundColor Gray
            Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 3
        }
    }
} catch {
    Write-Host "  ⚠️  Ollama not found" -ForegroundColor Yellow
    Write-Host "  Download from: https://ollama.com/download" -ForegroundColor Gray
    Write-Host "  Note: You can use --no-vlm flag to run without Ollama" -ForegroundColor Gray
    $ollamaInstalled = $false
}

# Download GLM-OCR model if Ollama is available
if ($ollamaInstalled -ne $false) {
    Write-Host "`n[4/5] Downloading GLM-OCR model..." -ForegroundColor Yellow
    Write-Host "  Model size: ~2.2GB (this may take a few minutes)..." -ForegroundColor Gray
    try {
        ollama pull glm-ocr:bf16
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ GLM-OCR model downloaded successfully" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Model download had issues" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠️  Could not download model" -ForegroundColor Yellow
        Write-Host "  You can download it later with: ollama pull glm-ocr:bf16" -ForegroundColor Gray
    }
} else {
    Write-Host "`n[4/5] Skipping model download (Ollama not installed)" -ForegroundColor Yellow
}

# Validate installation
Write-Host "`n[5/5] Validating installation..." -ForegroundColor Yellow
try {
    $helpOutput = python extract_usernames.py --help 2>&1
    if ($helpOutput -match "usage:") {
        Write-Host "  ✅ Installation validated successfully" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Validation had warnings" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ❌ Validation failed" -ForegroundColor Red
    Write-Host "  Run these commands for diagnostics:" -ForegroundColor Yellow
    Write-Host "    python --version" -ForegroundColor Gray
    Write-Host "    pip list" -ForegroundColor Gray
    Write-Host "    ollama list" -ForegroundColor Gray
}

# Print summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "✅ Python: Installed" -ForegroundColor Green
Write-Host "✅ Dependencies: Installed" -ForegroundColor Green
if ($ollamaInstalled -ne $false) {
    Write-Host "✅ Ollama: Installed" -ForegroundColor Green
    Write-Host "✅ GLM-OCR Model: Ready" -ForegroundColor Green
} else {
    Write-Host "⚠️  Ollama: Not installed (optional)" -ForegroundColor Yellow
}

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Place Instagram screenshots in a folder on your Desktop" -ForegroundColor White
Write-Host "2. Run: python extract_usernames.py folder_name" -ForegroundColor White
Write-Host "3. Check results in ~/Desktop/leads/" -ForegroundColor White

if ($ollamaInstalled -eq $false) {
    Write-Host "`n💡 Tip: Install Ollama for better accuracy" -ForegroundColor Yellow
    Write-Host "   Download: https://ollama.com/download" -ForegroundColor Gray
    Write-Host "   Or use: python extract_usernames.py folder_name --no-vlm" -ForegroundColor Gray
}

Write-Host "`nFor help: python extract_usernames.py --help" -ForegroundColor Gray
Write-Host "Documentation: https://github.com/beyourahi/extract_usernames`n" -ForegroundColor Gray
