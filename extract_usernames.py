#!/usr/bin/env python3

"""
Instagram Username Extractor - Multi-Pass OCR System
====================================================

PURPOSE:
This script extracts Instagram usernames from screenshot images using advanced
OCR (Optical Character Recognition) techniques with Tesseract.

KEY FEATURES:
- Multi-pass OCR: 5 preprocessing methods × 3 PSM modes = 15 attempts per image
- Voting system: Selects most common result across all OCR attempts
- Instagram verification: Validates usernames by checking profile URLs
- Duplicate detection: Skips already-processed usernames across runs
- Incremental updates: Appends new results without overwriting existing data

USAGE:
    python3 extract_usernames.py                    # Uses default: ~/Desktop/leads_images
    python3 extract_usernames.py my_folder         # Uses ~/Desktop/my_folder
    python3 extract_usernames.py /path/to/folder   # Uses absolute path

AUTHOR: Rahi Khan (Dropout Studio)
REPO: https://github.com/beyourahi/extract_usernames
"""

import os
import re
import time
import shutil
import argparse
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
import pytesseract
import requests
from datetime import datetime
from collections import Counter


# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================
# These values control how the script processes images and extracts usernames.
# Adjust these if your screenshots have different dimensions or layouts.

# Image cropping parameters (in pixels)
TOP_OFFSET = 165          # Distance from top edge to start of username area
CROP_HEIGHT = 90          # Height of the region containing username
LEFT_MARGIN = 100         # Left padding to exclude from crop
RIGHT_MARGIN = 100        # Right padding to exclude from crop

# OCR confidence threshold (percentage)
CONFIDENCE_THRESHOLD = 60 # Minimum confidence to auto-verify (0-100)

# Output directory (results are saved here)
OUTPUT_DIR = Path.home() / "Desktop" / "extracted_usernames"

# Debug directory (temporary, auto-deleted after run)
DEBUG_DIR = Path.home() / "Desktop" / "ocr_debug"

# Ensure output directories exist
DEBUG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Output file paths
VERIFIED_FILE = OUTPUT_DIR / "verified_usernames.md"
REVIEW_FILE = OUTPUT_DIR / "needs_review.md"
REPORT_FILE = OUTPUT_DIR / "extraction_report.md"


# ============================================================================
# COMMAND-LINE ARGUMENT PARSING
# ============================================================================

def parse_arguments():
    """
    Parse command-line arguments to get input directory.
    
    PARAMETERS:
    - folder_name (optional): Name of folder on Desktop or absolute path
    
    RETURNS:
    - Path object: Resolved input directory path
    
    EXAMPLES:
    - No argument: Uses ~/Desktop/leads_images
    - 'screenshots': Uses ~/Desktop/screenshots
    - '/Users/name/pics': Uses /Users/name/pics
    """
    parser = argparse.ArgumentParser(
        description='Extract Instagram usernames from screenshot images using OCR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Uses default: ~/Desktop/leads_images
  %(prog)s my_images             # Uses ~/Desktop/my_images
  %(prog)s /path/to/folder       # Uses absolute path
        """
    )
    
    parser.add_argument(
        'folder',
        nargs='?',  # Makes argument optional
        default='leads_images',
        help='Folder name (on Desktop) or absolute path to images (default: leads_images)'
    )
    
    args = parser.parse_args()
    
    # Determine if path is absolute or relative to Desktop
    folder_path = Path(args.folder)
    
    if folder_path.is_absolute():
        # User provided absolute path
        input_dir = folder_path
    else:
        # User provided folder name - assume it's on Desktop
        input_dir = Path.home() / "Desktop" / args.folder
    
    return input_dir


# ============================================================================
# DUPLICATE DETECTION
# ============================================================================

def load_existing_usernames():
    """
    Load previously extracted usernames from output files to prevent duplicates.
    
    This function reads both verified_usernames.md and needs_review.md files
    and extracts all usernames already processed in previous runs.
    
    RETURNS:
    - set: Collection of unique usernames already in the system
    
    PURPOSE FOR AI AGENTS:
    This prevents re-processing the same username multiple times across
    different batch runs, saving time and maintaining data integrity.
    """
    existing_usernames = set()
    
    # Pattern explanation for verified file: "123. username - https://..."
    # Regex breakdown: ^\d+\.\s+ (number + dot + space) + (\w+(?:[._]\w+)*) (username) + \s+-\s+https?://
    if VERIFIED_FILE.exists():
        with open(VERIFIED_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^\d+\.\s+(\w+(?:[._]\w+)*)\s+-\s+https?://', line)
                if match:
                    existing_usernames.add(match.group(1))
    
    # Pattern explanation for review file: "123. **username** - ..."
    # Regex breakdown: ^\d+\.\s+ (number + dot + space) + \*\*(\w+(?:[._]\w+)*)\*\* (bold username)
    if REVIEW_FILE.exists():
        with open(REVIEW_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^\d+\.\s+\*\*(\w+(?:[._]\w+)*)\*\*\s+-\s+', line)
                if match:
                    existing_usernames.add(match.group(1))
    
    return existing_usernames


# ============================================================================
# IMAGE PREPROCESSING TECHNIQUES
# ============================================================================
# These functions apply different preprocessing methods to enhance text clarity
# before OCR extraction. Each method works better for different image conditions.

def preprocess_adaptive_gaussian(img):
    """
    Adaptive Gaussian Thresholding - Best for varying lighting conditions.
    
    PROCESS:
    1. Convert to grayscale
    2. Denoise to remove artifacts
    3. Upscale 6x for better character recognition
    4. Apply adaptive threshold (adjusts per image region)
    5. Morphological closing to connect character fragments
    
    USE CASE: Images with uneven lighting or gradient backgrounds
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    thresh = cv2.adaptiveThreshold(upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 8)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)


