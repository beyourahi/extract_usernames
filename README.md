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
./setup.sh  # macOS/Linux  or  .\setup.ps1  # Windows

# 2. Extract usernames (interactive)
extract-usernames

# 3. Or use command flags
extract-usernames --input ~/Desktop/screenshots
```

**First-time setup wizard** saves your preferences for future runs. Reconfigure anytime with:
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
- **💾 Persistent Config** - Interactive setup saves preferences as JSON

---

## Architecture

```
extract_usernames/
├── cli.py              # Click CLI with persistent config
├── config.py           # JSON configuration manager
├── prompts.py          # Interactive questionnaire
├── main.py             # Extraction pipeline wrapper
├── notion_sync.py      # Notion synchronization
├── instagram_validator.py  # Username validation
└── notion_manager.py   # Notion API client
```

**Configuration stored at:** `~/.config/extract-usernames/config.json`

---

## Usage Examples

### Interactive Mode (Recommended)
```bash
# First run: complete setup wizard
extract-usernames

# Subsequent runs: uses saved config
extract-usernames

# Change specific settings
extract-usernames --reconfigure directories
extract-usernames --reconfigure extraction
extract-usernames --reconfigure notion
extract-usernames --reconfigure all
```

### Command-Line Flags (Override Config)
```bash
# Specify directories
extract-usernames --input ~/Desktop/leads_jan --output ~/results

# Extraction options
extract-usernames --vlm-model minicpm-v:8b --diagnostics

# Notion sync
extract-usernames --notion-token secret_xxx --notion-db xxx

# Legacy mode
extract-usernames --no-vlm  # EasyOCR-only
```

---

## Notion Integration

### Setup
1. Create a Notion integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Share your database with the integration
3. Run `extract-usernames --reconfigure notion` or provide flags:
   ```bash
   extract-usernames --notion-token secret_xxx --notion-db xxx
   ```

### Database Schema
Your Notion database should have:
- **Brand Name** (Title) - Instagram username
- **Social Media Account** (URL) - Profile link  
- **Status** (Status) - "Didn't Approach", "Approached", etc.
- **Business Type** (Multi-select) - Optional
- **Payment System** (Status) - Optional
- **Amount** (Number) - Optional

---

## Output Files

```
~/Desktop/leads/  (or custom output directory)
├── verified_usernames.md     # High-confidence extractions
├── needs_review.md           # Low-confidence or duplicates
└── extraction_report.md      # Performance metrics
```

---

## Requirements

- **Python 3.9+**
- **Ollama + GLM-OCR** (for VLM mode, recommended)
- **GPU** (optional but significantly faster)

**Install Ollama:**
```bash
# macOS
brew install ollama
ollama pull glm-ocr:bf16

# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama pull glm-ocr:bf16

# Windows
# Download from https://ollama.com/download
ollama pull glm-ocr:bf16
```

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Author

**Rahi Khan** - [Dropout Studio](https://dropout.studio)  
Freelance web developer specializing in SvelteKit and modern web experiences.

---

## Support

- **Issues:** [GitHub Issues](https://github.com/beyourahi/extract_usernames/issues)
- **Documentation:** [CLAUDE.md](CLAUDE.md) - Detailed technical docs
- **Contact:** [@beyourahi](https://github.com/beyourahi)
