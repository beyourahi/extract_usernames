# Extract Usernames

## Always Do First

**Invoke the `frontend-design` skill** before writing any frontend code, every session, no exceptions.

## Git Workflow -- READ FIRST

**NEVER CREATE BRANCHES.** Direct commits to main. No feature branches, no development branches.

**Conventional Commits:** `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `style:`, `perf:`

**Git Safety:**
- NEVER commit/push without permission
- NEVER stage all (`git add -A` or `git add .`)
- NEVER use destructive commands (`reset --hard`, `push --force`)
- Always create NEW commits (never `--amend`)

**Always break large tasks into focused scopes** — run parallel agents with git worktrees, each with a narrow, well-defined goal.

---

## Project Overview

Instagram username extraction from screenshots via dual-engine OCR (VLM-primary, EasyOCR fallback). CLI tool with persistent JSON config and optional Notion CRM sync. Production lead generation tool with 95%+ accuracy.

**Repository:** https://github.com/beyourahi/extract_usernames
**Author:** [@beyourahi](https://github.com/beyourahi)

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Python 3.9+, Click 8.1+ CLI |
| OCR | Ollama + GLM-OCR (VLM-primary), EasyOCR (fallback), OpenCV preprocessing |
| ML | PyTorch (GPU: CUDA/ROCm/MPS/CPU) |
| Integration | Notion API client, Instagram validation, Tenacity retry logic |
| Packaging | setuptools + pyproject.toml, editable install |

---

## Core Architecture

### Package Structure

```
extract_usernames/
├── cli.py                      # Click CLI entry, config management
├── cli_merge_duplicates.py     # Standalone deduplication CLI
├── config.py                   # JSON config manager (~/.config/extract-usernames/config.json)
├── main.py                     # Extraction pipeline orchestrator
├── ocr/
│   └── prompts.py             # Interactive setup wizard
├── integrations/
│   ├── instagram_validator.py # Profile validation
│   ├── notion_manager.py      # Notion API client
│   ├── notion_sync.py         # Database sync
│   └── notion_deduplicator.py # Smart deduplication
└── _archive/                  # Legacy scripts (backward compat)
```

**Key patterns:**
- Config: `~/.config/extract-usernames/config.json` (JSON, sections: `directories`, `extraction`, `notion`)
- Command: `extract-usernames` (installed via setuptools)
- Package name: `extract_usernames` (underscored)
- Entry point: `extract_usernames.cli:main`

**Data flow:**
1. CLI loads/prompts config → merge with flags (flags win)
2. VLM extraction (primary) or EasyOCR (fallback)
3. **AVIF crop archiving** (always-on, saved to `cropped_usernames_images/` subdirectory)
4. Deduplication (exact + Levenshtein distance)
5. Output (markdown files: `verified_usernames.md`, `needs_review.md`, `extraction_report.md`)
6. Optional Notion sync → auto-deduplicate

---

## Common Commands

```bash
# Setup
./scripts/setup.sh             # macOS/Linux installer (pip install -e .)
.\scripts\setup.ps1            # Windows installer

# Run
extract-usernames              # Interactive mode (uses saved config)
extract-usernames --input ~/screenshots --output ~/results
extract-usernames --reconfigure                    # Update settings
extract-usernames --notion-sync                    # Sync + auto-deduplicate
extract-usernames --notion-sync --dry-run-dedup    # Preview deduplication
extract-usernames --no-deduplicate                 # Skip deduplication