def preprocess_otsu(img):
    """
    Otsu's Binarization - Automatic threshold detection.
    
    PROCESS:
    1. Convert to grayscale
    2. Denoise
    3. Upscale 6x
    4. Apply Gaussian blur to smooth edges
    5. Otsu's method automatically determines optimal threshold
    
    USE CASE: Images with bimodal histograms (clear foreground/background)
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    blurred = cv2.GaussianBlur(upscaled, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def preprocess_clahe(img):
    """
    CLAHE (Contrast Limited Adaptive Histogram Equalization) - Enhanced contrast.
    
    PROCESS:
    1. Convert to grayscale
    2. Denoise
    3. Upscale 7x (higher for better detail)
    4. Apply CLAHE to enhance local contrast
    5. Otsu's threshold
    6. Morphological closing
    
    USE CASE: Low contrast images or faded screenshots
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=7, fy=7, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(upscaled)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)


def preprocess_bilateral(img):
    """
    Bilateral Filter - Preserves edges while removing noise.
    
    PROCESS:
    1. Convert to grayscale
    2. Apply bilateral filter (noise reduction with edge preservation)
    3. Upscale 6x
    4. Otsu's threshold
    
    USE CASE: Images with noise but clear text edges
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    upscaled = cv2.resize(filtered, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def preprocess_adaptive_mean(img):
    """
    Adaptive Mean Thresholding - Local averaging method.
    
    PROCESS:
    1. Convert to grayscale
    2. Denoise
    3. Upscale 6x
    4. Adaptive threshold using mean of neighborhood
    
    USE CASE: Images with varying lighting but uniform text
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    thresh = cv2.adaptiveThreshold(upscaled, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10)
    return thresh


# ============================================================================
# OCR EXTRACTION
# ============================================================================

