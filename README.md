# Instagram Username Extractor

Extract Instagram usernames from screenshots using advanced OCR and AI vision models.

**🎯 Perfect for**: Marketers, social media managers, lead generators, and anyone who needs to quickly extract usernames from Instagram screenshots.

## ✨ Features

- **🔄 Multi-Pass OCR** - 3 preprocessing variants with intelligent weighted voting for maximum accuracy
- **🤖 AI Vision Model** - Optional GLM-OCR integration for double-checking and rescuing failed extractions
- **⚡ GPU Acceleration** - Automatic detection and optimization for NVIDIA, AMD, Apple Silicon, or CPU
- **🔍 Smart Duplicate Detection** - Cross-run deduplication prevents re-processing existing usernames
- **📊 Confidence Tiers** - AUTO (≥90%), VERIFIED (≥80%), REVIEW (<80%) with clear categorization
- **🎯 Advanced Corrections** - Dot reconciliation, OCR confusion pattern fixes, segment concatenation
- **💻 Cross-Platform** - Works seamlessly on Windows, macOS, and Linux
- **🚀 Parallel Processing** - Automatic worker optimization for fastest possible extraction

## 📋 System Requirements

**Minimum**:
- 8GB RAM
- 2GB free disk space
- Python 3.9+
- Windows 10/11, macOS 11+, or Ubuntu 20.04+

**Recommended**:
- 16GB RAM
- GPU with 4GB+ VRAM
- Python 3.11+
- Ollama installed (for AI vision features)

> **💡 Note**: You can run EasyOCR-only mode with `--no-vlm` flag if you skip Ollama installation.

## 🚀 Installation

### Quick Setup (Recommended)

Use our automated setup scripts:

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
# Download and run setup script
.\setup.ps1
```

The script will automatically:
- ✅ Check Python 3.9+ installation
- ✅ Install all dependencies (~2-3GB download)
- ✅ Detect/install Ollama
- ✅ Download GLM-OCR model (~2.2GB)
- ✅ Validate installation

</details>

<details>
<summary><b>macOS</b></summary>

```bash
# Download and run setup script
chmod +x setup.sh
./setup.sh
```

The script will automatically:
- ✅ Check Python 3.9+ installation
- ✅ Install all dependencies (~2-3GB download)
- ✅ Detect/install Ollama via Homebrew
- ✅ Download GLM-OCR model (~2.2GB)
- ✅ Validate installation

</details>

<details>
<summary><b>Linux (Ubuntu/Debian)</b></summary>

```bash
# Download and run setup script
chmod +x setup.sh
./setup.sh
```

The script will automatically:
- ✅ Check Python 3.9+ installation
- ✅ Offer virtual environment creation (recommended)
- ✅ Install all dependencies (~2-3GB download)
- ✅ Detect/install Ollama
- ✅ Download GLM-OCR model (~2.2GB)
- ✅ Validate installation

</details>

### Verify Installation

Check that everything is working:

```bash
python extract_usernames.py --help
```

You should see the usage instructions without any errors.

## 🎬 Quick Start

1. **Prepare your screenshots** - Place Instagram screenshots in a folder on your Desktop (e.g., `my_screenshots`)

2. **Run the extractor**:
   ```bash
   python extract_usernames.py my_screenshots
   ```

3. **Find your results** - Check `~/Desktop/leads/` for output files:
   - **`verified_usernames.md`** - Ready-to-use usernames (copy to spreadsheet/CRM)
   - **`needs_review.md`** - Usernames requiring manual verification
   - **`extraction_report.md`** - Performance metrics and processing summary

**That's it!** ✅ Your extracted usernames are ready to use.

## 📖 Usage

### Basic Usage

```bash
# Process images in folder (relative to Desktop)
python extract_usernames.py my_screenshots

# Process images using absolute path
python extract_usernames.py /path/to/screenshots
```

### Advanced Options

```bash
# Custom output directory
python extract_usernames.py images --output /path/to/results

