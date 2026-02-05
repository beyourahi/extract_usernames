# Instagram Username Extractor

A powerful Python-based OCR tool that automatically extracts Instagram usernames from screenshot images using advanced multi-pass Tesseract OCR with multiple preprocessing techniques.

---

## 🎯 Features

* **Multi-Pass OCR**: Uses 5 different image preprocessing techniques with 3 PSM modes (15 combinations per image)
* **High Accuracy**: Voting system across all preprocessing methods for best results
* **Instagram Verification**: Automatically verifies if extracted usernames exist on Instagram
* **Duplicate Detection**: Intelligently skips already processed usernames across multiple runs
* **Batch Processing**: Process hundreds or thousands of images in one run
* **Detailed Reports**: Generates separate files for verified usernames and those needing review
* **Debug Support**: Saves preprocessed images for first 5 extractions for troubleshooting

---

## 📋 Prerequisites

* Python 3.7 or higher
* Tesseract OCR installed on your system
* macOS (script configured for macOS paths, but can be adapted)

---

## 🔧 Installation

### 1. Install Tesseract OCR

**macOS:**

```bash
brew install tesseract
```

**Ubuntu/Debian:**

```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download and install from: [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

---

### 2. Install Python Dependencies

```bash
pip3 install opencv-python numpy pytesseract pillow requests
```

---

### 3. Clone This Repository

```bash
git clone https://github.com/beyourahi/extract_usernames.git
cd extract_usernames
```

---

## 📸 Image Requirements

The script is designed for Instagram profile screenshots with the following specifications:

* **Username Location**: Top portion of the image (165px from top)
* **Crop Area**: 90px height for username extraction
* **Margins**: 100px left and right margins
* **Supported Formats**: `.png`, `.jpg`, `.jpeg`, `.webp`

### Screenshot Criteria

For best results, your screenshots should:

* Be Instagram profile screenshots showing the username at the top
* Have clear, legible usernames (not blurred or heavily filtered)
* Be in standard Instagram profile resolution
* Have consistent username placement

---

## 🚀 Usage

### 1. Prepare Your Images

Place all your Instagram screenshot images in a folder named `leads_images` on your Desktop:

```
~/Desktop/leads_images/
```

---

### 2. Run the Script

```bash
python3 extract_usernames.py
```

---

### 3. Follow the Prompts

If processing more than 50 images, the script will:

* Show estimated processing time
* Ask for confirmation to continue

---

### 4. Check Results

Results are saved in `~/Desktop/leads/` with three files:

* `verified_usernames.md` – Successfully verified usernames
* `needs_review.md` – Usernames needing manual verification
* `extraction_report.md` – Summary of current extraction run

---

## ⚙️ Configuration

You can modify these constants at the top of the script:

```python
TOP_OFFSET = 165          # Pixels from top to start cropping
CROP_HEIGHT = 90          # Height of the crop area
LEFT_MARGIN = 100         # Left margin to exclude
RIGHT_MARGIN = 100        # Right margin to exclude
CONFIDENCE_THRESHOLD = 60 # Minimum confidence % for auto-verification
```

---

## 📊 Output Files

### `verified_usernames.md`

Contains usernames that:

* Meet the confidence threshold (≥60%)
* Have been verified to exist on Instagram
* Are formatted as a numbered list with clickable links

**Example:**

```markdown
1. username_here - https://www.instagram.com/username_here
2. another_user - https://www.instagram.com/another_user
```

---

### `needs_review.md`

Contains usernames that:

* Have low confidence (<60%)
* Failed Instagram URL verification
* Encountered extraction errors

**Example:**

```markdown
1. **uncertain_name** - https://www.instagram.com/uncertain_name
   - **Image:** `screenshot_001.png`
   - Confidence: 45% | URL: ❌
   - Alternatives: uncertain_name(3), uncertainname(2)