def ocr_tesseract_multipass(img_cv, save_debug_path=None):
    """
    Run Tesseract OCR with multiple preprocessing methods and configurations.
    
    This function applies 5 preprocessing techniques, each tested with 3 different
    Tesseract PSM (Page Segmentation Mode) values, resulting in 15 total attempts.
    
    PSM MODES EXPLAINED:
    - PSM 7: Treat image as single text line
    - PSM 8: Treat image as single word
    - PSM 13: Raw line without special optimizations
    
    PARAMETERS:
    - img_cv: OpenCV image (BGR format)
    - save_debug_path: Optional path to save preprocessed image for debugging
    
    RETURNS:
    - list: All extracted username candidates
    
    PURPOSE FOR AI AGENTS:
    Multiple passes compensate for varying image quality. The voting system
    (implemented in calling function) selects the most common result.
    """
    # Define all preprocessing methods
    preprocessing_methods = [
        ('adaptive_gaussian', preprocess_adaptive_gaussian),
        ('otsu', preprocess_otsu),
        ('clahe', preprocess_clahe),
        ('bilateral', preprocess_bilateral),
        ('adaptive_mean', preprocess_adaptive_mean),
    ]
    
    # Tesseract PSM (Page Segmentation Mode) values to try
    psm_modes = [7, 8, 13]
    
    # Collect all results from every combination
    all_results = []
    
    # Loop through each preprocessing method
    for method_name, preprocess_func in preprocessing_methods:
        # Apply preprocessing
        processed = preprocess_func(img_cv.copy())
        
        # Save debug image (only for first method, only for first 5 images)
        if save_debug_path and method_name == 'adaptive_gaussian':
            cv2.imwrite(str(save_debug_path), processed)
        
        # Convert to PIL format (required by pytesseract)
        pil_img = Image.fromarray(processed)
        
        # Try each PSM mode
        for psm in psm_modes:
            # Tesseract configuration:
            # --psm: Page segmentation mode
            # --oem 3: Use LSTM neural net mode
            # -c tessedit_char_whitelist: Only allow these characters
            config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz0123456789._'
            
            # Run OCR
            text = pytesseract.image_to_string(pil_img, config=config).strip()
            
            # Clean and validate
            username = clean_username(text)
            
            # Add to results if valid
            if username:
                all_results.append(username)
    
    return all_results


# ============================================================================
# USERNAME VALIDATION
# ============================================================================

def clean_username(text):
    """
    Clean and validate extracted text as Instagram username.
    
    INSTAGRAM USERNAME RULES:
    - Length: 1-30 characters
    - Allowed characters: letters, numbers, periods, underscores
    - Must start with alphanumeric (not . or _)
    - Cannot end with period
    - Must contain at least one alphanumeric character
    
    PARAMETERS:
    - text: Raw extracted text from OCR
    
    RETURNS:
    - str: Valid username, or None if invalid
    
    PURPOSE FOR AI AGENTS:
    This function filters out OCR errors and ensures only valid Instagram
    usernames are considered. Invalid formats are rejected early.
    """
    if not text:
        return None
    
    # Convert to lowercase and remove whitespace
    text = text.lower().strip()
    text = re.sub(r'\s+', '', text)
    
    # Remove invalid characters (keep only alphanumeric, period, underscore)
    text = re.sub(r'[^\w._]', '', text)
    
    # Remove leading/trailing dots and underscores
    text = text.strip('._')
    
    # Check length constraints
    if len(text) < 1 or len(text) > 30:
        return None
    
    # Must start with alphanumeric character
    if text and not text[0].isalnum():
        return None
    
    # Cannot end with period
    if text.endswith('.'):
        return None
    
    # Must contain at least one alphanumeric character
    if not any(c.isalnum() for c in text):
        return None
    
    return text


# ============================================================================
# INSTAGRAM VERIFICATION
# ============================================================================

def check_instagram_exists(username):
    """
    Verify if Instagram profile exists by checking profile URL.
    
    METHOD:
    Sends HTTP HEAD request to instagram.com/{username}/
    - Status 200: Profile exists
    - Other status: Profile doesn't exist or is private
    - Exception: Network error (can't verify)
    
    PARAMETERS:
    - username: Instagram username to verify
    
    RETURNS:
    - True: Profile exists and is accessible
    - False: Profile doesn't exist or is inaccessible
    - None: Network error, verification failed
    
    PURPOSE FOR AI AGENTS:
    This prevents false positives by confirming the username actually exists
    on Instagram before marking it as verified.
    """
    try:
        url = f"https://www.instagram.com/{username}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        # Use HEAD request (faster than GET, only checks if resource exists)
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        # Network error, timeout, or other exception
        return None


# ============================================================================
# MAIN EXTRACTION LOGIC
# ============================================================================

