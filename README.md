# Instagram Username Extractor

**GPU-accelerated OCR tool that automatically extracts Instagram usernames from screenshots using EasyOCR with real-time verification.**

Fast • Accurate • Universal Hardware Support

---

## ✨ Key Features

- **🚀 GPU Accelerated**: Auto-detects and uses NVIDIA, AMD, Apple Silicon, or Intel GPUs
- **⚡ Blazing Fast**: Process 1000 images in 1-2 minutes with GPU (20-35x faster than CPU-only)
- **🎯 High Accuracy**: Deep learning OCR (EasyOCR) with 60%+ confidence threshold
- **✅ Real-Time Verification**: Checks if usernames exist on Instagram during extraction
- **🔄 Smart Duplicates**: Skips previously extracted usernames across multiple runs
- **📊 Detailed Reports**: Separate lists for verified usernames and those needing review
- **🔧 Zero Config**: Automatically detects and uses best available hardware

---

## 📋 Quick Start

### 1. Install Dependencies

```bash
pip install easyocr torch torchvision opencv-python pillow requests
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

| Hardware                  | 100 Images | 1000 Images | Speed         |
| ------------------------- | ---------- | ----------- | ------------- |
| **Apple Silicon (M1-M5)** | ~6-12 sec  | ~1-2 min    | 20-35x faster |
| **NVIDIA GPU**            | ~6-12 sec  | ~1-2 min    | 20-30x faster |
| **AMD GPU**               | ~10-18 sec | ~2-3 min    | 15-25x faster |
| **CPU Only (8-core)**     | ~30-60 sec | ~5-8 min    | Baseline      |

**First run:** Add 30-60 seconds for model download (one-time only)

---

## 📊 How It Works

```
Screenshot → Crop Username Area → Preprocess Image → GPU/CPU OCR
→ Validate Format → Check Instagram URL → Categorize Result → Save
```

### Processing Pipeline

1. **Load & Crop**: Extracts username region (165px from top, 90px height)
2. **Preprocess**: Denoise, upscale 3x, threshold, clean
3. **OCR Inference**: EasyOCR with GPU acceleration (if available)
4. **Validation**: Checks Instagram username rules (1-30 chars, alphanumeric, dots, underscores)
5. **Verification**: HTTP HEAD request to `instagram.com/username/`
6. **Categorization**:
   - **Verified** (✅): Confidence ≥60% + URL exists
   - **Unverified** (⚠️): Confidence ≥60% + Network error
   - **Review** (⚠️): Confidence <60% or URL doesn't exist
   - **Failed** (❌): No username extracted

---

## 📁 Output Files

### `verified_usernames.md`

Auto-verified usernames ready for immediate use.

```markdown
1. username_one - https://www.instagram.com/username_one
2. username_two - https://www.instagram.com/username_two
```

### `needs_review.md`

Usernames requiring manual verification.

```markdown
1. **uncertain_name** - https://www.instagram.com/uncertain_name
   - **Image:** `screenshot_042.png`
   - Confidence: 55% | URL: ❌

2. **another_user** - https://www.instagram.com/another_user
   - **Image:** `screenshot_089.png`
   - Confidence: 72% | URL: ⚠️ network error
```

### `extraction_report.md`

Performance summary with hardware info, statistics, and metrics.

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
- Skips duplicates automatically
- Appends only new results to files
- Updates totals and timestamps in headers

---

## ⚙️ Configuration

Adjust these values in the script if needed:

```python
TOP_OFFSET = 165      # Distance from top to username area
CROP_HEIGHT = 90      # Height of username region
LEFT_MARGIN = 100     # Left padding to exclude
RIGHT_MARGIN = 100    # Right padding to exclude
```

**When to adjust:**

- Screenshots from different layouts
- Non-standard Instagram UI
- Custom crop requirements

---

## 🔧 Advanced Usage

### Hardware Selection

The script automatically uses the best available hardware:

- Checks for GPU (NVIDIA/AMD/Apple/Intel)
- Falls back to CPU if no GPU found
- Uses max 3 parallel workers (prevents system freeze)

### Debug Mode

First 5 images save preprocessed versions to `~/Desktop/ocr_debug/`:

- View what the OCR "sees"
- Diagnose extraction failures
- Auto-deleted after successful run

---

## 🐛 Troubleshooting

### Installation Issues

```bash
# Reinstall dependencies
pip install --upgrade easyocr torch torchvision opencv-python pillow requests

# macOS SSL issues
/Applications/Python\ 3.XX/Install\ Certificates.command
```

### Low Accuracy

✅ **Check image quality** – Blurry or low-res screenshots reduce accuracy  
✅ **Verify crop area** – Adjust `TOP_OFFSET` and `CROP_HEIGHT` if needed  
✅ **Review debug images** – Check `~/Desktop/ocr_debug/` for first 5 extractions  
✅ **Consistent screenshots** – Use same device/resolution for best results

### Performance Issues

✅ **Computer freezing?** – Script limited to 3 workers (already optimized)  
✅ **Slow processing?** – First run downloads models (~50MB, one-time)  
✅ **GPU not detected?** – Check if PyTorch installed correctly  
✅ **Out of memory?** – Reduce worker count in `detect_hardware()` function

### No Images Found

```bash
# Verify path
ls ~/Desktop/leads_images/

# Check file extensions
# Supported: .jpg, .jpeg, .png, .bmp, .tiff, .webp
```

---

## 🎯 Username Validation Rules

Extracted usernames must match Instagram's format:

- **Length:** 1-30 characters
- **Allowed:** Letters, numbers, periods (`.`), underscores (`_`)
- **Rules:**
  - Must start with alphanumeric
  - Cannot end with period
  - No spaces or special characters

---

## 💡 Tips for Best Results

1. **Use clear screenshots** – Avoid heavily compressed or filtered images
2. **Process in batches** – Similar images (same device) produce consistent results
3. **Review low confidence** – Check `needs_review.md` for potential errors
4. **Clean up processed images** – Remove from input folder after extraction
5. **Check verification status** – URL icons show: ✅ exists, ❌ doesn't exist, ⚠️ network error

---

## 🔒 Privacy & Legal

**Intended for legitimate use:**

- Managing your own follower lists
- Business lead generation from public profiles
- Research with proper consent

**Important:**

- Only checks public profile URLs
- No scraping or data extraction
- No authentication required
- Respects Instagram's public API

⚠️ **Users are responsible for complying with Instagram's Terms of Service and applicable laws.**

---

## 🤝 Contributing

Contributions welcome! Feel free to:

- Report bugs via GitHub Issues
- Submit Pull Requests
- Suggest improvements
- Share feedback

---

## 📄 License

MIT License - Free for personal and commercial use.

---

## 📞 Support

**Having issues?**

1. Check the Troubleshooting section above
2. Review `extraction_report.md` for error details
3. Check debug images (first 5 extractions)
4. Open a GitHub issue with:
   - Python version: `python3 --version`
   - Error message
   - Hardware info from script output

---

## 🚀 What's Next?

After extraction:

1. Review `verified_usernames.md` – Ready to use
2. Check `needs_review.md` – Verify manually
3. Export to CSV if needed
4. Use for your workflow (CRM import, outreach, etc.)
