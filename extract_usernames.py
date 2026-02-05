#!/usr/bin/env python3

"""
Instagram Username Extractor - Tesseract Only with Advanced Multi-Pass
With duplicate detection and append functionality
"""

import os
import re
import time
import shutil
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
import pytesseract
import requests
from datetime import datetime
from collections import Counter

INPUT_DIR = Path.home() / "Desktop" / "leads_images"
DEBUG_DIR = Path.home() / "Desktop" / "ocr_debug"

# Create output directory
OUTPUT_DIR = Path.home() / "Desktop" / "leads"

VERIFIED_FILE = OUTPUT_DIR / "verified_usernames.md"
REVIEW_FILE = OUTPUT_DIR / "needs_review.md"
REPORT_FILE = OUTPUT_DIR / "extraction_report.md"

TOP_OFFSET = 165
CROP_HEIGHT = 90
LEFT_MARGIN = 100
RIGHT_MARGIN = 100

CONFIDENCE_THRESHOLD = 60

DEBUG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def load_existing_usernames():
    """Load existing usernames from both files to avoid duplicates"""
    existing_usernames = set()
    
    # Load from verified file
    if VERIFIED_FILE.exists():
        with open(VERIFIED_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                # Match pattern: "123. username - url"
                match = re.match(r'^\d+\.\s+(\w+(?:[._]\w+)*)\s+-\s+https?://', line)
                if match:
                    existing_usernames.add(match.group(1))
    
    # Load from review file
    if REVIEW_FILE.exists():
        with open(REVIEW_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                # Match pattern: "123. **username** - url"
                match = re.match(r'^\d+\.\s+\*\*(\w+(?:[._]\w+)*)\*\*\s+-\s+', line)
                if match:
                    existing_usernames.add(match.group(1))
    
    return existing_usernames


def preprocess_adaptive_gaussian(img):
    """Adaptive Gaussian - Best for varying lighting"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    thresh = cv2.adaptiveThreshold(upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 8)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)


def preprocess_otsu(img):
    """Otsu - Auto threshold detection"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    blurred = cv2.GaussianBlur(upscaled, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def preprocess_clahe(img):
    """CLAHE - Enhanced contrast"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=7, fy=7, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(upscaled)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)


def preprocess_bilateral(img):
    """Bilateral filter - Preserves edges"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    upscaled = cv2.resize(filtered, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def preprocess_adaptive_mean(img):
    """Adaptive Mean"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    thresh = cv2.adaptiveThreshold(upscaled, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10)
    return thresh


def ocr_tesseract_multipass(img_cv, save_debug_path=None):
    """Run Tesseract with multiple preprocessing methods and PSM modes"""
    
    preprocessing_methods = [
        ('adaptive_gaussian', preprocess_adaptive_gaussian),
        ('otsu', preprocess_otsu),
        ('clahe', preprocess_clahe),
        ('bilateral', preprocess_bilateral),
        ('adaptive_mean', preprocess_adaptive_mean),
    ]
    
    psm_modes = [7, 8, 13]
    
    all_results = []
    
    for method_name, preprocess_func in preprocessing_methods:
        processed = preprocess_func(img_cv.copy())
        
        if save_debug_path and method_name == 'adaptive_gaussian':
            cv2.imwrite(str(save_debug_path), processed)
        
        pil_img = Image.fromarray(processed)
        
        for psm in psm_modes:
            config = f'--psm {psm} --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz0123456789._'
            text = pytesseract.image_to_string(pil_img, config=config).strip()
            username = clean_username(text)
            if username:
                all_results.append(username)
    
    return all_results


def check_instagram_exists(username):
    """Verify Instagram username exists"""
    try:
        url = f"https://www.instagram.com/{username}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        return None


def extract_username_from_image(image_path, save_debug=True):
    """Extract username with multi-pass Tesseract"""
    try:
        img_cv = cv2.imread(str(image_path))
        height, width = img_cv.shape[:2]
        
        left = LEFT_MARGIN
        top = TOP_OFFSET
        right = width - RIGHT_MARGIN
        bottom = top + CROP_HEIGHT
        
        cropped = img_cv[top:bottom, left:right]
        
        debug_path = DEBUG_DIR / f"{image_path.stem}_crop.png" if save_debug else None
        
        all_results = ocr_tesseract_multipass(cropped, debug_path)
        
        if not all_results:
            return {
                'username': None,
                'confidence': 0,
                'verified': False,
                'status': 'failed'
            }
        
        counter = Counter(all_results)
        best_username = max(counter.items(), key=lambda x: (x[1], len(x[0])))[0]
        vote_count = counter[best_username]
        total_votes = len(all_results)
        confidence = (vote_count / total_votes) * 100
        
        url_verified = check_instagram_exists(best_username)
        
        if confidence >= CONFIDENCE_THRESHOLD and url_verified == True:
            status = 'verified'
        elif confidence >= CONFIDENCE_THRESHOLD and url_verified == None:
            status = 'unverified'
        else:
            status = 'review'
        
        return {
            'username': best_username,
            'confidence': confidence,
            'verified': url_verified,
            'status': status,
            'all_candidates': dict(counter)
        }
        
    except Exception as e:
        return {
            'username': None,
            'confidence': 0,
            'verified': False,
            'status': 'error',
            'error': str(e)
        }


def clean_username(text):
    """Clean and validate username"""
    if not text:
        return None
    
    text = text.lower().strip()
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[^\w._]', '', text)
    text = text.strip('._')
    
    if len(text) < 1 or len(text) > 30:
        return None
    
    if text and not text[0].isalnum():
        return None
    
    if text.endswith('.'):
        return None
    
    if not any(c.isalnum() for c in text):
        return None
    
    return text


def append_to_files(new_results, existing_usernames):
    """Append only new usernames to existing files"""
    
    # Filter out duplicates
    new_verified = [r for r in new_results if r['status'] == 'verified' and r['username'] not in existing_usernames]
    new_review = [r for r in new_results if r['status'] in ['review', 'unverified', 'error'] and (r['username'] not in existing_usernames if r['username'] else True)]
    
    # Count totals including existing
    total_verified_count = len(existing_usernames.intersection({r['username'] for r in new_results if r['status'] == 'verified'}))
    total_review_count = len(existing_usernames.intersection({r['username'] for r in new_results if r['status'] in ['review', 'unverified', 'error'] and r['username']}))
    
    # Append to verified file
    if new_verified:
        # Get current count
        current_count = 0
        if VERIFIED_FILE.exists():
            with open(VERIFIED_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if re.match(r'^\d+\.', line):
                        current_count += 1
        
        with open(VERIFIED_FILE, 'a', encoding='utf-8') as f:
            if not VERIFIED_FILE.exists() or VERIFIED_FILE.stat().st_size == 0:
                f.write("# Verified Instagram Usernames\n\n")
                f.write(f"**Last Updated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n")
                f.write("---\n\n")
            
            for i, item in enumerate(new_verified, current_count + 1):
                url = f"https://www.instagram.com/{item['username']}"
                f.write(f"{i}. {item['username']} - {url}\n")
        
        # Update header with new total
        update_file_header(VERIFIED_FILE, current_count + len(new_verified))
    
    # Append to review file
    if new_review:
        # Get current count
        current_count = 0
        if REVIEW_FILE.exists():
            with open(REVIEW_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if re.match(r'^\d+\.\s+\*\*', line):
                        current_count += 1
        
        with open(REVIEW_FILE, 'a', encoding='utf-8') as f:
            if not REVIEW_FILE.exists() or REVIEW_FILE.stat().st_size == 0:
                f.write("# Usernames Needing Manual Review\n\n")
                f.write(f"**Last Updated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n")
                f.write("---\n\n")
            
            for i, item in enumerate(new_review, current_count + 1):
                username = item['username'] or 'FAILED'
                url = f"https://www.instagram.com/{username}" if item['username'] else "N/A"
                confidence = item['confidence']
                verified = "✅" if item['verified'] == True else "❌" if item['verified'] == False else "⚠️"
                filename = item.get('filename', 'Unknown')
                
                f.write(f"{i}. **{username}** - {url}\n")
                f.write(f"   - **Image:** `{filename}`\n")
                f.write(f"   - Confidence: {confidence:.0f}% | URL: {verified}\n")
                
                if 'all_candidates' in item and len(item['all_candidates']) > 1:
                    alternatives = [f"{k}({v})" for k, v in item['all_candidates'].items()]
                    f.write(f"   - Alternatives: {', '.join(alternatives)}\n")
                
                f.write("\n")
        
        # Update header
        update_file_header(REVIEW_FILE, current_count + len(new_review))
    
    return len(new_verified), len(new_review)


def update_file_header(file_path, new_total):
    """Update the total count in file header"""
    if not file_path.exists():
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Update the total and date
    for i, line in enumerate(lines):
        if line.startswith('**Total Verified:**') or line.startswith('**Total Needing Review:**'):
            lines[i] = f"**Total:** {new_total}\n"
        elif line.startswith('**Last Updated:**') or line.startswith('**Generated:**'):
            lines[i] = f"**Last Updated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def create_report(total_processed, new_verified, new_review, skipped):
    """Create report for current run"""
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


def cleanup_debug_folder():
    """Delete the debug folder after processing"""
    try:
        if DEBUG_DIR.exists():
            shutil.rmtree(DEBUG_DIR)
            print(f"🗑️  Cleaned up debug folder")
    except Exception as e:
        print(f"⚠️  Could not delete debug folder: {e}")


def main():
    print("=" * 70)
    print("INSTAGRAM USERNAME EXTRACTOR - TESSERACT MULTI-PASS")
    print("=" * 70)
    print()
    
    # Load existing usernames
    print("📂 Loading existing usernames...")
    existing_usernames = load_existing_usernames()
    print(f"   Found {len(existing_usernames)} existing usernames")
    print()
    
    if not INPUT_DIR.exists():
        print(f"❌ Directory not found: {INPUT_DIR}")
        return
    
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    image_files = sorted([f for f in INPUT_DIR.iterdir() 
                          if f.is_file() and f.suffix.lower() in image_extensions])
    
    if not image_files:
        print(f"❌ No images found")
        return
    
    total = len(image_files)
    print(f"Found {total} images")
    print()
    
    if total > 50:
        est = total * 2 / 60
        print(f"⚠️  Estimated time: ~{est:.0f} minutes")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            return
        print()
    
    results = []
    start = time.time()
    skipped_duplicates = 0
    
    for i, img_path in enumerate(image_files, 1):
        print(f"[{i}/{total}] {img_path.name}")
        
        result = extract_username_from_image(img_path, save_debug=(i <= 5))
        result['filename'] = img_path.name
        
        # Check if duplicate
        if result['username'] and result['username'] in existing_usernames:
            print(f"  ⏭️  {result['username']} (duplicate - skipped)")
            skipped_duplicates += 1
            continue
        
        results.append(result)
        
        if result['username']:
            icon = "✅" if result['status'] == 'verified' else "⚠️"
            print(f"  {icon} {result['username']} ({result['confidence']:.0f}%)")
        else:
            print(f"  ❌ Failed")
    
    elapsed = time.time() - start
    
    print()
    print("=" * 70)
    print("SAVING RESULTS...")
    print("=" * 70)
    print()
    
    new_verified, new_review = append_to_files(results, existing_usernames)
    create_report(total, new_verified, new_review, skipped_duplicates)
    
    # Cleanup debug folder
    cleanup_debug_folder()
    
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


if __name__ == "__main__":
    main()
