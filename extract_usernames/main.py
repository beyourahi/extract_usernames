#!/usr/bin/env python3
"""Main extraction engine - wrapper for backward compatibility and CLI integration."""

import sys
import warnings
from pathlib import Path
from typing import Dict, Any

warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.data.dataloader')

# Import the original extraction logic
# We keep extract_usernames.py at repo root for backward compatibility
# but expose run_extraction() API for the new CLI

def run_extraction(
    input_dir: str,
    output_dir: str,
    use_vlm: bool = True,
    vlm_model: str = 'glm-ocr:bf16',
    diagnostics: bool = False,
    workers: int = None,
) -> Dict[str, Any]:
    """Run the Instagram username extraction pipeline.
    
    Args:
        input_dir: Directory containing screenshot images
        output_dir: Directory for output files
        use_vlm: Enable VLM-primary mode (default: True)
        vlm_model: VLM model to use (default: glm-ocr:bf16)
        diagnostics: Enable diagnostics mode (default: False)
        workers: Number of worker processes (default: auto-detect)
    
    Returns:
        Dictionary with extraction results:
        {
            'verified_count': int,
            'review_count': int,
            'failed_count': int,
            'duplicate_count': int,
            'processing_time': float,
            'verified_file': Path,
            'review_file': Path,
            'report_file': Path,
        }
    """
    # Import here to avoid circular imports and allow CLI to initialize first
    import os
    import sys
    from pathlib import Path
    
    # Add repo root to path for backward compatibility with original script
    repo_root = Path(__file__).parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    
    # Import the original extraction script
    # This maintains all the complex logic from extract_usernames.py
    try:
        import extract_usernames as extractor
    except ImportError:
        raise ImportError(
            "Could not import extract_usernames.py. "
            "Make sure the file exists at the repository root."
        )
    
    # Override module-level configuration
    extractor.VLM_MODEL = vlm_model
    extractor.setup_directories(output_dir)
    
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Detect hardware
    hardware_info = extractor.detect_hardware()
    
    if workers:
        hardware_info['optimal_workers'] = workers
    elif use_vlm:
        # Reduce workers for VLM mode to manage memory
        hardware_info['optimal_workers'] = min(2, hardware_info['optimal_workers'])
    
    # Check VLM availability
    if use_vlm:
        vlm_ok, vlm_msg = extractor.check_ollama_available()
        if not vlm_ok:
            print(f"⚠️  VLM not available: {vlm_msg}")
            print("   Falling back to EasyOCR-only mode")
            use_vlm = False
    
    # Scan for images
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_paths = [p for p in input_path.iterdir() 
                  if p.suffix.lower() in image_extensions]
    
    if not image_paths:
        raise ValueError(f"No images found in {input_dir}")
    
    # Load existing usernames
    existing_usernames = extractor.load_existing_usernames()
    
    # Prepare arguments for parallel processing
    use_gpu = hardware_info['gpu_available']
    args_list = [
        (path, idx, len(image_paths), existing_usernames, use_gpu, diagnostics, use_vlm)
        for idx, path in enumerate(image_paths, 1)
    ]
    
    # Run extraction
    import time
    from multiprocessing import Pool
    
    start_time = time.time()
    
    with Pool(processes=hardware_info['optimal_workers']) as pool:
        results = pool.map(extractor.extract_username_from_image_parallel, args_list)
    
    elapsed_time = time.time() - start_time
    
    # Save results
    new_verified, new_review = extractor.append_to_files(results, existing_usernames)
    
    # Generate report
    extractor.generate_report(
        hardware_info, input_path, results, elapsed_time, 
        new_verified, new_review, vlm_model, use_vlm
    )
    
    # Clean up debug directory if diagnostics disabled
    if not diagnostics:
        import shutil
        if extractor.DEBUG_DIR.exists():
            shutil.rmtree(extractor.DEBUG_DIR)
    
    # Return summary
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
    # If run directly, execute the original script
    import extract_usernames
    extract_usernames.main()
