# Instagram Username Extractor

**GPU-accelerated OCR tool that automatically extracts Instagram usernames from screenshots using EasyOCR with real-time verification.**

Fast - Accurate - Universal Hardware Support

---

## ✨ Key Features

- **🚀 GPU Accelerated**: Auto-detects and uses NVIDIA CUDA, AMD ROCm, or Apple Silicon (MPS)
- **⚡ Blazing Fast**: Process 1000 images in 1-2 minutes with GPU (20-35x faster than CPU-only)
- **🎯 High Accuracy**: Deep learning OCR (EasyOCR) with 60%+ confidence threshold
- **✅ Real-Time Verification**: Checks if usernames exist on Instagram during extraction
- **🔄 Smart Duplicates**: Skips previously extracted usernames across multiple runs
- **📊 Detailed Reports**: Separate lists for verified usernames and those needing review
- **🔧 Zero Config**: Automatically detects and uses best available hardware
- **🔇 Silent Mode**: Suppresses unnecessary warnings for clean output

---

## 📋 Quick Start

### 1. Install Dependencies

```bash
pip install easyocr torch torchvision opencv-python pillow requests numpy
```

**That's it!** No additional setup needed. The script will:

- Download OCR models on first run (~50MB, cached locally)
- Auto-detect your GPU or use CPU
- Work on macOS, Linux, and Windows

### 2. Prepare Your Screenshots

Place Instagram profile screenshots in `~/Desktop/leads_images/`

### 3. Run the Script

```bash
python3 extract_usernames.py
```

Or specify a custom folder:

```bash
python3 extract_usernames.py my_folder          # Uses ~/Desktop/my_folder
python3 extract_usernames.py /path/to/images   # Uses absolute path
```

### 4. Check Results

Results saved in `~/Desktop/leads/`:

- **`verified_usernames.md`** – Ready to use (high confidence + URL verified)
- **`needs_review.md`** – Manual review needed (low confidence or URL issues)
- **`extraction_report.md`** – Performance summary and statistics

---

## 🎯 Screenshot Requirements

The script works best with **Instagram profile screenshots** showing:

- Username clearly visible at the top
- Standard Instagram layout (mobile or desktop)
- Clear, unblurred text

**Supported formats:** `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp`

**Tip:** Screenshots from the same device/resolution produce most consistent results.

---

## ⚡ Performance

### Processing Speed by Hardware

| Hardware                  | 100 Images | 1000 Images | Speed         | Workers |
| ------------------------- | ---------- | ----------- | ------------- | ------- |
| **Apple Silicon (M1-M4)** | ~6-12 sec  | ~1-2 min    | 20-35x faster | 4-10    |
| **NVIDIA GPU (CUDA)**     | ~6-12 sec  | ~1-2 min    | 20-30x faster | 4-10    |
| **AMD GPU (ROCm)**        | ~10-18 sec | ~2-3 min    | 15-25x faster | 4-8     |
| **CPU Only (8-core)**     | ~30-60 sec | ~5-8 min    | Baseline      | 3-4     |

**First run:** Add 30-60 seconds for model download (one-time only)

**Note:** Script automatically adjusts worker count based on CPU cores (max: cpu_count - 1, min: 1, default: 4)

---

## 📊 How It Works

```
Screenshot → Crop Username Area → Preprocess Image → GPU/CPU OCR
→ Validate Format → Check Instagram URL → Categorize Result → Save
```

### Processing Pipeline

1. **Hardware Detection**: Auto-detects CUDA, MPS (Apple Silicon), or CPU
2. **Load & Crop**: Extracts username region (165px from top, 90px height)
3. **Preprocess**: Denoise, upscale 3x, threshold, morphological operations
4. **OCR Inference**: EasyOCR with GPU acceleration (if available)
5. **Validation**: Checks Instagram username rules (1-30 chars, alphanumeric, dots, underscores)
6. **Verification**: HTTP HEAD request to `instagram.com/username/`
7. **Categorization**:
   - **Verified** (✅): Confidence ≥60% + URL exists
   - **Unverified** (⚠️): Confidence ≥60% + Network error
   - **Review** (⚠️): Confidence <60% or URL doesn't exist
   - **Failed** (❌): No username extracted
   - **Duplicate** (⏭️): Already extracted in previous runs

---

## 📁 Output Files

### `verified_usernames.md`

Auto-verified usernames ready for immediate use.

