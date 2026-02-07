# Extract Usernames - Technical Documentation

**For AI assistants (Claude, ChatGPT, etc.) and developers**

Last updated: 2026-02-07

---

## ⚠️ Git Workflow & Repository Strategy — READ FIRST

**Commit Convention**

Use Conventional Commits format:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code refactoring without behavior change
- `test:` Test additions or modifications
- `chore:` Build process, dependencies, tooling
- `style:` Formatting, whitespace
- `perf:` Performance improvements

**Examples:**
```
feat(cli): add --reconfigure flag for selective setup
fix(config): resolve path expansion on Windows
docs: update installation instructions
refactor(prompts): simplify directory validation logic
```

**Commit Guidelines:**
- Atomic commits (one logical change per commit)
- Descriptive subjects (50 characters max)
- Focus on "why" not "what" in commit body

**Git Safety:**
- NEVER commit without explicit permission
- NEVER push without explicit permission
- NEVER run destructive commands (`reset --hard`, `push --force`)
- NEVER stage all files (`git add -A`, `git add .`) - stage specific files
- Always create NEW commits (avoid `--amend`)

---

## Project Overview

**Repository:** https://github.com/beyourahi/extract_usernames  
**Purpose:** Extract Instagram usernames from screenshots using dual-engine OCR (VLM-primary with EasyOCR fallback)  
**Author:** Rahi Khan (Dropout Studio) - [@beyourahi](https://github.com/beyourahi)

**Core Value Proposition:** Automated Instagram lead generation tool with 95%+ accuracy using vision language models, featuring persistent CLI configuration and optional Notion CRM integration.

---

## Tech Stack

**Core Framework:**
- Python 3.9+ (tested on 3.11)
- Click 8.1+ for CLI interface
- PyTorch for deep learning models

**OCR Engines:**
- Ollama + GLM-OCR (VLM-primary mode, recommended)
- EasyOCR (fallback/standalone mode)
- OpenCV for image preprocessing

**CRM Integration:**
- Notion API client for database sync
- Instagram validation via HTTP requests
- Tenacity for retry logic

**Development Tools:**
- setuptools + pyproject.toml for packaging
- pytest for testing (future)
- ruff + black for linting/formatting (future)

**Runtime:**
- Node.js not required (pure Python)
- Ollama external dependency (optional)

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
   - Cross-platform path handling

2. **Interactive First-Time Setup**
   - Click prompts with validation
   - Smart defaults (Desktop folders)
   - Optional sections (skip Notion if not needed)
   - Path existence verification

3. **Backward Compatibility**
   - Original `extract_usernames.py` kept at repo root
   - New `main.py` wraps it via import
   - Legacy scripts still work standalone
   - No breaking changes for existing users

4. **Packaging with Setuptools**
   - Command: `extract-usernames` (hyphenated)
   - Package: `extract_usernames` (underscored)
   - Entry point: `extract_usernames.cli:main`
   - Editable install for development

### Data Flow

1. CLI entry (`cli.py`) loads/prompts for config
2. Config merged with CLI flags (flags take priority)
3. Main wrapper (`main.py`) imports original `extract_usernames.py`
4. Image processing with VLM (primary) or EasyOCR (fallback)
5. Deduplication and validation
6. Output generation (markdown files)
7. Optional Notion sync (`notion_sync.py`)

---

## Common Commands

**Development:**
```bash
pip install -e .        # Install package in editable mode
extract-usernames       # Run CLI
python -m extract_usernames.cli  # Alternative entry point
```

**Code Quality:**
```bash
pytest tests/           # Run tests (future)
ruff check .            # Linting (future)
black --check .         # Format check (future)
mypy extract_usernames/ # Type checking (future)
```

**Package Building:**
```bash
python -m build         # Build wheel + tarball
pip install dist/*.whl  # Install from wheel
```

**IMPORTANT:** Always ask before running ANY scripts. Never assume completion means scripts should run.

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
- **VLM:** Ollama (external dependency, optional)

### Environment Variables

Create `.env` file in project root (optional, for Notion):

```bash
NOTION_TOKEN=secret_xxx
NOTION_DATABASE_ID=xxx
```

Alternatively, configure via interactive prompts or CLI flags.

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

## Code Style Guidelines

**Python Standards:**
- PEP 8 compliant
- Type hints for public functions
- Docstrings for modules and functions
- Snake_case for variables/functions
- PascalCase for classes

**File Organization:**
- Co-locate related functionality
- Keep modules focused and single-purpose
- Use `__init__.py` for package exports

**Import Order:**
1. Standard library
2. Third-party packages
3. Local modules

**Error Handling:**
- Use specific exceptions
- Provide helpful error messages
- Log errors with context

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

## Testing Practices

**Current State:** No automated tests present.

**Recommended Future Stack:**
- **Unit Tests:** pytest
- **Integration Tests:** Test CLI end-to-end
- **Mocking:** responses library for HTTP mocking

**Manual Testing Checklist:**
- [ ] Interactive setup wizard (all paths)
- [ ] Config save/load functionality
- [ ] CLI flag overrides
- [ ] VLM extraction accuracy
- [ ] EasyOCR fallback behavior
- [ ] Notion sync (create, deduplicate)
- [ ] Cross-platform compatibility (Windows, macOS, Linux)

---

## Repository Etiquette

### Commit Message Format

See "Git Workflow" section at top of document.

### Pull Request Guidelines

- Descriptive title and body
- Reference related issues
- Test changes locally before PR
- Update documentation if needed

### Code Review

- Be constructive and specific
- Test reviewer's code locally
- Suggest improvements with examples
- Approve only when confident

---

## Project-Specific Warnings

### CRITICAL - ABSOLUTE PRIORITY

**1. Configuration File Corruption**

- **Problem:** Invalid JSON in config file breaks CLI
- **Solution:** Validate JSON before saving, use atomic writes
- **Recovery:** Delete `~/.config/extract-usernames/config.json` and re-run setup

**2. Ollama Connection Issues**

- **Problem:** VLM mode fails silently if Ollama not running
- **Solution:** CLI checks Ollama availability and warns user
- **Fallback:** Always falls back to EasyOCR automatically

**3. Path Handling Cross-Platform**

- **Problem:** Windows uses backslashes, Unix uses forward slashes
- **Solution:** Use `pathlib.Path` everywhere, never string concatenation
- **Testing:** Test on Windows, macOS, and Linux

**4. GPU Memory Exhaustion**

- **Problem:** Processing many large images can exhaust GPU memory
- **Solution:** Use `--workers 1` to reduce parallelism
- **Detection:** Monitor GPU memory with `nvidia-smi` or similar

**5. Notion API Rate Limits**

- **Problem:** Batch uploads may hit Notion API rate limits
- **Solution:** Built-in retry logic with exponential backoff (tenacity)
- **Limit:** Notion allows ~3 requests/second

**6. Unicode Handling**

- **Problem:** Some usernames may contain special characters
- **Solution:** Use UTF-8 encoding everywhere
- **Validation:** Regex pattern only allows ASCII

**7. Backward Compatibility**

- **Problem:** Users may rely on old CLI behavior
- **Solution:** Original scripts kept at repo root
- **Testing:** Test both new and old workflows

**8. Config Migration**

- **Problem:** Future config schema changes break existing configs
- **Solution:** Implement config version field and migration logic
- **Current:** No versioning yet (TODO for v3.0)

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

### 6. Permission denied on config file
```bash
# Fix permissions on config directory
chmod 755 ~/.config/extract-usernames
chmod 644 ~/.config/extract-usernames/config.json
```

### 7. Import errors after package install
```bash
# Reinstall in editable mode
pip uninstall extract-usernames
pip install -e .
```

---

## Development

### Running Tests
```bash
pytest tests/  # Future
```

### Linting
```bash
ruff check .  # Future
black --check .  # Future
mypy extract_usernames/  # Future
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

### Development Workflow

1. Create feature branch (optional, not required)
2. Make changes
3. Test manually with `extract-usernames`
4. Run linting (when available)
5. Commit with conventional commit message
6. Push to GitHub (with permission)

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
- [ ] Automated testing suite
- [ ] Config versioning and migration
- [ ] GPU memory monitoring
- [ ] Progress bars for long operations

---

## Support

- **Issues:** https://github.com/beyourahi/extract_usernames/issues
- **Author:** [@beyourahi](https://github.com/beyourahi)
- **License:** MIT

---

**This is a production tool for lead generation. Follow best practices for data handling and API usage.**
