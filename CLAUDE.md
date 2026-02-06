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
3. **Multi-pass preprocessing** — three variants run on each image:
   - `preprocess_balanced` — CLAHE → bilateral filter → 3x LANCZOS4 upscale → median blur → adaptive threshold → morphological close
   - `preprocess_aggressive` — CLAHE (high clip) → 4x LANCZOS4 upscale → Otsu threshold → morphological close (larger kernel)
   - `preprocess_minimal` — grayscale → 3x LANCZOS4 upscale → denoise → mean-based adaptive threshold
4. **Multi-pass OCR with voting** (`ocr_extract_username`) — EasyOCR reader (singleton via `get_ocr_reader`) runs on all 3 preprocessing variants. If 2+ passes agree on a username, that consensus result is used. Otherwise the highest-confidence single result wins.
5. **Username validation** (`clean_username`) — enforces Instagram rules: 1-30 chars, alphanumeric/dots/underscores, must start alphanumeric, can't end with period.
6. **Character confusion correction** (`generate_username_candidates`) — generates up to 10 variants of the OCR result by substituting commonly confused characters (l/1/i, o/0, rn/m, vv/w, cl/d, ii/u). Each candidate is checked against Instagram before falling back to the original.
7. **Image quality scoring** (`calculate_image_quality`, `adjust_confidence`) — measures sharpness (Laplacian variance), contrast (std deviation), and brightness consistency. Adjusts OCR confidence up or down based on image quality.
8. **Verification** (`check_instagram_exists`) — HTTP HEAD to `instagram.com/{username}/` with retry logic (3 attempts, exponential backoff on 429 rate limiting). Returns True/False/None.
9. **Tiered categorization** — verified (≥70% adjusted confidence + URL exists), unverified (≥70% + network error), review (<70% or URL 404), failed (no extraction). Verified results are further tagged HIGH (≥85%) or MED (70-84%).
10. **Near-duplicate detection** (`find_similar_existing`) — Levenshtein distance check against existing usernames. Near-duplicates (edit distance ≤2) are flagged for review rather than auto-verified.
11. **Parallel processing** — `multiprocessing.Pool` distributes images across workers. Note: the global `_ocr_reader` singleton does NOT carry across processes; each worker initializes its own reader.
12. **Output** — appends to markdown files in `~/Desktop/leads/`: `verified_usernames.md`, `needs_review.md`, `extraction_report.md`. Tracks existing usernames to skip duplicates and near-duplicates across runs.

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

4. **Instagram verification is rate-limited** — `check_instagram_exists()` makes HTTP HEAD requests to instagram.com with retry logic and exponential backoff. High-volume runs may still trigger rate limiting or IP blocks. The function catches `requests.RequestException` and returns `None` (unverified) after exhausting retries.

5. **Output files are append-only** — `verified_usernames.md` and `needs_review.md` are designed for incremental appending across multiple runs. The duplicate detection in `load_existing_usernames()` relies on specific markdown formatting patterns (numbered lists with regex). Do not change the output format without updating the corresponding regex patterns.

6. **No input validation on image files** — `cv2.imread()` returns `None` for corrupt/unreadable files, which causes `shape[:2]` to throw. The try/except in `extract_username_from_image` catches this, but error messages may be cryptic.

7. **Worker count capped at 4** — `optimal_workers` is `min(4, max(1, cpu_count() - 1))`. This is intentional to prevent system freezing. Do not increase this cap without understanding memory implications (each worker loads its own EasyOCR model).

8. **Debug directory is auto-deleted** — `~/Desktop/ocr_debug/` is created at module load time and deleted via `shutil.rmtree()` at the end of a successful run. Do not store anything important there.