# Enable diagnostics (saves debug images and JSON)
python extract_usernames.py images --diagnostics

# Run without AI vision model (EasyOCR only)
python extract_usernames.py images --no-vlm

# Use alternative VLM model
python extract_usernames.py images --vlm-model minicpm-v:8b-2.6-q8_0
```

### Input Requirements

- **Formats**: JPG, PNG, WEBP, BMP, TIFF
- **Layout**: Instagram username must be visible in standard position (165px from top)
- **Quality**: Clear, unblurred screenshots work best

### Output Files

**verified_usernames.md** - Auto-verified with confidence scores:
```markdown
1. johndoe - https://www.instagram.com/johndoe [HIGH 95%]
2. jane_smith - https://www.instagram.com/jane_smith [MED 87%]
```

**needs_review.md** - Requires manual checking:
```markdown
1. **uncertain_name** - https://www.instagram.com/uncertain_name
   - **Image:** `screenshot_001.png`
   - Confidence: 72% | Quality: 0.54
   - **Near-duplicate of:** similar_name (edit distance: 2)
```

**extraction_report.md** - Processing summary with metrics and hardware info.

## 🔧 How It Works

The extraction pipeline uses a multi-stage approach:

1. **📸 Crop** - Extracts username region (165px from top, 90px height)
2. **🎨 Preprocess** - Runs 3 variants:
   - **Balanced**: CLAHE + bilateral filter + adaptive threshold
   - **Aggressive**: Strong CLAHE + Otsu threshold + morphological closing
   - **Minimal**: Fast denoising + adaptive threshold
3. **👁️ OCR** - EasyOCR reads each variant, votes on best result (aggressive gets 2x weight)
4. **🔧 Corrections** - Applies:
   - Dot reconciliation (dots vs 'o' confusion)
   - Known OCR patterns (tf→ff, rn→m, vv→w, etc.)
   - Segment merging for split usernames
5. **🤖 AI Verification** - GLM-OCR provides second opinion:
   - **Agrees**: Boosts confidence to 90%+
   - **Minor differences** (≤2 chars): Uses longer version, 85% confidence
   - **Major differences**: Overrides with AI result, 85% confidence
   - **Fails**: Uses EasyOCR result only
6. **📊 Categorize** - Routes to verified or review based on confidence:
   - **HIGH** (90%+): Auto-verified, high quality
   - **MED** (80-89%): Auto-verified, medium quality  
   - **REVIEW** (<80%): Manual verification needed

### Why Crop Region Matters

**The script expects Instagram's standard mobile screenshot layout**. The username appears at a consistent position, so we crop to that specific region for accurate extraction.

**If your screenshots have a different layout**, extractions may fail. Use `--diagnostics` to see debug images and verify the crop region captures the username.

### When AI Vision Helps

- **Rescue mode**: When EasyOCR fails completely, AI tries to extract
- **Validation**: When EasyOCR is uncertain, AI provides second opinion
- **Special characters**: AI better preserves dots and underscores

## 🔍 Troubleshooting

### Python not found
**Symptom**: `python: command not found`

**Solution**:
- Check Python is in PATH
- Try `python3` instead of `python`
- Reinstall from [python.org](https://www.python.org/downloads/)

### pip install fails
**Symptom**: `ERROR: Could not install packages`

**Solution**:
- Try `pip3` instead of `pip`
- Use `--user` flag: `pip install --user -r requirements.txt`
- Check internet connection
- Re-run the setup script for your platform

### Ollama not running
**Symptom**: `Ollama server not running`

**Solution**:
- Start Ollama: `ollama serve`
- Check if running as system service
- Fallback: Use `--no-vlm` flag for EasyOCR-only mode

### Model not found
**Symptom**: `Model not found. Run: ollama pull glm-ocr:bf16`

**Solution**:
```bash
ollama pull glm-ocr:bf16
# Wait for download (~2.2GB)
```

### Low accuracy
**Symptom**: Many usernames go to review file

**Solution**:
- Verify screenshots match expected crop region
- Run with `--diagnostics` to see debug images
- Check crop region captures username properly
- Ensure screenshots are clear and unblurred

### Slow processing
**Symptom**: Takes too long per image

**Solution**:
- Check GPU is detected (see extraction_report.md for device info)
- Reduce worker count if running out of memory
- Use `--no-vlm` for faster processing (EasyOCR only)
- Close other GPU-intensive applications

### Out of memory
**Symptom**: Process crashes with memory error

**Solution**:
- Use `--no-vlm` flag (reduces VRAM usage)
- Process fewer images at once
- Close other applications
- Upgrade RAM/VRAM if possible

## 🔬 Advanced: VLM Model Alternatives

> **💡 Note**: `glm-ocr:bf16` is the recommended default for Instagram username extraction. It's optimized for OCR tasks, lightweight (2.2GB), and fast.

### When to Consider Alternatives

- Processing degraded/blurry images where GLM-OCR struggles
- Need multilingual username support beyond English
- Have powerful hardware (16GB+ RAM, 8GB+ VRAM)
- Require >95% auto-verification rate

### Alternative Models

**Option 1: MiniCPM-V 2.6** (8GB)
- General-purpose vision model
- Better for complex/degraded images
- 4x larger, slower inference
- Good for challenging extractions

**Option 2: Qwen2.5-VL-7B** (6GB)
- General-purpose, all-rounder
- 3x larger than GLM-OCR
- Good balance of capabilities
- Overkill for clean screenshots

### Using Alternative Models

1. **Download the model**:
   ```bash
   ollama pull minicpm-v:8b-2.6-q8_0
   # or
   ollama pull qwen2.5vl:7b
   ```

2. **Run with the model**:
   ```bash
   python extract_usernames.py my_images --vlm-model minicpm-v:8b-2.6-q8_0
   ```

3. **Test with sample images** to compare accuracy:
   ```bash
   # Default GLM-OCR
   python extract_usernames.py test_images
   
   # Alternative model
   python extract_usernames.py test_images --vlm-model minicpm-v:8b-2.6-q8_0
   ```

> **⚠️ Warning**: Larger models require more VRAM and reduce parallel processing capability (2 workers max vs 6 workers).

## ❓ FAQ

**Q: Why do some usernames need review?**  
A: Low confidence (<80%), poor image quality, or near-duplicates are flagged for manual verification to prevent false positives.

**Q: Can I process non-Instagram screenshots?**  
A: Only if the username appears at the same position (165px from top). The script is optimized for Instagram's standard mobile layout.

**Q: Does this work offline?**  
A: Yes! After initial downloads (Python packages, Ollama, GLM-OCR model), everything runs locally without internet.

**Q: Is GPU required?**  
A: No, it runs on CPU. GPU makes it 5-10x faster though.

**Q: How accurate is it?**  
A: Typically >85% auto-verified on clean screenshots. Accuracy depends on image resolution, lighting, and clarity.

**Q: What about privacy?**  
A: Everything runs locally on your machine. No cloud API calls, no data leaves your computer.

**Q: Can I process thousands of images?**  
A: Yes! The parallel processing handles large batches efficiently. Processing speed: ~5-15 images/second depending on hardware.

**Q: What if I have duplicates across multiple runs?**  
A: The script automatically detects and skips exact duplicates. Near-duplicates (similar names) are flagged for review.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

- **Commit format**: Use [conventional commits](https://www.conventionalcommits.org/)
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation
  - `chore:` for maintenance
  - `refactor:` for code improvements

- **Testing**: Test on multiple platforms (Windows, macOS, Linux) before submitting

- **Architecture**: The single-file design is intentional for portability. Please maintain this in PRs.

- **Issues**: Submit feature requests and bug reports via [GitHub Issues](https://github.com/beyourahi/extract_usernames/issues)

## 📄 License

MIT License - See LICENSE file for details.

---

Having issues? [Open an issue](https://github.com/beyourahi/extract_usernames/issues) • Questions? Check the [FAQ](#-faq) above