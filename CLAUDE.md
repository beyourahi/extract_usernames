# Instagram Username Extractor

## Project Overview

Single-file Python CLI tool that extracts Instagram usernames from screenshots using EasyOCR with GPU acceleration. It crops a specific region of each screenshot (where the Instagram username appears), runs OCR, validates the username format, verifies it exists via HTTP HEAD request to instagram.com, and categorizes results into verified/review/failed.

**Project Type**: Single-script Python CLI tool (no framework, no build system, no tests)

## Running

```bash
# Default: reads images from ~/Desktop/leads_images/
python3 extract_usernames.py

# Custom folder on Desktop
python3 extract_usernames.py my_folder

# Absolute path
python3 extract_usernames.py /path/to/images
```

No test suite or build system exists. The project is a single script (`extract_usernames.py`).

## Dependencies

```bash
pip install easyocr torch torchvision opencv-python pillow requests
```

EasyOCR downloads ~50MB of models on first run (cached locally).

## Architecture

Everything lives in `extract_usernames.py`. The processing pipeline:

1. **Hardware detection** (`detect_hardware`) — probes CUDA, MPS (Apple Silicon), falls back to CPU. Determines worker count for multiprocessing.
2. **Image cropping** — uses hardcoded pixel offsets (`TOP_OFFSET=165`, `CROP_HEIGHT=90`, margins of 100px) to extract the username region from Instagram profile screenshots.
3. **Preprocessing** (`preprocess_image`) — grayscale → denoise → 3x upscale → adaptive threshold → morphological close. All via OpenCV.
4. **OCR** (`ocr_extract_username`) — EasyOCR reader (singleton via `get_ocr_reader`), picks highest-confidence result.
5. **Username validation** (`clean_username`) — enforces Instagram rules: 1-30 chars, alphanumeric/dots/underscores, must start alphanumeric, can't end with period.
6. **Verification** (`check_instagram_exists`) — HTTP HEAD to `instagram.com/{username}/`, status 200 = exists.
7. **Categorization** — verified (≥60% confidence + URL exists), unverified (≥60% + network error), review (low confidence or URL 404), failed (no extraction).
8. **Parallel processing** — `multiprocessing.Pool` distributes images across workers. Note: the global `_ocr_reader` singleton does NOT carry across processes; each worker initializes its own reader.
9. **Output** — appends to markdown files in `~/Desktop/leads/`: `verified_usernames.md`, `needs_review.md`, `extraction_report.md`. Tracks existing usernames to skip duplicates across runs.

## Key Constants

The crop region constants at the top of the file are tuned for standard Instagram mobile profile screenshots. If screenshots come from a different layout, these need adjustment:

```python
TOP_OFFSET = 165   # pixels from top to username area
CROP_HEIGHT = 90   # height of crop region
LEFT_MARGIN = 100  # left padding
RIGHT_MARGIN = 100 # right padding
```

## Output Paths

All output goes to `~/Desktop/leads/`. Debug images (first 5 processed) go to `~/Desktop/ocr_debug/` and are deleted after a successful run.

## Repository Etiquette

### Conventional Commits

Use semantic commit messages:

```
feat:     new feature
fix:       bug fix
refactor: code restructuring without behavior change
docs:     documentation changes
chore:    tooling, config, dependencies
perf:     performance improvements
```

### Atomic Commits

- One logical change per commit
- Commit messages should explain WHY, not WHAT
- Keep commits small and focused

## Project-Specific Warnings

### Critical Constraints

1. **Single-file architecture** — Everything lives in `extract_usernames.py`. Do not split into multiple files or create a package structure unless explicitly requested. This is intentionally a single self-contained script.

2. **Crop region constants are fragile** — `TOP_OFFSET`, `CROP_HEIGHT`, `LEFT_MARGIN`, `RIGHT_MARGIN` are pixel-specific to standard Instagram mobile profile screenshots. Changing these affects all extraction accuracy. Never modify without understanding the source screenshot layout.

3. **OCR reader singleton does NOT cross process boundaries** — `_ocr_reader` is a module-level global. Each `multiprocessing.Pool` worker initializes its own reader instance. Do not attempt to share the reader across processes or pass it as an argument.

4. **Instagram verification is rate-limited** — `check_instagram_exists()` makes HTTP HEAD requests to instagram.com. High-volume runs may trigger rate limiting or IP blocks. The bare `except:` clause in that function intentionally catches all network errors and returns `None` (unverified) rather than crashing.

5. **Output files are append-only** — `verified_usernames.md` and `needs_review.md` are designed for incremental appending across multiple runs. The duplicate detection in `load_existing_usernames()` relies on specific markdown formatting patterns (numbered lists with regex). Do not change the output format without updating the corresponding regex patterns.

6. **No input validation on image files** — `cv2.imread()` returns `None` for corrupt/unreadable files, which causes `shape[:2]` to throw. The try/except in `extract_username_from_image` catches this, but error messages may be cryptic.

7. **Worker count capped at 4** — `optimal_workers` is `min(4, max(1, cpu_count() - 1))`. This is intentional to prevent system freezing. Do not increase this cap without understanding memory implications (each worker loads its own EasyOCR model).

8. **Debug directory is auto-deleted** — `~/Desktop/ocr_debug/` is created at module load time and deleted via `shutil.rmtree()` at the end of a successful run. Do not store anything important there.
