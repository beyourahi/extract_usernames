# Instagram Username Extractor

## Project Overview

Single-file Python CLI tool that extracts Instagram usernames from screenshots using EasyOCR with GPU acceleration. It crops a specific region of each screenshot (where the Instagram username appears), runs multi-pass OCR with weighted voting, validates the username format, and categorizes results into verified/review/failed based on OCR confidence.

**Project Type**: Single-script Python CLI tool (no framework, no build system, no tests)

## Running

```bash
# Folder name on Desktop (required argument)
python3 extract_usernames.py my_folder

# Absolute path
python3 extract_usernames.py /path/to/images

# Custom output directory (default: ~/Desktop/leads)
python3 extract_usernames.py my_folder --output /path/to/output

# With diagnostic output (debug images + JSON)
python3 extract_usernames.py my_folder --diagnostics

# Disable VLM (EasyOCR only)
python3 extract_usernames.py my_folder --no-vlm
```

No test suite or build system exists. The project is a single script (`extract_usernames.py`).

## Dependencies

```bash
pip install easyocr torch torchvision opencv-python

# VLM support (runs by default, gracefully degrades if unavailable)
brew install ollama          # macOS (or see https://ollama.com for other platforms)
ollama pull minicpm-v:8b-2.6-q8_0    # downloads ~8.5 GB model
pip install ollama           # Python client
```

EasyOCR downloads ~50MB of models on first run (cached locally). VLM runs by default via Ollama — if Ollama is not running or the model isn't pulled, the script falls back to EasyOCR-only automatically. Use `--no-vlm` to explicitly disable.

## Architecture

Everything lives in `extract_usernames.py`. The processing pipeline:

1. **Hardware detection** (`detect_hardware`) — probes CUDA, MPS (Apple Silicon), falls back to CPU. Determines worker count for multiprocessing.
2. **Image cropping** — uses hardcoded pixel offsets (`TOP_OFFSET=165`, `CROP_HEIGHT=90`, margins of 100px) to extract the username region from Instagram profile screenshots.
3. **Multi-pass preprocessing** — three variants run on each image:
   - `preprocess_balanced` — CLAHE → bilateral filter → 3x LANCZOS4 upscale → median blur → adaptive threshold → morphological close
   - `preprocess_aggressive` — CLAHE (high clip) → 4x LANCZOS4 upscale → Otsu threshold → morphological close (larger kernel)
   - `preprocess_minimal` — grayscale → 3x LANCZOS4 upscale → denoise → mean-based adaptive threshold
4. **Multi-pass OCR with weighted voting** (`ocr_extract_username`) — EasyOCR reader (singleton via `get_ocr_reader`) runs on all 3 preprocessing variants. Aggressive variant is weighted 2x in voting (empirically most accurate). Consensus requires weight >= 3 (aggressive + one other). Falls back to highest-confidence single result. Also tries concatenating adjacent text segments (sorted by x-coordinate) to recover usernames split at underscores.
5. **Username validation** (`clean_username`) — enforces Instagram rules: 1-30 chars, alphanumeric/dots/underscores, must start alphanumeric, can't end with period. Preserves trailing underscores (valid on Instagram).
6. **Image quality scoring** (`calculate_image_quality`, `adjust_confidence`) — measures sharpness (Laplacian variance), contrast (std deviation), and brightness consistency. Only penalizes very low quality (<0.5); no boost for high quality (prevents inflating borderline results).
7. **VLM second opinion** (on by default, disable with `--no-vlm`) — after EasyOCR produces a result, sends the cropped image to minicpm-v:8b-2.6-q8_0 via Ollama for an independent read. Consensus logic: if both agree, confidence is boosted to >=90%. If they disagree by <=2 edit distance, the longer result is preferred (preserves underscores/dots that one engine may drop). If they disagree by >2 edits, VLM result is preferred at 85% confidence. If EasyOCR fails entirely, VLM acts as a rescue at 80% confidence. Gracefully degrades to EasyOCR-only if Ollama is unavailable.
8. **Confidence-only categorization** — verified HIGH (>=90%), verified MED (>=80%), review (<80%), failed (no extraction). No HTTP verification (Instagram requires auth for all profile requests since mid-2024).
9. **Near-duplicate detection** (`find_similar_existing`) — Levenshtein distance check against existing usernames. Near-duplicates (edit distance <=2) are flagged for review rather than auto-verified.
10. **Within-batch deduplication** — `append_to_files()` tracks a `seen` set to prevent the same username from being written twice in a single run.
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

All output goes to `~/Desktop/leads/` by default (override with `--output`). When `--diagnostics` is passed, debug images go to a sibling `ocr_debug/` directory and a JSON dump goes to the output directory as `validation_raw_results.json`. Without `--diagnostics`, the debug directory is cleaned up automatically. All directories are created with `parents=True` for cross-platform compatibility.

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

4. **No HTTP verification** — Instagram requires authentication for all profile page requests (since mid-2024). HTTP HEAD/GET returns 200 for all usernames (real or fake) because the login page always responds 200. Classification relies entirely on OCR confidence.

5. **Output files are append-only** — `verified_usernames.md` and `needs_review.md` are designed for incremental appending across multiple runs. The duplicate detection in `load_existing_usernames()` relies on specific markdown formatting patterns (numbered lists with regex). Do not change the output format without updating the corresponding regex patterns.

6. **No input validation on image files** — `cv2.imread()` returns `None` for corrupt/unreadable files, which causes `shape[:2]` to throw. The try/except in `extract_username_from_image` catches this, but error messages may be cryptic.

7. **Worker count capped at 4** — `optimal_workers` is `min(4, max(1, cpu_count() - 1))`. This is intentional to prevent system freezing. Do not increase this cap without understanding memory implications (each worker loads its own EasyOCR model).

8. **Debug directory behavior** — `~/Desktop/ocr_debug/` is created at module load time. Without `--diagnostics`, it is deleted at the end of a successful run via `shutil.rmtree()`. With `--diagnostics`, it is preserved along with a JSON dump. Do not store anything important there.

9. **VLM runs by default** — VLM depends on a local Ollama server (`localhost:11434`). If Ollama is not running or the model isn't pulled, the script warns and falls back to EasyOCR-only. Use `--no-vlm` to explicitly disable. VLM calls are serialized through a single Ollama instance (one image at a time), so it is the processing bottleneck. Workers are reduced to 2 when VLM is active to leave memory headroom for the model (~8.5 GB for `minicpm-v:8b-2.6-q8_0`).

10. **VLM consensus heuristic is tuned for underscore/dot preservation** — The "prefer longer result when edit distance <=2" rule exists specifically because EasyOCR tends to drop underscores and dots while VLMs preserve them. Do not change this heuristic without regression testing against `ground_truth.csv`.
