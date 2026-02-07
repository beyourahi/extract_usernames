# Extract Usernames - Technical Documentation

**For AI assistants (Claude, ChatGPT, etc.) and developers**

Last updated: 2026-02-07

---

## Project Overview

**Repository:** https://github.com/beyourahi/extract_usernames  
**Purpose:** Extract Instagram usernames from screenshots using dual-engine OCR (VLM-primary with EasyOCR fallback)  
**Author:** Rahi Khan (Dropout Studio) - [@beyourahi](https://github.com/beyourahi)

---

## Architecture (v2.0 - Interactive CLI)

### Package Structure

```
extract_usernames/
├── __init__.py           # Package initialization
├── cli.py                # Click CLI entry point
├── config.py             # JSON configuration manager
├── prompts.py            # Interactive Click prompts
├── main.py               # Extraction pipeline wrapper
├── notion_sync.py        # Notion sync orchestration
├── instagram_validator.py # Instagram validation
└── notion_manager.py     # Notion API client

Root files (backward compatibility):
├── extract_usernames.py  # Original extraction script
├── leads_to_notion.py    # Original Notion sync script
├── setup.py              # Setuptools packaging
├── pyproject.toml        # Modern Python metadata
└── requirements.txt      # Dependencies with click>=8.1.0
```

### Key Design Decisions

1. **Persistent Configuration**
   - Location: `~/.config/extract-usernames/config.json`
   - Format: JSON with nested structure
   - Sections: `directories`, `extraction`, `notion`
   - CLI flags override saved config

2. **Interactive First-Time Setup**
   - Click prompts with validation
   - Smart defaults (Desktop folders)
   - Optional sections (skip Notion if not needed)

3. **Backward Compatibility**
   - Original `extract_usernames.py` kept at repo root
   - New `main.py` wraps it via import
   - Legacy scripts still work standalone

4. **Packaging with Setuptools**
   - Command: `extract-usernames` (hyphenated)
   - Package: `extract_usernames` (underscored)
   - Entry point: `extract_usernames.cli:main`

---

## Installation

### Modern Setup (Recommended)
```bash
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames
./setup.sh  # or setup.ps1 on Windows
```

This runs `pip install -e .` to install the package in editable mode.

### Manual Installation
```bash
pip install -e .
```

### Dependencies
- **Core:** `click>=8.1.0`, `torch`, `easyocr`, `opencv-python`, `numpy`
- **Notion:** `notion-client`, `python-dotenv`, `requests`, `tenacity`
- **VLM:** Ollama (external dependency)

---

## CLI Usage

### Command Structure
```bash
extract-usernames [OPTIONS]
```

### Option Priority (highest to lowest)
1. Command-line flags (e.g., `--input /path`)
2. Saved configuration (`~/.config/extract-usernames/config.json`)
3. Interactive prompts (if config missing)
4. Hard-coded defaults

### Key Options

**Configuration Management:**
- `--reconfigure [all|directories|extraction|notion]` - Re-run setup for specific section

**Directories:**
- `--input PATH` - Input directory (default: prompts or config)
- `--output PATH` - Output directory (default: prompts or config)

**Extraction:**
- `--vlm-model MODEL` - VLM model (default: glm-ocr:bf16)
- `--no-vlm` - Disable VLM, use EasyOCR only
- `--diagnostics` - Save debug files
- `--workers N` - Number of parallel workers

**Notion:**
- `--notion-token TOKEN` - Notion integration token
- `--notion-db DATABASE_ID` - Notion database ID
- `--skip-notion` - Skip Notion sync even if configured

**Utility:**
- `--version` - Show version
- `--help` - Show help message

### Examples

**First run (interactive):**
```bash
extract-usernames
# Prompts for:
# - Input directory
# - Output directory  
# - Enable VLM? (y/n)
# - VLM model
# - Enable Notion? (y/n)
# - Notion token & database ID
```

**Subsequent runs:**
```bash
extract-usernames  # Uses saved config
```

**Override specific settings:**
```bash
extract-usernames --input ~/Desktop/new_folder --diagnostics
```

**Reconfigure Notion only:**
```bash
extract-usernames --reconfigure notion
```

**CLI-only mode (no config):**
```bash
extract-usernames --input ~/screenshots --output ~/results --no-vlm
```

---

## Configuration File Format

**Location:** `~/.config/extract-usernames/config.json`

```json
{
  "directories": {
    "input": "/Users/rahi/Desktop/screenshots",
    "output": "/Users/rahi/Desktop/leads"
  },
  "extraction": {
    "use_vlm": true,
    "vlm_model": "glm-ocr:bf16",
    "diagnostics": false,
    "workers": null
  },
  "notion": {
    "enabled": true,
    "token": "secret_xxx",
    "database_id": "xxx"
  }
}
```

### Config Manager API

```python
from extract_usernames.config import ConfigManager

config = ConfigManager()

# Load config (creates if missing)
data = config.load()

# Save config
config.save(data)

# Get specific value with fallback
token = config.get("notion.token", default=None)

# Merge CLI overrides
final_config = config.merge_with_args(cli_args)
```

---

## Extraction Pipeline

### Flow

1. **Input validation** - Check if directory exists and contains images
2. **Hardware detection** - GPU availability (CUDA/ROCm/MPS/CPU)
3. **VLM availability check** - Test Ollama connection
4. **Load existing usernames** - For deduplication
5. **Parallel processing** - Multi-worker image processing
6. **Deduplication** - Exact match + Levenshtein distance
7. **Output generation** - Write markdown files and report
8. **Notion sync** (optional) - Validate and upload to Notion

### Dual-Engine OCR

**VLM-Primary Mode (Default):**
```python
result = extract_with_vlm(image)  # GLM-OCR via Ollama
if not result or confidence < 0.85:
    result = extract_with_easyocr(image)  # Fallback
```

**EasyOCR-Only Mode (`--no-vlm`):**
```python
result = extract_with_easyocr(image)  # Single engine
```

### Preprocessing

```python
# Region of interest (ROI)
TOP_OFFSET = 165
CROP_HEIGHT = 90
LEFT_MARGIN = 100
RIGHT_MARGIN = 100

cropped = image[TOP_OFFSET:TOP_OFFSET+CROP_HEIGHT, LEFT_MARGIN:-RIGHT_MARGIN]
```

### Validation

**Regex pattern:**
```python
USERNAME_PATTERN = r'^[a-z0-9._]{1,30}$'
```

**Additional checks:**
- Length: 1-30 characters
- Allowed characters: `a-z`, `0-9`, `.`, `_`
- No consecutive periods
- Not start/end with period

---

## Notion Integration

### Workflow

1. **Load usernames** from `verified_usernames.md`
2. **Deduplicate** within batch (case-insensitive)
3. **Check Notion** for existing entries
4. **Validate on Instagram** (optional, can skip with `--skip-validation`)
5. **Batch create** Notion pages
6. **Generate report** with statistics

### Notion API

```python
from extract_usernames.notion_manager import NotionDatabaseManager

manager = NotionDatabaseManager(token, database_id)

# Get existing usernames
existing = manager.get_all_existing_usernames()

# Create single page
result = manager.create_page(username, url, status="Didn't Approach")

# Batch create
stats = manager.batch_create_pages(validated_accounts, skip_duplicates=True)
```

### Instagram Validation

```python
from extract_usernames.instagram_validator import InstagramValidator

with InstagramValidator(delay_between_requests=2.0) as validator:
    results = validator.validate_batch(usernames)
```

**Validation method:**
- HTTP GET to `https://www.instagram.com/{username}/`
- Status 200 + no redirect to login = valid
- Status 404 = invalid
- Other = uncertain

---

## Common Issues

### 1. "Config file not found" on first run
**Expected behavior.** CLI will prompt for configuration.

### 2. "Ollama not available"
Install Ollama:
```bash
brew install ollama  # macOS
curl -fsSL https://ollama.com/install.sh | sh  # Linux
# Windows: Download from ollama.com/download

ollama pull glm-ocr:bf16
```

### 3. "extract-usernames: command not found"
```bash
pip install -e .  # Reinstall package
# Or use absolute path
python -m extract_usernames.cli
```

### 4. Notion sync fails with "Database not found"
Verify:
1. Integration has access to database (Share menu)
2. Database ID is correct (32-char hex)
3. Token is valid (starts with `secret_`)

### 5. Low accuracy extractions
- Ensure VLM mode enabled (not `--no-vlm`)
- Check GPU availability with `--diagnostics`
- Try alternative VLM: `--vlm-model minicpm-v:8b-2.6-q8_0`

---

## Development

### Running Tests
```bash
pytest tests/
```

### Linting
```bash
ruff check .
black --check .
mypy extract_usernames/
```

### Building Package
```bash
python -m build
# Creates dist/extract_usernames-*.whl and dist/extract_usernames-*.tar.gz
```

### Installing from Wheel
```bash
pip install dist/extract_usernames-*.whl
```

---

## Changelog

### v2.0.0 (2026-02-07)
- ✨ Interactive CLI with persistent JSON configuration
- ✨ Click-based prompts for first-time setup
- ✨ `extract-usernames` command installed via setuptools
- ✨ `--reconfigure` flag for section-specific updates
- 🏗️ Reorganized into `extract_usernames/` package
- 📦 Modern packaging with `setup.py` + `pyproject.toml`
- 🔄 Backward compatible with original scripts

### v1.0.0 (Previous)
- Initial release with VLM-primary architecture
- Command-line args only
- Standalone scripts

---

## Future Enhancements

- [ ] Web UI (Gradio/Streamlit)
- [ ] Batch upload via CLI (folder monitoring)
- [ ] Custom VLM prompt templates
- [ ] Export to CSV/Excel
- [ ] Multiple Notion database support
- [ ] Docker containerization

---

## Support

- **Issues:** https://github.com/beyourahi/extract_usernames/issues
- **Author:** [@beyourahi](https://github.com/beyourahi)
- **License:** MIT
