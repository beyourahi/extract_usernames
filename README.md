# Instagram Username Extractor

Extracts Instagram usernames from screenshots using OCR (optical character recognition). Designed for processing large batches of screenshots from lead generation campaigns or prospecting work.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Why this exists:** Manually typing usernames from hundreds of screenshots wastes time. This tool automates the extraction, validates the usernames, and optionally syncs them to Notion for CRM workflows.

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames
./scripts/setup.sh  # macOS, Linux, WSL, Git Bash

# Run the extractor
extract-usernames
```

**Windows users:** Install [WSL](https://docs.microsoft.com/windows/wsl/install) or [Git Bash](https://gitforwindows.org) first, then run the script above.

**Advanced options:**
```bash
./scripts/setup.sh --skip-ollama  # EasyOCR-only mode
./scripts/setup.sh --help         # Show all options
```

The first run asks for your screenshot folder and output preferences. These settings are saved to `~/.config/extract-usernames/config.json` for future runs.

Update settings anytime:
```bash
extract-usernames --reconfigure
```

### Platform Support

The setup script automatically detects your platform and provides appropriate installation instructions:

| Platform | Package Manager | Ollama Installation |
|----------|-----------------|---------------------|
| macOS | Homebrew | `brew install ollama` |
| Ubuntu/Debian | apt | curl script |
| Fedora/RHEL | dnf/yum | curl script |
| Arch Linux | pacman | curl script |
| WSL (Windows) | apt | curl script |
| Git Bash (Windows) | manual | download from ollama.com |

---

## Requirements

- **Python 3.9 or later**
- **Ollama with GLM-OCR model** (enables AI-based text recognition for better accuracy on Instagram screenshots)
- **GPU recommended** (NVIDIA CUDA, AMD ROCm, or Apple Metal—works on CPU, just 3-4x slower)

Without Ollama, the tool falls back to EasyOCR-only mode, which still works but has lower accuracy (~88% vs ~96%).

---

## Installation

### Install Ollama and GLM-OCR Model

Ollama provides the vision language model (VLM) that recognizes text in screenshots more accurately than traditional OCR.

**macOS:**
```bash
brew install ollama
ollama pull glm-ocr:bf16
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull glm-ocr:bf16
```

**Windows:**
Download from [ollama.com/download](https://ollama.com/download), then:
```powershell
ollama pull glm-ocr:bf16
```

### Install the Package

```bash
cd extract_usernames
pip install -e .
```

This installs the `extract-usernames` command and all Python dependencies.

---

## Basic Usage

### Interactive Mode

Run without flags to use your saved settings:

```bash
extract-usernames
```

The tool processes all screenshots in your configured input folder, removes duplicates, validates the usernames, and saves results to your output folder.

### Common Workflows

**Process screenshots from a specific campaign:**
```bash
extract-usernames --input ~/Desktop/jan_2026_campaign --output ~/Desktop/jan_leads
```

**Force sync to Notion after extraction:**
```bash
extract-usernames --notion-sync
```

**Reconfigure a specific setting:**
```bash
extract-usernames --reconfigure
```

**Use a different VLM model for higher accuracy:**
```bash
extract-usernames --vlm-model minicpm-v:8b-2.6-q8_0
```

**Disable VLM entirely (EasyOCR-only mode):**
```bash
extract-usernames --no-vlm
```

---

## Output Files

The tool generates three markdown files in your output directory:

### `verified_usernames.md`
High-confidence extractions ready to use:
```markdown
# Verified Usernames (47)

## 2026-02-07 17:30:15

- brand_name_1
- brand_name_2
- coffee_shop_nyc
...
```

### `needs_review.md`
Low-confidence results or near-duplicates requiring manual review:
```markdown
# Usernames Needing Review (3)

## Low Confidence Extractions
- possible_typo ⚠️ Low OCR confidence

## Near Duplicates
- coffeeshop_nyc ⚠️ Similar to: coffee_shop_nyc
```

### `extraction_report.md`
Performance metrics and processing details:
```markdown
# Extraction Report

