# Instagram Username Extractor

**Fast, accurate Instagram username extraction from screenshots using dual-engine OCR (VLM + EasyOCR).**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames
./scripts/setup.sh      # macOS/Linux
# or
.\scripts\setup.ps1     # Windows

# 2. Extract usernames (interactive)
extract-usernames

# 3. Or use command flags
extract-usernames --input ~/Desktop/screenshots --output ~/results
```

**First-time setup wizard** saves your preferences for future runs. Reconfigure anytime:
```bash
extract-usernames --reconfigure
```

---

## Features

- **🎯 VLM-Primary Mode** - Uses GLM-OCR (vision language model) for maximum accuracy
- **🔄 Dual-Engine Fallback** - Falls back to EasyOCR when VLM unavailable
- **⚡ GPU Acceleration** - Supports NVIDIA CUDA, AMD ROCm, Apple Metal
- **🧹 Smart Deduplication** - Detects exact and near-duplicate usernames
- **📤 Notion Integration** - Sync validated leads to Notion database
- **✅ Instagram Validation** - Real-time profile verification
- **💾 Persistent Config** - Interactive setup saves preferences as JSON
- **📊 Detailed Reports** - Performance metrics and extraction statistics

---

## Project Structure

```
extract_usernames/
├── extract_usernames/          # Core package
│   ├── cli.py                 # Click CLI with persistent config
│   ├── config.py              # JSON configuration manager
│   ├── main.py                # Extraction pipeline wrapper
│   │
│   ├── ocr/                   # OCR & VLM modules
│   │   ├── __init__.py
│   │   └── prompts.py         # Interactive setup wizard
│   │
│   ├── integrations/          # External service integrations
│   │   ├── instagram_validator.py  # Profile validation
│   │   ├── notion_manager.py       # Notion API client
│   │   └── notion_sync.py          # Database synchronization
│   │
│   └── _archive/              # Legacy code (backward compatibility)
│       └── extract_usernames.py
│
├── scripts/                   # Installation & setup
│   ├── setup.sh              # Unix/macOS installer
│   ├── setup.ps1             # Windows installer
│   └── setup.py              # Package configuration
│
├── .env.example              # Environment template
├── pyproject.toml            # Modern Python packaging
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

**Configuration stored at:** `~/.config/extract-usernames/config.json`

---

## Installation

### Prerequisites

- **Python 3.9+**
- **Ollama + GLM-OCR** (for VLM mode, recommended)
- **GPU** (optional but significantly faster)

### Install Ollama (Recommended)

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
```powershell
# Download from https://ollama.com/download
ollama pull glm-ocr:bf16
```

### Install Package

```bash
cd extract_usernames
pip install -e .
```

---

## Usage

### Interactive Mode (Recommended)

```bash
# First run: complete setup wizard
extract-usernames

# Subsequent runs: uses saved config
extract-usernames
```

### Configuration Management

```bash
# View current configuration
extract-usernames --show-config

# Reset to defaults
extract-usernames --reset-config

# Reconfigure specific sections
extract-usernames --reconfigure              # Choose section interactively
```

### Command-Line Options

```bash
# Override input/output directories
extract-usernames --input ~/Desktop/leads_jan --output ~/results

# Extraction options
extract-usernames --vlm-model minicpm-v:8b-2.6-q8_0
extract-usernames --no-vlm                # Force EasyOCR-only mode
extract-usernames --diagnostics           # Enable debug output

# Notion sync
extract-usernames --notion-sync           # Force sync
extract-usernames --no-notion-sync        # Skip sync
```

### Full CLI Reference

```
Usage: extract-usernames [OPTIONS] [INPUT_PATH]

Options:
  -o, --output PATH        Output directory
  --no-vlm                Disable VLM mode (EasyOCR-only)
  --vlm-model TEXT        VLM model to use (default: glm-ocr:bf16)
  --diagnostics           Enable diagnostics mode
  --reconfigure           Reconfigure settings
  --show-config           Show current configuration
  --reset-config          Reset configuration to defaults
  --notion-sync           Sync to Notion after extraction
  --no-notion-sync        Skip Notion sync
  --version               Show version and exit
  --help                  Show this message and exit
```

---

## Notion Integration

### Setup Instructions

1. **Create Integration:**
   - Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
   - Click "+ New integration"
   - Name it (e.g., "Instagram Leads")
   - Copy the "Internal Integration Token"

2. **Share Database:**
   - Open your Notion database
   - Click "Share" → Add your integration
   - Copy the database URL or ID

3. **Configure Tool:**
   ```bash
   extract-usernames --reconfigure notion
   ```