```

---

### `extraction_report.md`

Summary of the current extraction run showing:

* Total images processed
* New verified usernames added
* New usernames needing review
* Duplicates skipped

---

## 🔄 Multiple Runs & Duplicate Handling

The script intelligently handles multiple runs:

* **First Run**: Extracts all usernames
* **Subsequent Runs**:

  * Automatically skips usernames already extracted
  * Appends only new usernames to existing files
  * Updates total counts in file headers
  * Maintains cumulative results across all runs

**Example Workflow:**

```
Run 1: 100 images → 95 verified, 5 need review
Run 2: 200 images (30 duplicates) → +165 verified, +5 need review
Total: 260 verified, 10 need review (30 skipped)
```

---

## 🛠️ How It Works

1. **Image Loading**: Reads images from the input directory
2. **Cropping**: Extracts the username area based on defined offsets
3. **Multi-Pass Preprocessing**: Applies 5 different preprocessing techniques:

   * Adaptive Gaussian Thresholding
   * Otsu's Binarization
   * CLAHE (Contrast Limited Adaptive Histogram Equalization)
   * Bilateral Filtering
   * Adaptive Mean Thresholding
4. **OCR Extraction**: Runs Tesseract with 3 different PSM modes per preprocessing method
5. **Voting System**: Selects the most common result across all attempts
6. **Validation**: Cleans and validates username format
7. **Verification**: Checks if the Instagram profile exists
8. **Duplicate Check**: Compares against existing usernames
9. **Output**: Saves results to appropriate files

---

## 📝 Username Validation Rules

Extracted usernames must meet Instagram's requirements:

* 1–30 characters long
* Contains only letters, numbers, periods (`.`), and underscores (`_`)
* Must start with an alphanumeric character
* Cannot end with a period
* Must contain at least one alphanumeric character

---

## 🐛 Troubleshooting

### "Module not found" Errors

```bash
pip3 install --upgrade opencv-python numpy pytesseract pillow requests
```

### Low Accuracy

* Check if images are properly cropped
* Adjust `TOP_OFFSET` and `CROP_HEIGHT` values
* Verify image quality is sufficient
* Check debug images in `~/Desktop/ocr_debug/` (auto-deleted after run)

### Tesseract Not Found

```bash
brew install tesseract
tesseract --version
```

### SSL Certificate Errors (Instagram Verification)

```bash
/Applications/Python\ 3.XX/Install\ Certificates.command
```

---

## ⚡ Performance

* **Average Processing Time**: ~2–3 seconds per image

**Batch Estimates:**

* 100 images: ~3–5 minutes
* 500 images: ~15–25 minutes
* 1000 images: ~30–50 minutes
* 2000 images: ~60–100 minutes

---

## 🔒 Privacy & Ethics

This tool is designed for legitimate use cases such as:

* Managing your own follower/following lists
* Research and analysis with proper consent
* Business lead generation from public profiles

**Please use responsibly and respect Instagram's Terms of Service.**

---

## 🤝 Contributing

Contributions are welcome. Please feel free to submit a Pull Request.

---

## 📄 License

This project is open source and available under the MIT License.

---

## ⚠️ Disclaimer

This tool is for educational and legitimate business purposes only. Users are responsible for complying with Instagram's Terms of Service and applicable laws. The authors are not responsible for any misuse of this tool.

---

## 💡 Tips for Best Results

1. **Consistent Screenshots**: Use screenshots from the same device/resolution
2. **Clear Images**: Avoid heavily compressed or low-quality images
3. **Batch Processing**: Process similar images together for consistent results
4. **Manual Review**: Always check the `needs_review.md` file and correct as needed
5. **Regular Cleanup**: Delete processed images from `leads_images` folder after extraction

---

## 📞 Support

If you encounter issues or have questions:

1. Check the Troubleshooting section above
2. Review the debug images (first 5 extractions)
3. Open an issue on GitHub with:

   * Your Python version
   * Tesseract version
   * Sample error message
   * Example image (if possible)