def extract_username_from_image(image_path, save_debug=True):
    """
    Extract username from a single image using multi-pass OCR.
    
    WORKFLOW:
    1. Load image
    2. Crop to username region (based on TOP_OFFSET, CROP_HEIGHT, margins)
    3. Run multi-pass OCR (5 preprocessing × 3 PSM modes = 15 attempts)
    4. Use voting system to select best result
    5. Calculate confidence (% of votes for winning username)
    6. Verify username exists on Instagram
    7. Determine status (verified/unverified/review)
    
    PARAMETERS:
    - image_path: Path to screenshot image
    - save_debug: Whether to save preprocessed image for debugging
    
    RETURNS:
    - dict: Contains username, confidence, verification status, and metadata
    
    PURPOSE FOR AI AGENTS:
    This is the core extraction function. It coordinates all preprocessing,
    OCR, validation, and verification steps for a single image.
    """
    try:
        # Load image with OpenCV
        img_cv = cv2.imread(str(image_path))
        height, width = img_cv.shape[:2]
        
        # Calculate crop boundaries
        left = LEFT_MARGIN
        top = TOP_OFFSET
        right = width - RIGHT_MARGIN
        bottom = top + CROP_HEIGHT
        
        # Crop to username region
        cropped = img_cv[top:bottom, left:right]
        
        # Set debug path (only for first 5 images)
        debug_path = DEBUG_DIR / f"{image_path.stem}_crop.png" if save_debug else None
        
        # Run multi-pass OCR
        all_results = ocr_tesseract_multipass(cropped, debug_path)
        
        # Check if any results were found
        if not all_results:
            return {
                'username': None,
                'confidence': 0,
                'verified': False,
                'status': 'failed'
            }
        
        # Voting system: count occurrences of each username
        counter = Counter(all_results)
        
        # Select username with most votes (ties broken by length)
        best_username = max(counter.items(), key=lambda x: (x[1], len(x[0])))[0]
        vote_count = counter[best_username]
        total_votes = len(all_results)
        confidence = (vote_count / total_votes) * 100
        
        # Verify username exists on Instagram
        url_verified = check_instagram_exists(best_username)
        
        # Determine status based on confidence and verification
        if confidence >= CONFIDENCE_THRESHOLD and url_verified == True:
            status = 'verified'  # High confidence + URL exists
        elif confidence >= CONFIDENCE_THRESHOLD and url_verified == None:
            status = 'unverified'  # High confidence but couldn't verify URL
        else:
            status = 'review'  # Low confidence or URL doesn't exist
        
        # Return all metadata
        return {
            'username': best_username,
            'confidence': confidence,
            'verified': url_verified,
            'status': status,
            'all_candidates': dict(counter)  # All alternatives found
        }
        
    except Exception as e:
        # Handle any unexpected errors
        return {
            'username': None,
            'confidence': 0,
            'verified': False,
            'status': 'error',
            'error': str(e)
        }


# ============================================================================
# OUTPUT FILE MANAGEMENT
# ============================================================================

