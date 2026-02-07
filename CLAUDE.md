# Instagram Username Extractor

## Project Overview

Single-file Python CLI tool that extracts Instagram usernames from screenshots using **VLM-primary dual-engine architecture**. By default, the VLM (Vision Language Model via Ollama) performs primary extraction, with EasyOCR cross-validating results through an intelligent consensus validator. This approach maximizes accuracy, especially for preserving dots and underscores that traditional OCR often drops or misreads.

**Architecture**: VLM primary + EasyOCR cross-validation with 5-strategy consensus (default), or EasyOCR-only legacy mode (`--no-vlm`)

**Project Type**: Single-script Python CLI tool (no framework, no build system, no tests)

## Running

```bash
# Folder name on Desktop (VLM-primary mode, default)
python3 extract_usernames.py my_folder

# Absolute path
python3 extract_usernames.py /path/to/images

# Custom output directory (default: ~/Desktop/leads)
python3 extract_usernames.py my_folder --output /path/to/output

# With diagnostic output (debug images + JSON + consensus decisions)
python3 extract_usernames.py my_folder --diagnostics

# Disable VLM (EasyOCR-only legacy mode)
python3 extract_usernames.py my_folder --no-vlm

# Use alternative VLM model (default: glm-ocr:bf16)
python3 extract_usernames.py my_folder --vlm-model minicpm-v:8b-2.6-q8_0
```

No test suite or build system exists. The project is a single script (`extract_usernames.py`).

## Installation

Automated setup scripts handle all dependencies:

**Windows:**
```powershell
.\setup.ps1
```

**macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

Setup scripts automatically:
- Check Python 3.9+ installation
- Install Python dependencies (~2-3GB)
- Install/detect Ollama
- Download GLM-OCR model (~2.2GB)
- Validate installation

**Manual installation:**
```bash
pip install -r requirements.txt

# VLM support (runs by default, gracefully degrades if unavailable)
brew install ollama          # macOS (or see https://ollama.com for other platforms)
ollama pull glm-ocr:bf16     # downloads ~2.2 GB model (default)
pip install ollama           # Python client
```

## Dependencies

See `requirements.txt`:
- `easyocr>=1.7.0` - Cross-validation OCR engine
- `opencv-python>=4.8.0,<5.0.0` - Image preprocessing
- `numpy>=1.24.0` - Array operations
- `torch>=2.0.0` - PyTorch backend
- `torchvision>=0.15.0` - Vision utilities
- `ollama>=0.1.0` - VLM integration (optional)

EasyOCR downloads ~50MB of models on first run (cached locally). VLM runs by default via Ollama — if Ollama is not running or the model isn't pulled, the script falls back to EasyOCR-only automatically. Use `--no-vlm` to explicitly disable.

## Architecture

Everything lives in `extract_usernames.py`. The processing pipeline:

### VLM-Primary Dual-Engine Architecture (Default)

1. **Hardware detection** (`detect_hardware`) — probes CUDA, MPS (Apple Silicon), falls back to CPU. Determines worker count: max 2 workers when VLM enabled (memory constraint), max 6 when EasyOCR-only.

2. **Image cropping** — uses hardcoded pixel offsets (`TOP_OFFSET=165`, `CROP_HEIGHT=90`, margins of 100px) to extract the username region from Instagram profile screenshots.

3. **VLM primary extraction** (`vlm_primary_extract`) — sends **raw cropped image** (no preprocessing) to VLM via Ollama. VLM reads text holistically and preserves dots/underscores better than EasyOCR. Enhanced confidence scoring:
   - Base confidence: 85%
   - Penalty for hedging language ("appears", "seems", etc.): -15%
   - Bonus for valid Instagram format: +10%
   - Penalty for unusual patterns (excessive dots, no vowels, etc.): -10%
   - Final confidence clamped to 60-100%

4. **EasyOCR cross-validation** (`easyocr_cross_validate`) — if VLM succeeds, runs EasyOCR multi-pass for comparison:
   - **Multi-pass preprocessing** — three variants:
     - `preprocess_balanced` — CLAHE → bilateral filter → 3x LANCZOS4 upscale → median blur → adaptive threshold → morphological close
     - `preprocess_aggressive` — CLAHE (high clip) → 4x LANCZOS4 upscale → Otsu threshold → morphological close (larger kernel, weighted 2x in voting)
     - `preprocess_minimal` — grayscale → 3x LANCZOS4 upscale → denoise → mean-based adaptive threshold
   - **Weighted voting** — consensus requires weight >=3 (aggressive + one other)
   - **Cross-variant corrections**:
     - Dot reconciliation (`_find_dotted_sibling`) — prefers dotted versions when variants differ
     - Confusion pattern fixes (`_find_confusion_correction`) — applies known corrections (tf→ff, rn→m, vv→w, 0→o, 5→s, 8→b, etc.)
   - EasyOCR reader is singleton via `get_ocr_reader` (but does NOT carry across process boundaries)