### Required Database Schema

Your Notion database must have these properties:

| Property Name | Type | Required | Description |
|--------------|------|----------|-------------|
| **Brand Name** | Title | ✅ | Instagram username |
| **Social Media Account** | URL | ✅ | Profile link |
| **Status** | Status/Select | ✅ | "Didn't Approach", "Approached", etc. |
| Business Type | Multi-select | ⚪ | Optional categorization |
| Payment System | Status/Select | ⚪ | Optional payment tracking |
| Amount | Number | ⚪ | Optional deal value |

### Sync Behavior

- **Duplicate Detection:** Skips usernames already in database
- **Validation:** Optional real-time Instagram profile verification
- **Rate Limiting:** Configurable delay between API calls
- **Auto-sync:** Can be enabled for automatic syncing after extraction

---

## Output Files

All output files are saved to your configured output directory (default: `~/Desktop/leads/`):

### verified_usernames.md
High-confidence extractions ready for use:
```markdown
# Verified Usernames (10)

## 2026-02-07 17:30:15
- brand_name_1
- brand_name_2
...
```

### needs_review.md
Low-confidence or potential duplicates requiring manual review:
```markdown
# Usernames Needing Review (3)

## Low Confidence Extractions
- possible_username ⚠️ Low OCR confidence

## Near Duplicates
- similar_name_v2 ⚠️ Similar to: similar_name
```

### extraction_report.md
Detailed performance metrics:
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

### cropped_usernames_images/ (Directory)
**New in v2.0:** Cropped username regions saved in AVIF format for quality assurance and LLM batch processing:

```
cropped_usernames_images/
├── screenshot_001_crop.avif
├── screenshot_002_crop.avif
└── ...
```

**Features:**
- **Always saved** (regardless of diagnostics mode)
- **AVIF format** with quality 75 - optimal balance of text clarity and file size (50-80% smaller than PNG)
- **One file per screenshot** - enables visual verification and LLM-based quality checks
- **Non-blocking** - pipeline continues even if AVIF save fails

---

## Configuration File

Stored at `~/.config/extract-usernames/config.json`:

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
    "database_id": "xxx",
    "skip_validation": false,
    "validation_delay": 2,
    "auto_sync": false
  }
}
```

---

## Advanced Usage

### Custom VLM Models

Supports any Ollama-compatible vision model:
```bash
# Install alternative model
ollama pull minicpm-v:8b-2.6-q8_0

# Use it
extract-usernames --vlm-model minicpm-v:8b-2.6-q8_0
```

### Diagnostics Mode

Enables debug output and preserves intermediate files:
```bash
extract-usernames --diagnostics
```

Creates `debug/` directory with:
- Raw OCR outputs
- VLM responses
- Preprocessed images
- Detailed logs

### Batch Processing

Process multiple screenshot folders:
```bash
for folder in ~/Desktop/leads_*; do
  extract-usernames --input "$folder" --output "${folder}_results"
done
```

---

## Troubleshooting

### Common Issues

**VLM Not Available:**
```bash
# Check Ollama is running
ollama list

# Restart Ollama
killall ollama
ollama serve
```

**Low Accuracy:**
- Ensure screenshots are clear and readable
- Try diagnostics mode to inspect OCR output
- Consider using VLM mode for better results

**Notion Sync Fails:**
- Verify integration has access to database
- Check database schema matches requirements
- Confirm token is valid

**Config Not Saving:**
```bash
# Check config directory exists
mkdir -p ~/.config/extract-usernames

# Reset and reconfigure
extract-usernames --reset-config
```

---

## Performance

### Benchmarks

| Hardware | Mode | Speed | Accuracy |
|----------|------|-------|----------|
| Apple M2 (Metal) | VLM | ~1s/image | 96% |
| RTX 3080 (CUDA) | VLM | ~0.8s/image | 96% |
| CPU Only | EasyOCR | ~3s/image | 88% |

### Optimization Tips

1. **Use VLM mode** for best accuracy
2. **Enable GPU** for 3-4x speedup
3. **Batch process** large screenshot folders
4. **Reduce workers** if hitting memory limits

---

## Development

### Setup Development Environment

```bash
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames
pip install -e ".[dev]"
```

### Project Architecture

- **CLI Layer** (`cli.py`) - Click interface, config management
- **OCR Layer** (`ocr/`) - VLM and OCR prompts
- **Integration Layer** (`integrations/`) - External services
- **Pipeline** (`main.py`) - Orchestrates extraction workflow

### Running Tests

```bash
pytest tests/
```

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.
