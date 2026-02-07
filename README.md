# Instagram Username Extractor

Extract Instagram usernames from screenshots using **VLM-primary dual-engine architecture** with intelligent consensus validation.

## ✨ Features

- **VLM-Primary Architecture** - Vision Language Model as primary extraction engine
- **Intelligent Consensus** - 5-strategy cross-validation with EasyOCR
- **Enhanced Accuracy** - 95%+ confidence on high-quality extractions
- **Dot Preservation** - Superior handling of dots and underscores
- **GPU Accelerated** - NVIDIA, AMD, Apple Silicon, or CPU
- **Smart Deduplication** - Cross-run duplicate detection
- **Confidence Tiers** - HIGH (≥95%), MED (≥85%), REVIEW (<85%)
- **Cross-Platform** - Windows, macOS, Linux

## 📋 Requirements

- Python 3.9+
- 8GB RAM (16GB recommended for VLM)
- 4GB free disk space
- Ollama + GLM-OCR (installed by setup scripts)

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
   - `verified_usernames.md` - Ready to use (≥85% confidence)
   - `needs_review.md` - Manual verification needed
   - `extraction_report.md` - Processing metrics + engine performance

## 📖 Usage

```bash
# Basic usage (VLM-primary mode, default)
python extract_usernames.py my_screenshots

# Absolute path
python extract_usernames.py /path/to/screenshots

# Custom output directory
python extract_usernames.py images --output /path/to/results

# EasyOCR-only legacy mode (faster, lower accuracy)
python extract_usernames.py images --no-vlm

# Alternative VLM model (for better accuracy on degraded images)
python extract_usernames.py images --vlm-model minicpm-v:8b-2.6-q8_0

# Enable diagnostics (debug images + JSON + consensus decisions)
python extract_usernames.py images --diagnostics
```

**Supported formats:** JPG, PNG, WEBP, BMP, TIFF

## 🔧 How It Works

### VLM-Primary Dual-Engine Architecture (Default)

1. **Crop** - Extracts username region (165px from top, 90px height)
2. **VLM Primary Extraction** - GLM-OCR reads raw image holistically (preserves dots/underscores)
3. **EasyOCR Cross-Validation** - 3 preprocessing variants (balanced, aggressive, minimal) with weighted voting
4. **Intelligent Consensus** - 5 reconciliation strategies:
   - **Exact Agreement** - Both engines match → confidence +5% (capped at 95%)
   - **Dot Reconciliation** - Differ only by dots/underscores → prefer VLM version
   - **Confusion Correction** - Known OCR patterns (tf→ff, rn→m) → prefer corrected
   - **Minor Edit Distance** (≤2) - Prefer longer version (preserves dropped chars)
   - **Significant Disagreement** (>2) - Flag for review, use higher confidence engine
5. **Categorize** - Routes to verified (≥85%) or review (<85%)

### EasyOCR-Only Legacy Mode (`--no-vlm`)

1. **Crop** - Same username region extraction
2. **Multi-Pass OCR** - 3 preprocessing variants with weighted voting
3. **Cross-Variant Corrections** - Dot reconciliation, confusion pattern fixes
4. **Categorize** - Same confidence tiers (95%/85%)

**Note:** The script expects Instagram's standard mobile screenshot layout. Use `--diagnostics` if extractions fail.

## 📊 Performance

**VLM-Primary Mode (Default):**
- Speed: ~0.5-2 images/second
- Accuracy: 95%+ on clean screenshots
- Best for: Maximum accuracy, dot/underscore preservation
- Workers: 2 (memory constraint)

**EasyOCR-Only Mode (`--no-vlm`):**
- Speed: ~5-15 images/second
- Accuracy: 85%+ on clean screenshots
- Best for: Speed-critical workflows, bulk processing
- Workers: 6 (parallel processing)

## 🛠️ Troubleshooting

**Python not found**
- Try `python3` instead of `python`
- Reinstall from [python.org](https://www.python.org/downloads/)

**Dependencies fail to install**
- Re-run setup script
- Try: `pip install --user -r requirements.txt`

**Ollama not running**
- Start: `ollama serve`
- Or use: `--no-vlm` flag for EasyOCR-only mode

**Model not found**
```bash
ollama pull glm-ocr:bf16
```

**Low accuracy**
- Verify crop region with `--diagnostics`
- Check consensus decisions in `{image}_consensus.json`
- Ensure clear, unblurred screenshots
- Screenshots must use Instagram's standard layout
- Try alternative VLM model for degraded images

**Slow processing**
- Check GPU detection in `extraction_report.md`
- VLM-primary is intentionally slower (0.5-2 img/sec) for accuracy
- Use `--no-vlm` for 5-10x faster processing

**Memory issues**
- VLM mode uses 2 workers (vs 6 for EasyOCR-only)
- Close other applications
- Use smaller VLM model (glm-ocr:bf16 is smallest at 2.2GB)

## 🔬 VLM Model Alternatives

Default `glm-ocr:bf16` is recommended (lightweight, fast, OCR-optimized). For challenging images:

**MiniCPM-V 2.6** (~8.5GB) - Best for complex/blurry/watermarked images:
```bash
ollama pull minicpm-v:8b-2.6-q8_0
python extract_usernames.py images --vlm-model minicpm-v:8b-2.6-q8_0
```

**Qwen2.5-VL-7B** (~6GB) - All-rounder, excellent document understanding:
```bash
ollama pull qwen2.5-vl:7b
python extract_usernames.py images --vlm-model qwen2.5-vl:7b
```

⚠️ Larger models are slower but provide better accuracy on degraded images.

## ❓ FAQ

**Q: Why is VLM-primary mode slower?**  
A: VLM processes images holistically (preserves dots/underscores) and runs dual-engine consensus for maximum accuracy. Speed: 0.5-2 img/sec vs 5-15 img/sec EasyOCR-only. Use `--no-vlm` for faster processing.

**Q: Can I process non-Instagram screenshots?**  
A: Only if usernames appear at 165px from top. Optimized for Instagram's mobile layout.

**Q: Does this work offline?**  
A: Yes, after initial downloads everything runs locally.

**Q: Is GPU required?**  
A: No, but GPU is 5-10x faster. VLM benefits most from GPU acceleration.

**Q: How accurate is it?**  
A: VLM-primary: >95% auto-verified on clean screenshots. EasyOCR-only: >85%.

**Q: Privacy?**  
A: Everything runs locally. No cloud API calls. Ollama runs on localhost.

**Q: Can I process thousands of images?**  
A: Yes. VLM-primary: ~0.5-2 img/sec. EasyOCR-only: ~5-15 img/sec. Choose based on accuracy vs speed needs.

**Q: What's the consensus validator?**  
A: When VLM and EasyOCR disagree, 5 strategies reconcile differences:
1. Exact agreement (highest confidence)
2. Dot/underscore reconciliation (prefer VLM)
3. Known OCR confusion corrections (tf→ff, rn→m, etc.)
4. Minor differences (prefer longer version)
5. Major disagreements (flag for review)

**Q: When should I use `--no-vlm`?**  
A: Use EasyOCR-only mode when:
- Processing thousands of images (speed matters)
- Memory constraints (<8GB RAM)
- Ollama/VLM not available
- Usernames don't contain dots/underscores

## 🤝 Contributing

Contributions welcome! Follow [conventional commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.).

Submit issues: [GitHub Issues](https://github.com/beyourahi/extract_usernames/issues)

## 📄 License

MIT License - See LICENSE file for details.