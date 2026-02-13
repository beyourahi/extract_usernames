# Setup Scripts

Installation scripts that check your Python version, install the package, and guide you through Ollama setup if available.

---

## Install on macOS / Linux

```bash
cd extract_usernames
./scripts/setup.sh
```

If you get a permission error, make the script executable first:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

## Install on Windows

```powershell
cd extract_usernames
.\scripts\setup.ps1
```

If PowerShell blocks the script, allow it to run for this session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

---

## What These Scripts Do

Both platform scripts perform these steps:

1. Check Python 3.9 or later is installed (required for the package)
2. Install the package with `pip install -e .` (editable mode for development)
3. Check if Ollama is available (optional)
4. Download GLM-OCR model (~2.2GB) if Ollama exists
5. Validate the CLI command works (`extract-usernames --version`)

The scripts guide you through any missing requirements. If Ollama is not installed, the tool falls back to EasyOCR (no manual intervention needed).

---

## Files

### setup.sh
**Platform:** macOS, Linux, Unix-like systems

Checks your Python version, installs the package, and guides you through Ollama setup if available. Uses colored output for readability.

### setup.ps1
**Platform:** Windows (PowerShell 5.0+)

Windows-native version with colored output and the same setup steps as `setup.sh`. Includes Windows-specific error handling.

### setup.py
**Purpose:** Package configuration file

Called by pip during installation (`pip install -e .`). Not run directly.

Defines:
- Package metadata (name, version, author)
- Dependencies from `requirements.txt`
- Entry point for the `extract-usernames` CLI command
- Python version requirement (3.9 or later)

---

## Manual Installation

If you prefer manual setup or need more control:

### 1. Install the Package

```bash
cd extract_usernames
pip install -e .
```

### 2. Install Ollama (Optional)

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
3. In your terminal:
   ```
   ollama pull glm-ocr:bf16
   ```

### 3. Verify Installation

```bash
extract-usernames --version
```

---

## Troubleshooting

**"python3: command not found" or version too old**

Install Python 3.9 or later:
```bash
brew install python@3.11  # macOS
sudo apt install python3   # Ubuntu/Debian
```

Windows: Download from [python.org/downloads](https://www.python.org/downloads/) and check "Add Python to PATH" during installation.

---

**"Permission denied" when running setup.sh**

Make the script executable:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

---

**"Script cannot be loaded because running scripts is disabled"**

Allow the script to run for this session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

---

**Ollama won't start or connect**

macOS/Linux - Check if Ollama is running:
```bash
pgrep ollama
```

If not running, start it manually:
```bash
ollama serve &
```

Windows - Check the system tray for the Ollama icon. If not running, restart the Ollama application.

---

**"extract-usernames: command not found" after installation**

Reload your shell configuration:
```bash
source ~/.bashrc   # or ~/.zshrc
```

Or restart your terminal.

---

## Post-Installation

After setup completes:

1. Run the setup wizard to configure input/output directories:
   ```bash
   extract-usernames
   ```

2. Place screenshots in the configured directory (default: `~/Desktop/screenshots/`)

3. Run extraction:
   ```bash
   extract-usernames
   ```

4. (Optional) Configure Notion integration:
   ```bash
   extract-usernames --reconfigure
   ```

---

## Development

Installing from source for development work:

```bash
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames
pip install -e ".[dev]"
extract-usernames --version
```

---

## Environment Variables

Advanced configuration options:

```bash
# Custom Python binary
export PYTHON_BIN=/usr/local/bin/python3.11

# Skip Ollama model download during setup
export SKIP_OLLAMA_PULL=1

# Custom pip options
export PIP_OPTIONS="--no-cache-dir --quiet"
```

---

## Uninstallation

```bash
# Remove package
pip uninstall instagram-username-extractor

# Remove configuration files
rm -rf ~/.config/extract-usernames

# Remove Ollama model (optional)
ollama rm glm-ocr:bf16
```

---

## Support

For setup issues:

1. Check the troubleshooting section above
2. Review the [main README.md](../README.md) for general help
3. Open an issue on [GitHub](https://github.com/beyourahi/extract_usernames/issues)
