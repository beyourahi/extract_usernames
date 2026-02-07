# Setup Scripts

Automated installation scripts for Instagram Username Extractor across different platforms.

---

## Quick Start

### macOS / Linux

```bash
cd extract_usernames
./scripts/setup.sh
```

### Windows (PowerShell)

```powershell
cd extract_usernames
.\scripts\setup.ps1
```

---

## What These Scripts Do

All setup scripts perform the following steps:

1. **✅ Check Python** - Verifies Python 3.9+ is installed
2. **📦 Install Package** - Installs the tool with `pip install -e .`
3. **🤖 Check Ollama** - Verifies Ollama installation (optional but recommended)
4. **💾 Download Model** - Pulls GLM-OCR model (~2.2GB) if Ollama is available
5. **✅ Validate** - Confirms CLI is accessible via `extract-usernames` command

---

## Files

### setup.sh
**Platform:** macOS, Linux, Unix-like systems  
**Requirements:** Bash shell

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Features:**
- Colored output for better readability
- Automatic Python version detection
- Ollama installation guidance
- Error handling with clear messages

---

### setup.ps1
**Platform:** Windows  
**Requirements:** PowerShell 5.0+

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

**Features:**
- Windows-native colored output
- Python version validation
- Ollama installation guidance
- Error handling with exit codes

---

### setup.py
**Purpose:** Python package configuration (used by `pip install`)  
**Note:** Not meant to be run directly - called by pip during installation

Defines:
- Package metadata
- Dependencies from `requirements.txt`
- Entry point: `extract-usernames` CLI command
- Python version requirements (>=3.9)

---

## Manual Installation

If you prefer manual setup:

### 1. Install Python Dependencies

```bash
cd extract_usernames
pip install -e .
```

### 2. Install Ollama (Optional but Recommended)

**macOS:**
```bash
brew install ollama
ollama serve &
ollama pull glm-ocr:bf16
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull glm-ocr:bf16
```

**Windows:**
1. Download from [ollama.com/download](https://ollama.com/download)
2. Install and run Ollama
3. Open terminal:
   ```
   ollama pull glm-ocr:bf16
   ```

### 3. Verify Installation

```bash
extract-usernames --version
```

---

## Troubleshooting

### Python Not Found

**macOS/Linux:**
```bash
# Install Python 3.9+
brew install python@3.11  # macOS
sudo apt install python3   # Ubuntu/Debian
```

**Windows:**
- Download from [python.org/downloads](https://www.python.org/downloads/)
- Ensure "Add Python to PATH" is checked during installation

### Permission Denied (setup.sh)

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### PowerShell Execution Policy Error

```powershell
# Allow script execution for current session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

### Ollama Not Starting

**macOS/Linux:**
```bash
# Check if Ollama is running
pgrep ollama

# Start Ollama manually
ollama serve &
```

**Windows:**
- Check if Ollama is running in system tray
- Restart Ollama application

### CLI Not Found After Installation

```bash
# Reload shell configuration
source ~/.bashrc   # or ~/.zshrc

# Or restart terminal
```

---

## Development

### Installing from Source for Development

```bash
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify
extract-usernames --version
```

### Testing Setup Scripts

To test setup scripts in a clean environment:

```bash
# Create virtual environment
python3 -m venv test_env
source test_env/bin/activate  # macOS/Linux
# or
.\test_env\Scripts\Activate   # Windows

# Run setup
./scripts/setup.sh

# Test CLI
extract-usernames --version

# Cleanup
deactivate
rm -rf test_env
```

---

## Environment Variables

Optional environment variables for advanced configuration:

```bash
# Custom Python binary
export PYTHON_BIN=/usr/local/bin/python3.11

# Skip Ollama model download
export SKIP_OLLAMA_PULL=1

# Custom pip options
export PIP_OPTIONS="--no-cache-dir --quiet"
```

---

## Post-Installation

After running setup scripts:

1. **Configure Tool:**
   ```bash
   extract-usernames  # First run starts setup wizard
   ```

2. **Place Screenshots:**
   - Default: `~/Desktop/screenshots/`
   - Or configure custom path during setup

3. **Run Extraction:**
   ```bash
   extract-usernames
   ```

4. **Optional - Setup Notion:**
   ```bash
   extract-usernames --reconfigure notion
   ```

---

## Uninstallation

```bash
# Remove package
pip uninstall instagram-username-extractor

# Remove configuration
rm -rf ~/.config/extract-usernames

# Remove Ollama model (optional)
ollama rm glm-ocr:bf16
```

---

## Support

For issues with setup scripts:

1. Check [Troubleshooting](#troubleshooting) section above
2. Review [main README.md](../README.md) for general help
3. Open an issue on [GitHub](https://github.com/beyourahi/extract_usernames/issues)