# Package
python -m build                # Build wheel + tarball
pip install dist/*.whl         # Install from wheel

# Alternative entry
python -m extract_usernames.cli
```

**CRITICAL:** Always ask before running scripts. Never assume completion means execution.

---

## Installation

```bash
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames
./scripts/setup.sh  # or setup.ps1 on Windows (runs pip install -e .)
```

**Dependencies:** `click>=8.1.0`, `torch`, `easyocr`, `opencv-python`, `numpy`, `notion-client`, `tenacity`
**VLM:** Ollama + `glm-ocr:bf16` model (optional, recommended)
**Config:** `.env` (optional, or use interactive prompts)

---

## CLI Reference

**Priority:** CLI flags > saved config > prompts > defaults

**Key flags:**
- `--input PATH`, `--output PATH` - Directories
- `--vlm-model MODEL` - VLM model (default: `glm-ocr:bf16`)
- `--no-vlm` - EasyOCR-only mode
- `--diagnostics` - Debug files
- `--reconfigure` - Update config
- `--notion-sync` - Force Notion sync
- `--deduplicate` / `--no-deduplicate` - Auto-deduplicate Notion (default: on)
- `--dry-run-dedup` - Preview deduplication without removing
- `--version`, `--help`

**First run:** Interactive setup wizard (prompts for input/output dirs, VLM, Notion)
**Subsequent runs:** Uses `~/.config/extract-usernames/config.json`

---

## Configuration

**Location:** `~/.config/extract-usernames/config.json`

```json
{
  "directories": {"input": "...", "output": "..."},
  "extraction": {"use_vlm": true, "vlm_model": "glm-ocr:bf16", "diagnostics": false, "workers": null},
  "notion": {"enabled": true, "token": "secret_xxx", "database_id": "xxx"}
}
```

**Config API:** `extract_usernames.config.ConfigManager` - load(), save(), get(), merge_with_args()

---

## Code Style

- PEP 8, type hints on public functions, docstrings
- snake_case (variables/functions), PascalCase (classes)
- Import order: stdlib → third-party → local
- Specific exceptions with helpful messages
- Focused, single-purpose modules

---

## Extraction Pipeline

**Flow:**
1. Input validation (dir exists, contains images)
2. Hardware detection (CUDA/ROCm/MPS/CPU)
3. VLM availability check (Ollama connection)
4. Load existing usernames (deduplication)
5. Parallel processing (multi-worker)
6. **AVIF crop archiving** (always-on, `cropped_usernames_images/` subdirectory, quality 75)
7. Deduplication (exact + Levenshtein distance)
8. Output (markdown: `verified_usernames.md`, `needs_review.md`, `extraction_report.md`)
9. Optional Notion sync + auto-deduplicate

**Dual-Engine OCR:**
- VLM-primary (default): GLM-OCR via Ollama → fallback to EasyOCR if confidence < 0.85
- `--no-vlm`: EasyOCR-only

**Preprocessing ROI:** `image[165:255, 100:-100]` (crop header region)

**Validation:** Regex `^[a-z0-9._]{1,30}$`, no consecutive periods, no start/end period

---

## Notion Integration

**Workflow:**
1. Load `verified_usernames.md`
2. Deduplicate batch (case-insensitive)
3. Check existing entries in Notion
4. Optional Instagram validation (HTTP GET, 200=valid, 404=invalid)
5. Batch create pages
6. Auto-deduplicate (default) - smart scoring algorithm keeps best username, archives duplicates

**Smart Deduplication:** Groups by URL, scores usernames (-1000 for malformed like "1.", rewards letters/lowercase/length), keeps highest score, archives rest.

**API:** `extract_usernames.integrations.notion_manager.NotionDatabaseManager`, `extract_usernames.integrations.instagram_validator.InstagramValidator`, `extract_usernames.integrations.notion_deduplicator.run_deduplication()`

---

## Critical Warnings

**Config corruption:** Invalid JSON breaks CLI → delete `~/.config/extract-usernames/config.json` and re-run setup
**Ollama:** CLI checks availability, auto-falls back to EasyOCR
**Cross-platform paths:** Use `pathlib.Path` everywhere (Windows backslashes vs Unix forward slashes)
**GPU memory:** Use `--workers 1` if exhausting VRAM
**Notion rate limits:** Built-in retry logic (tenacity), ~3 req/sec limit
**Deduplication safety:** Entries archived (not deleted), restorable from Notion trash
**AVIF crops:** Saved to `cropped_usernames_images/` subdirectory (always-on), requires `pillow-avif-plugin` dependency
**Config versioning:** No migration logic yet (TODO v3.0)

---

## Troubleshooting

**"Config file not found":** Expected on first run (interactive setup)
**"Ollama not available":** `brew install ollama && ollama pull glm-ocr:bf16` (macOS) or see README
**"Command not found":** `pip install -e .` or use `python -m extract_usernames.cli`
**Notion "Database not found":** Verify integration access, database ID (32-char hex), token validity
**Low accuracy:** Enable VLM (`--vlm-model minicpm-v:8b-2.6-q8_0`), check `--diagnostics`
**Permission denied:** `chmod 755 ~/.config/extract-usernames && chmod 644 config.json`

---

## Documentation References

**Extended guides:**
- `README.md` - Installation, usage examples, benchmarks, Notion setup
- `CONTRIBUTING.md` - Contribution guidelines

**Repository:** https://github.com/beyourahi/extract_usernames
**Author:** [@beyourahi](https://github.com/beyourahi)
**License:** MIT

---

**Production lead generation tool. Handle data responsibly. Follow API usage best practices.**

---

## Frontend UI Visual Verification (REQUIRED)

**During any frontend UI or design work, you MUST use Playwright MCP to visually verify your changes.**

### Workflow

1. **Determine the active port** for this project before taking screenshots (see Port Detection below)
2. **Take screenshots** via Playwright MCP targeting the correct `http://localhost:<port>`
3. **Save to `tmp_screenshots/`** at the root of this repository
4. **Analyze each screenshot** against the plan or requirements to verify accuracy
5. **Iterate** — fix discrepancies, re-screenshot, re-analyze until requirements are met

### Rules

- **ALWAYS** take at least one screenshot per UI change before considering it done
- **NEVER** mark frontend work as complete without visual verification
- Screenshots go in `tmp_screenshots/` at the project root (create the directory if it doesn't exist)
- Name screenshots descriptively: `tmp_screenshots/homepage-hero.png`, `tmp_screenshots/cart-drawer-open.png`
- Take screenshots at multiple viewport sizes when responsive behavior matters (mobile + desktop)
- After each batch of changes, compare the screenshots against the original requirements or design spec and explicitly state what matches and what still needs work

### Port Detection

Multiple dev servers may be running simultaneously across projects. **Always identify the correct port before screenshotting.**

Detection order (use the first that works):

1. **Check dev server output** — the terminal running `bun run dev` prints the active URL (e.g. `Local: http://localhost:4457`)
2. **Check `vite.config.ts`** — look for an explicit `server.port` value
3. **Check `package.json`** — some scripts hardcode a port via `--port` flag
4. **Scan active ports** — run `lsof -i :3000-4999 | grep LISTEN` to see what's bound, then match the process to this project's directory

**Never assume port 3000.** If multiple Vite/Hydrogen servers are running, confirm you're screenshotting the right one by checking the page title or a unique element.

### Example Playwright MCP Usage

```
// First confirm the port (e.g. from dev server output: http://localhost:4457)
navigate to http://localhost:4457
take screenshot → tmp_screenshots/homepage-initial.png

// After making changes, verify
take screenshot → tmp_screenshots/homepage-after-fix.png
// Analyze: does this match the requirement?
```

### What to Check in Screenshots

- Layout matches the intended design/spec
- Spacing, typography, and colors are correct
- Interactive states (hover, focus, open/closed) render properly
- No visible layout breaks or overflow issues
- Responsive breakpoints behave as expected
