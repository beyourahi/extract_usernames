#!/usr/bin/env python3
"""Thin orchestrator wrapping `_archive.extract_usernames` for the new CLI.

The legacy monolith owns all real logic and module-level globals (VLM_MODEL,
OUTPUT_DIR, DEBUG_DIR, VERIFIED_FILE, REVIEW_FILE, REPORT_FILE). This module's
job is to mutate those globals via `setup_directories` and assignment, then
drive `multiprocessing.Pool` over `extract_username_from_image_parallel`.
"""

import sys
import warnings
from pathlib import Path
from typing import Dict, Any

# EasyOCR's torch DataLoader emits a noisy worker-count UserWarning on import.
# Filter must be installed before any submodule triggers easyocr import.
warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.data.dataloader')


def run_extraction(
    input_dir: str,
    output_dir: str,
    use_vlm: bool = True,
    vlm_model: str = 'glm-ocr:bf16',
    diagnostics: bool = False,
    workers: int = None,
) -> Dict[str, Any]:
    """Drive the extraction pipeline; mutates extractor module globals.

    Side effects:
    - Sets `extractor.VLM_MODEL`, calls `extractor.setup_directories(output_dir)`
      which assigns OUTPUT_DIR / DEBUG_DIR / VERIFIED_FILE / REVIEW_FILE / REPORT_FILE.
    - Creates output dir, debug dir, and `cropped_usernames_images/` subdir.
    - When `diagnostics=False`, removes DEBUG_DIR via `shutil.rmtree` after run.
    - Forks worker processes via `multiprocessing.Pool` (one-shot, context-managed).

    VLM mode caps `optimal_workers` at 2 to bound VRAM (Ollama loads one model
    instance per worker). Passing explicit `workers` bypasses this guard.

    Falls back to EasyOCR-only when Ollama is unreachable (mutates local `use_vlm`).

    Raises:
        FileNotFoundError: input_dir missing.
        ValueError: input_dir exists but contains no images with supported ext.
        ImportError: _archive package missing or broken.

    Returns dict with keys: verified_count, review_count, failed_count,
    duplicate_count, processing_time, verified_file, review_file, report_file.
    Counts treat near-duplicates as review, not verified.
    """
    # Deferred imports keep CLI startup fast and avoid the multiprocessing
    # fork-vs-spawn pickling pitfalls that surface when these are top-level.
    import os
    import sys
    from pathlib import Path

    try:
        from ._archive import extract_usernames as extractor
    except ImportError:
        raise ImportError(
            "Could not import extract_usernames.py from _archive. "
            "Make sure the file exists in extract_usernames/_archive/."
        )

    # Mutates extractor module state — must happen before worker fork.
    extractor.VLM_MODEL = vlm_model
    extractor.setup_directories(output_dir)

    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    hardware_info = extractor.detect_hardware()

    if workers:
        hardware_info['optimal_workers'] = workers
    elif use_vlm:
        # VRAM/RAM bound: each Ollama worker pins a full VLM model in memory.
        hardware_info['optimal_workers'] = min(2, hardware_info['optimal_workers'])

    if use_vlm:
        # Probes Ollama server + checks model is pulled. Demotes to EasyOCR
        # gracefully so CLI users without Ollama still get a result.
        vlm_ok, vlm_msg = extractor.check_ollama_available()
        if not vlm_ok:
            print(f"⚠️  VLM not available: {vlm_msg}")
            print("   Falling back to EasyOCR-only mode")
            use_vlm = False

    # Discovery whitelist — keep in sync with README "supported formats".
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_paths = [p for p in input_path.iterdir()
                  if p.suffix.lower() in image_extensions]

    if not image_paths:
        raise ValueError(f"No images found in {input_dir}")

    # Existing usernames are loaded from prior `verified_usernames.md` /
    # `needs_review.md` and used for cross-batch deduplication inside workers.
    existing_usernames = extractor.load_existing_usernames()

    use_gpu = hardware_info['gpu_available']
    # Worker argument tuple shape is positional — must match the destructure
    # at the top of `extract_username_from_image_parallel` in _archive.
    args_list = [
        (path, idx, len(image_paths), existing_usernames, use_gpu, diagnostics, use_vlm,
         str(extractor.OUTPUT_DIR), str(extractor.DEBUG_DIR), vlm_model)
        for idx, path in enumerate(image_paths, 1)
    ]

    import time
    from multiprocessing import Pool

    start_time = time.time()

    with Pool(processes=hardware_info['optimal_workers']) as pool:
        results = pool.map(extractor.extract_username_from_image_parallel, args_list)

    elapsed_time = time.time() - start_time

    # append_to_files writes verified_usernames.md / needs_review.md and returns
    # the count of NEW entries appended (not total results length).
    new_verified, new_review = extractor.append_to_files(results, existing_usernames)

    extractor.generate_report(
        hardware_info, input_path, results, elapsed_time,
        new_verified, new_review, vlm_model, use_vlm
    )

    if not diagnostics:
        # DEBUG_DIR contains per-image preprocess variants + VLM raw responses;
        # only retain when explicitly asked.
        import shutil
        if extractor.DEBUG_DIR.exists():
            shutil.rmtree(extractor.DEBUG_DIR)

    # Status taxonomy: verified | review | failed | error. is_duplicate and
    # is_near_duplicate are orthogonal flags set in _parallel wrapper.
    # near-duplicate counts as review (not verified) by design.
    verified = sum(1 for r in results if r['status'] == 'verified'
                   and not r.get('is_duplicate') and not r.get('is_near_duplicate'))
    review = sum(1 for r in results if r['status'] == 'review'
                 or r.get('is_near_duplicate', False))
    failed = sum(1 for r in results if r['status'] in ['failed', 'error'])
    duplicates = sum(1 for r in results if r.get('is_duplicate', False))

    return {
        'verified_count': verified,
        'review_count': review,
        'failed_count': failed,
        'duplicate_count': duplicates,
        'processing_time': elapsed_time,
        'verified_file': extractor.VERIFIED_FILE,
        'review_file': extractor.REVIEW_FILE,
        'report_file': extractor.REPORT_FILE,
    }


if __name__ == '__main__':
    # `python -m extract_usernames.main` falls through to the legacy argparse
    # CLI in _archive (different flag set than `cli.py`'s Click interface).
    from ._archive import extract_usernames
    extract_usernames.main()