5. **Intelligent consensus validator** (`intelligent_consensus_validator`) — merges VLM and EasyOCR results using 5 strategies:
   - **Strategy 1: Exact Agreement** — if both engines produce identical username, boost confidence +5% (capped at 95%). This is the highest confidence tier.
   - **Strategy 2: Dot/Underscore Reconciliation** — if usernames differ only by dots/underscores (e.g., `user.name` vs `username`), prefer VLM version (VLM preserves special chars better). Confidence +3%.
   - **Strategy 3: Character Confusion Correction** — if difference matches known OCR confusion patterns (tf→ff, rn→m, etc.), prefer corrected version. Confidence 88%.
   - **Strategy 4: Minor Edit Distance (≤2)** — if edit distance ≤2, prefer longer version (likely preserves more characters). Use original confidence.
   - **Strategy 5: Significant Disagreement (>2)** — if engines disagree significantly, use higher-confidence result with -10 to -15% penalty. Flag for review.

6. **Fallback behavior**:
   - If VLM fails but EasyOCR succeeds → use EasyOCR result (method: `ocr_rescue`)
   - If EasyOCR fails but VLM succeeds → use VLM result (method: `vlm_only`)
   - If both fail → mark as `failed` for manual review

7. **Username validation** (`clean_username`) — enforces Instagram rules: 1-30 chars, alphanumeric/dots/underscores, must start alphanumeric, can't end with period. Preserves trailing underscores (valid on Instagram).

8. **Classification with stricter tiers** (`classify_status`):
   - **HIGH (verified)**: ≥95% confidence (exact engine agreement or VLM high confidence)
   - **MED (verified)**: 85-94% confidence (minor differences resolved)
   - **REVIEW**: <85% confidence (significant disagreement or low confidence)

9. **Near-duplicate detection** (`find_similar_existing`) — Levenshtein distance check against existing usernames. Near-duplicates (edit distance ≤2) are flagged for review rather than auto-verified.

10. **Within-batch deduplication** — `append_to_files()` tracks a `seen` set to prevent the same username from being written twice in a single run.

11. **Parallel processing** — `multiprocessing.Pool` distributes images across workers (max 2 when VLM enabled, max 6 when EasyOCR-only). Note: the global `_ocr_reader` singleton does NOT carry across processes; each worker initializes its own reader.

12. **Output** — appends to markdown files in `~/Desktop/leads/` (or custom `--output` path): `verified_usernames.md`, `needs_review.md`, `extraction_report.md`. Tracks existing usernames to skip duplicates and near-duplicates across runs.

### EasyOCR-Only Legacy Mode (`--no-vlm`)

When VLM is disabled, the pipeline simplifies:
1. Hardware detection (max 6 workers)
2. Image cropping
3. EasyOCR multi-pass with weighted voting (as described above)
4. Username validation
5. Classification with **same stricter tiers** (95%/85%, not old 90%/80%)
6. Output

## Key Constants

The crop region constants at the top of the file are tuned for standard Instagram mobile profile screenshots. If screenshots come from a different layout, these need adjustment:

```python
TOP_OFFSET = 165   # pixels from top to username area
CROP_HEIGHT = 90   # height of crop region
LEFT_MARGIN = 100  # left padding
RIGHT_MARGIN = 100 # right padding
```

## Output Paths

All output goes to `~/Desktop/leads/` by default (override with `--output`). When `--diagnostics` is passed:
- Debug images go to `{output_parent}/ocr_debug/`
- VLM raw responses saved as `{image_stem}_vlm_response.txt`
- Consensus decisions saved as `{image_stem}_consensus.json`
- Full JSON dump saved as `validation_raw_results.json`

Without `--diagnostics`, the debug directory is cleaned up automatically. All directories are created with `parents=True` for cross-platform compatibility.

## Enhanced Reporting