```markdown
# Verified Instagram Usernames

**Last Updated:** February 6, 2026 at 10:30 AM
**Total:** 92

---

1. username_one - https://www.instagram.com/username_one
2. username_two - https://www.instagram.com/username_two
```

### `needs_review.md`

Usernames requiring manual verification.

```markdown
# Usernames Needing Manual Review

**Last Updated:** February 6, 2026 at 10:30 AM
**Total:** 8

---

1. **uncertain_name** - https://www.instagram.com/uncertain_name
   - **Image:** `screenshot_042.png`
   - Confidence: 55% | URL: ❌

2. **another_user** - https://www.instagram.com/another_user
   - **Image:** `screenshot_089.png`
   - Confidence: 72% | URL: ⚠️
```

### `extraction_report.md`

Performance summary with hardware info, statistics, and metrics.

```markdown
# Instagram Username Extraction Report

**Generated:** February 6, 2026 at 10:30 AM

---

## Hardware Configuration

- **Device:** Apple M2 GPU
- **GPU Available:** Yes
- **GPU Type:** Apple Metal (MPS)
- **Worker Processes:** 4

## Results Summary

- ✅ **Verified:** 92 (92.0%)
- ⚠️ **Needs Review:** 8 (8.0%)
- ❌ **Failed:** 0 (0.0%)
- ⏭️ **Duplicates:** 0 (0.0%)

## Performance Metrics

- **Total Time:** 12.34 seconds
- **Processing Speed:** 8.10 images/second
- **Average Confidence:** 87.5%
```

---

## 🔄 Multiple Runs & Incremental Processing

Run the script multiple times without duplicating results:

```
Run 1: 100 images → 92 verified, 8 review
Run 2: 200 images → +165 verified, +12 review (23 duplicates skipped)
Run 3: 150 images → +130 verified, +5 review (15 duplicates skipped)

Total: 387 verified, 25 review
```

**How it works:**

- Loads existing usernames from previous runs
- Skips duplicates automatically (shows ⏭️ icon)
- Appends only new results to files
- Updates totals and timestamps in headers

---

## ⚙️ Configuration

Adjust these values in the script if needed:

```python
TOP_OFFSET = 165      # Distance from top to username area (pixels)
CROP_HEIGHT = 90      # Height of username region (pixels)
LEFT_MARGIN = 100     # Left padding to exclude (pixels)
RIGHT_MARGIN = 100    # Right padding to exclude (pixels)
```

**When to adjust:**

- Screenshots from different layouts (e.g., desktop vs mobile)
- Non-standard Instagram UI versions
- Custom crop requirements for specific use cases

**Worker Count:**

By default, the script uses `min(4, cpu_count - 1)` workers. To change:

```python
# In detect_hardware() function:
'optimal_workers': min(4, max(1, cpu_count() - 1))  # Change 4 to your preference
```

**Safety:** Using more workers (e.g., 10) won't damage hardware but may cause:

- Higher CPU/GPU temperatures
- Louder fans
- Automatic thermal throttling (macOS protects itself)

---

## 🔧 Advanced Usage

### Hardware Selection

The script automatically uses the best available hardware in this priority order:

1. **NVIDIA CUDA** (if `torch.cuda.is_available()`)
2. **Apple Metal (MPS)** (if `torch.backends.mps.is_available()`)
3. **CPU fallback** (if no GPU detected)

Hardware info printed at startup:

```
🔍 Detecting hardware...

   Device: Apple M2 GPU
   GPU: ✅ Apple Metal (MPS)
   Workers: 4 parallel processes
```

### Debug Mode

First 5 images save preprocessed versions to `~/Desktop/ocr_debug/`:

- View what the OCR "sees" after preprocessing
- Diagnose extraction failures
- Auto-deleted after successful run

**Tip:** If accuracy is low, check debug images to verify cropping is correct.

---

## 🐛 Troubleshooting

### Installation Issues

```bash
# Reinstall dependencies
pip install --upgrade easyocr torch torchvision opencv-python pillow requests numpy

# macOS SSL issues
/Applications/Python\ 3.XX/Install\ Certificates.command

# If EasyOCR fails to download models
pip install --upgrade easyocr --no-cache-dir
```

### Warnings During Execution

**"pin_memory not supported on MPS"** warnings are harmless and automatically suppressed. If you still see them, ensure the script starts with:

```python
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.data.dataloader')
```

### Low Accuracy

