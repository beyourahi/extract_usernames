# Setup Scripts

Installation scripts that check your Python version, install the package, and guide you through Ollama setup if available.

---

## Installation

**All Platforms (macOS, Linux, WSL, Git Bash):**

```bash
cd extract_usernames
./scripts/setup.sh
```

If you get a permission error:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Windows Users:**

This script requires either:
- **WSL (Windows Subsystem for Linux)**: [Install Guide](https://docs.microsoft.com/windows/wsl/install)
- **Git Bash**: [Download](https://gitforwindows.org)

After installing WSL or Git Bash, run the setup script as shown above.

**Advanced Options:**
```bash
./scripts/setup.sh --help              # Show all options
./scripts/setup.sh --skip-ollama       # EasyOCR-only mode
./scripts/setup.sh --verbose           # Detailed output
./scripts/setup.sh --dry-run           # Preview without executing
```

---

## Platform Detection

The unified setup script automatically detects:
- **macOS** (Intel and Apple Silicon)
- **Linux distributions** (Ubuntu, Debian, Fedora, RHEL, Arch)
- **Windows Subsystem for Linux (WSL)**
- **Git Bash for Windows**

For native Windows PowerShell/CMD, the script provides installation instructions for WSL or Git Bash.

---

## What the Setup Script Does

The unified setup script performs these steps:

1. **Detect Platform**: Automatically identifies your OS (macOS, Linux, WSL, Git Bash)
2. **Check Python**: Validates Python 3.9+ is installed (tries `python3` then `python`)
3. **Install Package**: Runs `pip install -e .` (editable mode for development)
4. **Setup Ollama**: Checks if Ollama is available (optional)
5. **Download Model**: Pulls GLM-OCR model (~2.2GB) if Ollama exists
6. **Validate CLI**: Tests the `extract-usernames` command

The script guides you through any missing requirements with platform-specific installation instructions. If Ollama is not installed, the tool falls back to EasyOCR automatically (no manual intervention needed).

**Command-Line Flags:**
- `--skip-ollama` - Skip Ollama installation and model download (EasyOCR-only mode)
- `--skip-model` - Install Ollama but skip model download
- `--verbose` - Show detailed output during installation
- `--dry-run` - Preview installation steps without executing
- `--help` - Display usage information

---

## Files

### setup.sh
**Platform:** macOS, Linux, WSL, Git Bash (Universal)

Universal setup script with intelligent platform detection. Checks Python version, installs the package, and guides you through Ollama setup with platform-specific instructions. Features colored output, command-line flags, and comprehensive error handling.

**Version:** 3.0.0

### setup.ps1
**Platform:** Windows PowerShell (DEPRECATED)

⚠️ **Deprecated as of 2026-02-13. Will be removed in August 2026.**

Legacy Windows-native setup script. Windows users should now use `setup.sh` via WSL or Git Bash instead. This file remains for backward compatibility only and displays an interactive deprecation warning when run.

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

**"Setup script not working on Windows"**

The unified setup script requires WSL or Git Bash. Native PowerShell/CMD are not supported.

Install one of these Unix-like environments:
- **WSL (Recommended)**: `wsl --install` in PowerShell (requires Windows 10/11)
- **Git Bash**: Download from [gitforwindows.org](https://gitforwindows.org)

After installation, run the setup script in WSL or Git Bash terminal.

---

**WSL-specific: "Command not found" errors**

If commands work in WSL but not in Windows terminal:
1. WSL and Windows have separate environments
2. Run `extract-usernames` from within the WSL terminal
3. Access Windows files via `/mnt/c/Users/...` paths

---

**Git Bash-specific: Path issues**

Git Bash supports both Unix and Windows path formats:
```bash
# Unix-style (preferred)
./scripts/setup.sh

# Windows-style (also works)
C:/Users/yourname/extract_usernames/scripts/setup.sh
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