**Date:** 2026-02-07 17:30:15
**Processing Time:** 45.2s
**Images Processed:** 50
**Success Rate:** 94%

## Hardware
- GPU: NVIDIA RTX 3080
- Mode: VLM-Primary (GLM-OCR)
```

### `cropped_usernames_images/` directory
Cropped username regions from each screenshot, saved in AVIF format. Useful for visual verification or feeding to other LLM tools for quality checks. AVIF format reduces file size by 50-80% compared to PNG while maintaining text clarity.

---

## Notion Integration

Syncs extracted usernames to a Notion database for CRM tracking.

### Setup

**1. Create a Notion integration:**
- Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
- Click "+ New integration"
- Name it (e.g., "Instagram Leads")
- Copy the "Internal Integration Token"

**2. Share your database with the integration:**
- Open your Notion database
- Click "Share" → Add your integration
- Copy the database URL (you'll need the database ID from it)

**3. Configure the tool:**
```bash
extract-usernames --reconfigure
```
Select "Notion settings" and paste your token and database ID when prompted.

### Required Database Properties

Your Notion database needs these properties (case-sensitive):

| Property Name            | Type          | Required | Purpose                               |
| ------------------------ | ------------- | -------- | ------------------------------------- |
| **Brand Name**           | Title         | Yes      | Instagram username                    |
| **Social Media Account** | URL           | Yes      | Full Instagram profile URL            |
| **Status**               | Status/Select | Yes      | Lead status ("Didn't Approach", etc.) |
| Business Type            | Multi-select  | No       | Optional categorization               |
| Payment System           | Status/Select | No       | Optional payment tracking             |
| Amount                   | Number        | No       | Optional deal value                   |

### How Sync Works

- Checks for existing usernames before adding (case-insensitive)
- Optionally validates profiles by checking if the Instagram page exists
- Respects Notion API rate limits with configurable delays
- Can be enabled for automatic sync after every extraction

---

## Command Reference

```
Usage: extract-usernames [OPTIONS] [INPUT_PATH]

Options:
  -o, --output PATH        Output directory
  --no-vlm                 Disable VLM mode (use EasyOCR only)
  --vlm-model TEXT         Specify VLM model (default: glm-ocr:bf16)
  --diagnostics            Save debug files to help troubleshoot issues
  --reconfigure            Update saved settings
  --show-config            Display current configuration
  --reset-config           Reset to default settings
  --notion-sync            Force sync to Notion after extraction
  --no-notion-sync         Skip Notion sync
  --version                Show version
  --help                   Show this help message
```

---

## Configuration File

Settings are stored at `~/.config/extract-usernames/config.json`:

```json
{
  "input_dir": "~/Desktop/screenshots",
  "output_dir": "~/Desktop/leads",
  "vlm_enabled": true,
  "vlm_model": "glm-ocr:bf16",
  "diagnostics": false,
  "notion": {
    "enabled": true,
    "token": "secret_xxx",
    "database_id": "abc123...",
    "skip_validation": false,
    "validation_delay": 2,
    "auto_sync": false
  }
}
```

**Priority order:** CLI flags override config file values, which override defaults.

---

## Advanced Features

### Custom VLM Models

Try different vision models for specific use cases:

```bash
# Install an alternative model
ollama pull minicpm-v:8b-2.6-q8_0