The `extraction_report.md` includes engine performance metrics when VLM is enabled:
- VLM primary successes count
- EasyOCR rescue count (VLM failed, OCR succeeded)
- Consensus methods distribution (exact_agreement, dot_reconciled_vlm, confusion_corrected, etc.)
- Engine comparison table (avg confidence, dot preservation rate)
- Processing speed per engine

## Repository Etiquette

### Conventional Commits

Use semantic commit messages:

```
feat:     new feature
fix:      bug fix
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

4. **No HTTP verification** — Instagram requires authentication for all profile page requests (since mid-2024). HTTP HEAD/GET returns 200 for all usernames (real or fake) because the login page always responds 200. Classification relies entirely on OCR/VLM confidence.

5. **Output files are append-only** — `verified_usernames.md` and `needs_review.md` are designed for incremental appending across multiple runs. The duplicate detection in `load_existing_usernames()` relies on specific markdown formatting patterns (numbered lists with regex). Do not change the output format without updating the corresponding regex patterns.

6. **No input validation on image files** — `cv2.imread()` returns `None` for corrupt/unreadable files, which causes `shape[:2]` to throw. The try/except in `extract_username_from_image` catches this, but error messages may be cryptic.

7. **Worker count logic is architecture-dependent** — `optimal_workers` is `min(6, max(1, cpu_count() - 1))` baseline. When VLM is enabled, reduced to `min(2, optimal_workers)` to prevent memory exhaustion (VLM models require significant VRAM/RAM). When EasyOCR-only, full 6 workers are used.

8. **Debug directory behavior** — Debug directory is created as `{output_parent}/ocr_debug/` when needed. Without `--diagnostics`, it is deleted at the end of a successful run via `shutil.rmtree()`. With `--diagnostics`, it is preserved along with VLM responses, consensus decisions, and JSON dump. Do not store anything important there.

9. **VLM runs by default** — VLM depends on a local Ollama server (`localhost:11434`). If Ollama is not running or the model isn't pulled, the script warns and falls back to EasyOCR-only. Use `--no-vlm` to explicitly disable. VLM calls are serialized through a single Ollama instance (one image at a time), so it is the processing bottleneck.

10. **VLM model is configurable** — Default model is `glm-ocr:bf16` (~2.2GB, optimized for OCR, fastest). Alternative models can be specified via `--vlm-model` flag. Recommended alternatives:
    - `minicpm-v:8b-2.6-q8_0` (~8.5GB) — better accuracy on challenging images, slower
    - `qwen2.5-vl:7b` (~6GB) — excellent document understanding, balanced speed/accuracy

11. **VLM-primary architecture is accuracy-first** — Processing speed is ~0.5-2 images/sec (vs 5-15 images/sec EasyOCR-only). This is intentional — VLM preserves dots/underscores that EasyOCR drops, and dual-engine consensus catches OCR hallucinations. Use `--no-vlm` for speed-critical workflows.

12. **Intelligent consensus validator has 5 strategies** — The reconciliation logic is carefully tuned:
    - Exact agreement gets highest boost (confidence +5%, capped at 95%)
    - Dot reconciliation always prefers VLM (VLM preserves special chars better)
    - Minor disagreements (edit distance ≤2) prefer longer version (preserves dropped chars)
    - Major disagreements apply confidence penalty and flag for review
    Do not change these heuristics without extensive regression testing.

13. **Confidence tiers are stricter than legacy** — Old tiers were HIGH ≥90%, MED ≥80%. New tiers are HIGH ≥95%, MED ≥85%. This reduces false positives in verified list. Even with `--no-vlm`, new tiers apply.

14. **DEEP PATH processing on all images** — Unlike a hypothetical FAST PATH (VLM-only on clean images), this implementation runs VLM + EasyOCR cross-validation on EVERY image for maximum accuracy. This is intentional.

15. **Setup scripts handle dependencies** — `setup.ps1` (Windows) and `setup.sh` (macOS/Linux) automate the full installation process including Python dependency checks, Ollama installation, and model downloads. These should be the primary installation method documented to users.

16. **Consensus metadata is rich** — When `--diagnostics` is enabled, consensus decisions are saved as JSON with full details: both engine results, edit distance, reconciliation strategy, final decision reasoning. This is invaluable for debugging and tuning.

17. **VLM sends raw images** — Unlike EasyOCR which requires heavy preprocessing (CLAHE, upscaling, thresholding), VLM receives the raw cropped image. VLMs are trained on natural images and don't benefit from traditional OCR preprocessing.
