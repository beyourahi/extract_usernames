# Instagram Username Extractor

Extract Instagram usernames from screenshots using advanced OCR and AI vision models.

## ✨ Features

- **Multi-Pass OCR** - 3 preprocessing variants with weighted voting
- **AI Vision** - Optional GLM-OCR for verification and rescue
- **GPU Accelerated** - NVIDIA, AMD, Apple Silicon, or CPU
- **Smart Deduplication** - Cross-run duplicate detection
- **Confidence Tiers** - HIGH (≥90%), MED (≥80%), REVIEW (<80%)
- **Cross-Platform** - Windows, macOS, Linux

## 📋 Requirements

- Python 3.9+
- 8GB RAM (16GB recommended)
- 2GB free disk space
- Ollama (optional, for AI features)

## 🚀 Installation

**Windows:**
```powershell
.\setup.ps1
```

**macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

The setup script automatically installs Python dependencies (~2-3GB), Ollama, and the GLM-OCR model (~2.2GB).

**Verify installation:**
```bash
python extract_usernames.py --help
```

## ⚡ Quick Start

1. Place Instagram screenshots in a folder on your Desktop (e.g., `my_screenshots`)

2. Run:
   ```bash
   python extract_usernames.py my_screenshots
   ```

3. Check results in `~/Desktop/leads/`:
   - `verified_usernames.md` - Ready to use
   - `needs_review.md` - Manual verification needed
   - `extraction_report.md` - Processing metrics

## 📖 Usage

```bash
# Basic usage
python extract_usernames.py my_screenshots

# Absolute path
python extract_usernames.py /path/to/screenshots

# Custom output directory
python extract_usernames.py images --output /path/to/results

# EasyOCR only (no AI vision)
python extract_usernames.py images --no-vlm

# Alternative VLM model
python extract_usernames.py images --vlm-model minicpm-v:8b-2.6-q8_0

# Enable diagnostics (debug images + JSON)
python extract_usernames.py images --diagnostics
```

**Supported formats:** JPG, PNG, WEBP, BMP, TIFF

## 🔧 How It Works

1. **Crop** - Extracts username region (165px from top, 90px height)
2. **Preprocess** - 3 variants (balanced, aggressive, minimal)
3. **OCR** - EasyOCR reads variants, votes on best result
4. **Corrections** - Dot reconciliation, OCR confusion fixes, segment merging
5. **AI Verification** - GLM-OCR provides second opinion (optional)
6. **Categorize** - Routes to verified (≥80%) or review (<80%)

**Note:** The script expects Instagram's standard mobile screenshot layout. Use `--diagnostics` if extractions fail.

## 🛠️ Troubleshooting

**Python not found**
- Try `python3` instead of `python`
- Reinstall from [python.org](https://www.python.org/downloads/)

**Dependencies fail to install**
- Re-run setup script
- Try: `pip install --user -r requirements.txt`

**Ollama not running**
- Start: `ollama serve`
- Or use: `--no-vlm` flag

**Model not found**
```bash
ollama pull glm-ocr:bf16
```

**Low accuracy**
- Verify crop region with `--diagnostics`
- Ensure clear, unblurred screenshots
- Screenshots must use Instagram's standard layout

**Slow processing**
- Check GPU detection in `extraction_report.md`
- Use `--no-vlm` for faster processing

## 🔬 VLM Model Alternatives

Default `glm-ocr:bf16` is recommended (lightweight, fast). For degraded images or higher accuracy needs:

**MiniCPM-V 2.6** (8GB) - Better for complex/blurry images:
```bash
ollama pull minicpm-v:8b-2.6-q8_0
python extract_usernames.py images --vlm-model minicpm-v:8b-2.6-q8_0
```

**Qwen2.5-VL-7B** (6GB) - All-rounder, good balance:
```bash
ollama pull qwen2.5vl:7b
python extract_usernames.py images --vlm-model qwen2.5vl:7b
```

⚠️ Larger models are slower and reduce parallel workers (2 vs 6).

## ❓ FAQ

**Q: Can I process non-Instagram screenshots?**  
A: Only if usernames appear at 165px from top. Optimized for Instagram's mobile layout.

**Q: Does this work offline?**  
A: Yes, after initial downloads everything runs locally.

**Q: Is GPU required?**  
A: No, but GPU is 5-10x faster.

**Q: How accurate is it?**  
A: >85% auto-verified on clean screenshots.

**Q: Privacy?**  
A: Everything runs locally. No cloud API calls.

**Q: Can I process thousands of images?**  
A: Yes. Speed: ~5-15 images/second depending on hardware.

## 🤝 Contributing

Contributions welcome! Follow [conventional commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.).

Submit issues: [GitHub Issues](https://github.com/beyourahi/extract_usernames/issues)

## 📄 License

MIT License - See LICENSE file for details.