def append_to_files(new_results, existing_usernames):
    """
    Append only new (non-duplicate) usernames to output files.
    
    This function handles incremental updates, ensuring:
    - Duplicates are not added
    - Line numbering continues from previous runs
    - Headers are updated with new totals
    - Both verified and review files are updated
    
    PARAMETERS:
    - new_results: List of extraction results from current run
    - existing_usernames: Set of usernames already in files
    
    RETURNS:
    - tuple: (new_verified_count, new_review_count)
    
    PURPOSE FOR AI AGENTS:
    This enables cumulative extraction across multiple runs without data loss
    or duplication. Previous results are preserved and extended.
    """
    # Filter out duplicates - only keep new usernames
    new_verified = [r for r in new_results 
                   if r['status'] == 'verified' 
                   and r['username'] not in existing_usernames]
    
    new_review = [r for r in new_results 
                 if r['status'] in ['review', 'unverified', 'error'] 
                 and (r['username'] not in existing_usernames if r['username'] else True)]
    
    # ---- Append to verified file ----
    if new_verified:
        # Count existing entries to continue numbering
        current_count = 0
        if VERIFIED_FILE.exists():
            with open(VERIFIED_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if re.match(r'^\d+\.', line):
                        current_count += 1
        
        # Append new entries
        with open(VERIFIED_FILE, 'a', encoding='utf-8') as f:
            # Add header if file is new or empty
            if not VERIFIED_FILE.exists() or VERIFIED_FILE.stat().st_size == 0:
                f.write("# Verified Instagram Usernames\n\n")
                f.write(f"**Last Updated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n")
                f.write("---\n\n")
            
            # Write new usernames with continued numbering
            for i, item in enumerate(new_verified, current_count + 1):
                url = f"https://www.instagram.com/{item['username']}"
                f.write(f"{i}. {item['username']} - {url}\n")
        
        # Update total count in header
        update_file_header(VERIFIED_FILE, current_count + len(new_verified))
    
    # ---- Append to review file ----
    if new_review:
        # Count existing entries
        current_count = 0
        if REVIEW_FILE.exists():
            with open(REVIEW_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if re.match(r'^\d+\.\s+\*\*', line):
                        current_count += 1
        
        # Append new entries
        with open(REVIEW_FILE, 'a', encoding='utf-8') as f:
            # Add header if file is new or empty
            if not REVIEW_FILE.exists() or REVIEW_FILE.stat().st_size == 0:
                f.write("# Usernames Needing Manual Review\n\n")
                f.write(f"**Last Updated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n")
                f.write("---\n\n")
            
            # Write new usernames with metadata
            for i, item in enumerate(new_review, current_count + 1):
                username = item['username'] or 'FAILED'
                url = f"https://www.instagram.com/{username}" if item['username'] else "N/A"
                confidence = item['confidence']
                verified = "✅" if item['verified'] == True else "❌" if item['verified'] == False else "⚠️"
                filename = item.get('filename', 'Unknown')
                
                # Write entry with all metadata
                f.write(f"{i}. **{username}** - {url}\n")
                f.write(f"   - **Image:** `{filename}`\n")
                f.write(f"   - Confidence: {confidence:.0f}% | URL: {verified}\n")
                
                # Include alternative candidates if multiple were found
                if 'all_candidates' in item and len(item['all_candidates']) > 1:
                    alternatives = [f"{k}({v})" for k, v in item['all_candidates'].items()]
                    f.write(f"   - Alternatives: {', '.join(alternatives)}\n")
                
                f.write("\n")
        
        # Update total count in header
        update_file_header(REVIEW_FILE, current_count + len(new_review))
    
    return len(new_verified), len(new_review)


def update_file_header(file_path, new_total):
    """
    Update the total count and timestamp in file header.
    
    This function reads the file, updates the "Total" and "Last Updated" lines,
    and writes it back. Maintains header formatting while updating statistics.
    
    PARAMETERS:
    - file_path: Path to markdown file to update
    - new_total: New total count to display in header
    
    PURPOSE FOR AI AGENTS:
    Keeps file headers accurate after appending new entries. Users see
    current totals without manually counting.
    """
    if not file_path.exists():
        return
    
    # Read entire file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Update relevant header lines
    for i, line in enumerate(lines):
        # Update total count
        if line.startswith('**Total Verified:**') or line.startswith('**Total Needing Review:**'):
            lines[i] = f"**Total:** {new_total}\n"
        # Update timestamp
        elif line.startswith('**Last Updated:**') or line.startswith('**Generated:**'):
            lines[i] = f"**Last Updated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def create_report(total_processed, new_verified, new_review, skipped):
    """
    Create extraction report for current run.
    
    Generates a summary markdown file showing:
    - Number of images processed
    - New usernames added to each file
    - Number of duplicates skipped
    - References to output files
    
    PARAMETERS:
    - total_processed: Total images in current batch
    - new_verified: Count of new verified usernames added
    - new_review: Count of new review-needed usernames added
    - skipped: Count of duplicates skipped
    
    PURPOSE FOR AI AGENTS:
    Provides audit trail of each extraction run. Users can track what was
    added in each batch and cumulative progress.
    """
    report_content = [
        "# Extraction Report - Current Run",
        "",
        f"**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        "",
        "## Current Run Summary",
        "",
        f"- **Images Processed:** {total_processed}",
        f"- **New Verified Added:** {new_verified}",
        f"- **New Review Added:** {new_review}",
        f"- **Duplicates Skipped:** {skipped}",
        "",
        "## Files",
        "",
        "1. ✅ `verified_usernames.md` - All verified usernames (cumulative)",
        "2. ⚠️ `needs_review.md` - All usernames needing review (cumulative)",
        ""
    ]
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_content))


# ============================================================================
# CLEANUP
# ============================================================================