✅ **Check image quality** – Blurry or low-res screenshots reduce accuracy  
✅ **Verify crop area** – Adjust `TOP_OFFSET` and `CROP_HEIGHT` if needed  
✅ **Review debug images** – Check `~/Desktop/ocr_debug/` for first 5 extractions  
✅ **Consistent screenshots** – Use same device/resolution for best results  
✅ **Username visibility** – Ensure username is in the top 165-255px region

### Performance Issues

✅ **Slow first run?** – Models download once (~50MB, cached for future use)  
✅ **GPU not detected?** – Verify PyTorch installation: `python -c "import torch; print(torch.cuda.is_available() or torch.backends.mps.is_available())"`  
✅ **Out of memory?** – Reduce worker count in `detect_hardware()` function  
✅ **Computer overheating?** – Use fewer workers (default 4 is safe) or ensure good ventilation  
✅ **Network errors for verification?** – Instagram may rate-limit; results marked as ⚠️ (unverified)

### No Images Found

```bash
# Verify path
ls ~/Desktop/leads_images/

# Check file extensions
# Supported: .jpg, .jpeg, .png, .bmp, .tiff, .webp

# Try absolute path
python3 extract_usernames.py /absolute/path/to/images
```

---

## 🎯 Username Validation Rules

Extracted usernames must match Instagram's format:

- **Length:** 1-30 characters
- **Allowed:** Letters, numbers, periods (`.`), underscores (`_`)
- **Rules:**
  - Must start with alphanumeric character
  - Cannot end with period
  - No spaces or special characters (automatically removed)
  - Consecutive periods/underscores are cleaned

**Example transformations:**

- `_username.` → `username`
- `user  name` → `username`
- `@username` → `username`

---

## 💡 Tips for Best Results

1. **Use clear screenshots** – Avoid heavily compressed, filtered, or low-resolution images
2. **Process in batches** – Similar images (same device/zoom) produce consistent results
3. **Review low confidence** – Check `needs_review.md` for potential OCR errors
4. **Clean up processed images** – Remove from input folder after successful extraction
5. **Check verification status** – URL icons show: ✅ exists, ❌ doesn't exist, ⚠️ network error
6. **Keep laptop plugged in** – Heavy GPU usage drains battery quickly
7. **Run during idle time** – GPU-intensive, may slow down other tasks
8. **Monitor first 5 extractions** – Debug images help identify cropping issues early

---

## 🔒 Privacy & Legal

**Intended for legitimate use:**

- Managing your own follower/following lists
- Business lead generation from public profiles
- Market research with proper consent
- Personal contact management

**What this tool does:**

- Processes screenshots you manually captured
- Checks public profile URLs (no login required)
- Extracts only usernames (no personal data)
- No API calls to Instagram (uses HTTP HEAD requests only)

**What this tool does NOT do:**

- ❌ Scrape Instagram data
- ❌ Access private profiles
- ❌ Store personal information
- ❌ Automate Instagram interactions
- ❌ Violate rate limits (respects 5-second timeouts)

⚠️ **Users are responsible for complying with Instagram's Terms of Service, GDPR, and applicable laws. Use responsibly and ethically.**

---

## 🤝 Contributing

Contributions welcome! Feel free to:

- Report bugs via GitHub Issues
- Submit Pull Requests
- Suggest improvements or new features
- Share feedback and use cases

**Development setup:**

```bash
git clone https://github.com/yourusername/instagram-username-extractor
cd instagram-username-extractor
pip install -r requirements.txt
python3 extract_usernames.py
```

---

## 📄 License

MIT License - Free for personal and commercial use.

---

## 📞 Support

**Having issues?**

1. Check the **Troubleshooting** section above
2. Review `extraction_report.md` for error details and hardware info
3. Check debug images in `~/Desktop/ocr_debug/` (first 5 extractions)
4. Open a GitHub issue with:
   - Python version: `python3 --version`
   - PyTorch version: `python3 -c "import torch; print(torch.__version__)"`
   - Error message (full traceback)
   - Hardware info from script output
   - Sample screenshot (if possible)

---

## 🚀 What's Next?

After extraction:

1. **Review verified list** – `verified_usernames.md` is ready to use
2. **Manual verification** – Check `needs_review.md` for low-confidence extractions
3. **Export to CSV** – Copy usernames to seadsheet for CRM import
4. **Workflow integration** – Use for outreach campaigns, analytics, or lead generation
5. **Run incrementally** – Process new batches anytime; duplicates are auto-skipped

---