# Use it for extraction
extract-usernames --vlm-model minicpm-v:8b-2.6-q8_0
```

Some models are faster but less accurate. The default `glm-ocr:bf16` balances both.

### Diagnostics Mode

Saves intermediate processing files to help troubleshoot low accuracy:

```bash
extract-usernames --diagnostics
```

Creates a `debug/` directory with:
- Raw OCR text outputs
- VLM API responses
- Preprocessed image crops
- Detailed processing logs

### Batch Processing Multiple Folders

Process several screenshot folders in one go:

```bash
for folder in ~/Desktop/campaigns/*/; do
  extract-usernames --input "$folder" --output "${folder}results"
done
```

---

## Troubleshooting

### Ollama won't start or VLM unavailable

```bash
# Check if Ollama is running
ollama list

# Restart Ollama
killall ollama
ollama serve
```

If the GLM-OCR model isn't available, the tool falls back to EasyOCR automatically.

### Low extraction accuracy

- Verify screenshots are clear and text is readable
- Enable diagnostics mode to inspect what OCR sees: `--diagnostics`
- Try VLM mode if you're using EasyOCR-only
- Check that screenshots are from Instagram profile pages (the tool expects a specific layout)

### Notion sync fails

- Verify the integration has access to the database (click Share in Notion)
- Check that database properties match the required schema exactly (case-sensitive)
- Test the integration token in Notion's API settings
- Review error messages—they usually indicate which property is missing

### Configuration won't save

```bash
# Ensure config directory exists
mkdir -p ~/.config/extract-usernames

# Reset and reconfigure from scratch
extract-usernames --reset-config
```

If issues persist, check file permissions on `~/.config/extract-usernames/`.

---

## Performance Benchmarks

| Hardware         | Mode         | Speed       | Accuracy |
| ---------------- | ------------ | ----------- | -------- |
| Apple M2 (Metal) | VLM (GLM-OCR)| ~1s/image   | 96%      |
| RTX 3080 (CUDA)  | VLM (GLM-OCR)| ~0.8s/image | 96%      |
| CPU Only         | EasyOCR      | ~3s/image   | 88%      |

**To maximize performance:**
- Use VLM mode with a GPU for 3-4x speedup over CPU-only
- Batch large folders instead of running repeatedly on small sets
- Reduce worker count if hitting GPU memory limits

---

## Technical Details

### How It Works

1. **Preprocessing:** Crops the header region from screenshots (Instagram profile pages have usernames in a consistent location)
2. **Primary OCR:** Sends cropped region to VLM (GLM-OCR via Ollama)
3. **Fallback OCR:** If VLM confidence is low (<85%), falls back to EasyOCR
4. **Validation:** Checks username format against Instagram's rules (lowercase letters, numbers, periods, underscores; 1-30 characters)
5. **Deduplication:** Removes exact duplicates and flags near-duplicates using Levenshtein distance
6. **Optional Notion Sync:** Checks for existing entries, validates profiles, and batch creates pages

### Project Structure

```
extract_usernames/
├── extract_usernames/          # Core package
│   ├── cli.py                 # Click CLI and persistent config
│   ├── config.py              # JSON configuration manager
│   ├── main.py                # Extraction pipeline orchestrator
│   │
│   ├── ocr/                   # OCR and VLM modules
│   │   ├── __init__.py
│   │   └── prompts.py         # Interactive setup wizard
│   │
│   ├── integrations/          # External service integrations
│   │   ├── instagram_validator.py  # Profile verification
│   │   ├── notion_manager.py       # Notion API client
│   │   └── notion_sync.py          # Database sync logic
│   │
│   └── _archive/              # Legacy code (backward compatibility)
│
├── scripts/                   # Installation scripts
│   ├── setup.sh              # Unix/macOS
│   ├── setup.ps1             # Windows
│   └── setup.py              # Package configuration
│
├── .env.example              # Environment template
├── pyproject.toml            # Python packaging
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

### Key Dependencies

- **click** (CLI framework with option parsing)
- **torch** (PyTorch for GPU-accelerated OCR)
- **easyocr** (Traditional OCR fallback)
- **opencv-python** (Image preprocessing)
- **notion-client** (Notion API integration)
- **tenacity** (Retry logic for API calls)

---

## Development

### Setup Development Environment

```bash
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames
pip install -e ".[dev]"
```

### Architecture Overview

- **CLI Layer** (`cli.py`): Handles command-line interface, loads/saves config
- **OCR Layer** (`ocr/`): VLM and EasyOCR processing with fallback logic
- **Integration Layer** (`integrations/`): Notion API, Instagram validation
- **Pipeline** (`main.py`): Orchestrates the full extraction workflow

---

## Contributing

Contributions are welcome. Fork the repository, create a feature branch, and open a pull request with a clear description of your changes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.