def cleanup_debug_folder():
    """
    Delete temporary debug folder after processing.
    
    The debug folder contains preprocessed images from first 5 extractions.
    These are useful for troubleshooting but not needed after successful run.
    
    PURPOSE FOR AI AGENTS:
    Automatic cleanup prevents accumulation of temporary files. Debug images
    are only retained if user needs to troubleshoot issues.
    """
    try:
        if DEBUG_DIR.exists():
            shutil.rmtree(DEBUG_DIR)
            print(f"🗑️  Cleaned up debug folder")
    except Exception as e:
        print(f"⚠️  Could not delete debug folder: {e}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function - orchestrates entire extraction workflow.
    
    WORKFLOW:
    1. Parse command-line arguments for input directory
    2. Load existing usernames (duplicate detection)
    3. Find all images in input directory
    4. Confirm processing if large batch (>50 images)
    5. Process each image with OCR extraction
    6. Skip duplicates, track new usernames
    7. Append results to output files
    8. Generate report
    9. Cleanup debug files
    10. Display summary
    
    PURPOSE FOR AI AGENTS:
    This is the entry point. It coordinates all modules and provides user
    feedback throughout the extraction process.
    """
    print("=" * 70)
    print("INSTAGRAM USERNAME EXTRACTOR - TESSERACT MULTI-PASS")
    print("=" * 70)
    print()
    
    # Parse command-line arguments to get input directory
    INPUT_DIR = parse_arguments()
    
    # Load existing usernames for duplicate detection
    print("📂 Loading existing usernames...")
    existing_usernames = load_existing_usernames()
    print(f"   Found {len(existing_usernames)} existing usernames")
    print()
    
    # Verify input directory exists
    if not INPUT_DIR.exists():
        print(f"❌ Directory not found: {INPUT_DIR}")
        print(f"   Please create the folder or specify a different path.")
        return
    
    # Find all image files in directory
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    image_files = sorted([f for f in INPUT_DIR.iterdir() 
                          if f.is_file() and f.suffix.lower() in image_extensions])
    
    # Check if any images were found
    if not image_files:
        print(f"❌ No images found in {INPUT_DIR}")
        print(f"   Supported formats: {', '.join(image_extensions)}")
        return
    
    total = len(image_files)
    print(f"Found {total} images in {INPUT_DIR}")
    print()
    
    # Confirm processing for large batches
    if total > 50:
        est = total * 2 / 60  # Estimated minutes (2 seconds per image average)
        print(f"⚠️  Estimated time: ~{est:.0f} minutes")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        print()
    
    # Initialize tracking variables
    results = []
    start = time.time()
    skipped_duplicates = 0
    
    # Process each image
    for i, img_path in enumerate(image_files, 1):
        print(f"[{i}/{total}] {img_path.name}")
        
        # Extract username from image
        result = extract_username_from_image(img_path, save_debug=(i <= 5))
        result['filename'] = img_path.name
        
        # Check for duplicate
        if result['username'] and result['username'] in existing_usernames:
            print(f"  ⏭️  {result['username']} (duplicate - skipped)")
            skipped_duplicates += 1
            continue
        
        # Add to results
        results.append(result)
        
        # Display extraction result
        if result['username']:
            icon = "✅" if result['status'] == 'verified' else "⚠️"
            print(f"  {icon} {result['username']} ({result['confidence']:.0f}%)")
        else:
            print(f"  ❌ Failed")
    
    # Calculate elapsed time
    elapsed = time.time() - start
    
    print()
    print("=" * 70)
    print("SAVING RESULTS...")
    print("=" * 70)
    print()
    
    # Save results to files
    new_verified, new_review = append_to_files(results, existing_usernames)
    
    # Generate report
    create_report(total, new_verified, new_review, skipped_duplicates)
    
    # Cleanup temporary files
    cleanup_debug_folder()
    
    # Display summary
    print()
    print("✅ COMPLETE")
    print()
    print(f"⏱️  Time: {elapsed/60:.1f} minutes")
    print(f"📊 New entries: {new_verified + new_review}/{total}")
    print(f"⏭️  Duplicates skipped: {skipped_duplicates}")
    print()
    print(f"📁 OUTPUT FOLDER: {OUTPUT_DIR}")
    print()
    print("=" * 70)


# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Script entry point - only runs when executed directly.
    
    This allows the script to be imported as a module without auto-execution,
    while still functioning as a standalone command-line tool.
    """
    main()
