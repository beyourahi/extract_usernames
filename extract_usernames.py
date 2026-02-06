#!/usr/bin/env python3

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.data.dataloader')

import os
import re
import time
import shutil
import argparse
import platform
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
import easyocr
import requests
import torch
from datetime import datetime
from multiprocessing import Pool, cpu_count


TOP_OFFSET = 165
CROP_HEIGHT = 90
LEFT_MARGIN = 100
RIGHT_MARGIN = 100

OUTPUT_DIR = Path.home() / "Desktop" / "leads"
DEBUG_DIR = Path.home() / "Desktop" / "ocr_debug"

DEBUG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

VERIFIED_FILE = OUTPUT_DIR / "verified_usernames.md"
REVIEW_FILE = OUTPUT_DIR / "needs_review.md"
REPORT_FILE = OUTPUT_DIR / "extraction_report.md"


def detect_hardware():
    hardware_info = {
        'device': 'cpu',
        'device_name': 'CPU',
        'gpu_available': False,
        'gpu_type': None,
        'architecture': platform.machine(),
        'platform': platform.system(),
        'cpu_cores': cpu_count(),
        'optimal_workers': min(4, max(1, cpu_count() - 1))
    }
    
    if torch.cuda.is_available():
        hardware_info['device'] = 'cuda'
        hardware_info['device_name'] = torch.cuda.get_device_name(0)
        hardware_info['gpu_available'] = True
        
        device_name_upper = hardware_info['device_name'].upper()
        if 'AMD' in device_name_upper or 'RADEON' in device_name_upper:
            hardware_info['gpu_type'] = 'AMD ROCm'
        else:
            hardware_info['gpu_type'] = 'NVIDIA CUDA'
        
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        hardware_info['device'] = 'mps'
        hardware_info['device_name'] = f"Apple Silicon GPU ({platform.processor()})"
        hardware_info['gpu_available'] = True
        hardware_info['gpu_type'] = 'Apple Metal (MPS)'
        
    else:
        hardware_info['device'] = 'cpu'
        hardware_info['device_name'] = f"{cpu_count()}-core CPU"
        hardware_info['gpu_available'] = False
        hardware_info['gpu_type'] = None
    
    return hardware_info


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Extract Instagram usernames from screenshots using universal GPU/CPU acceleration',
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
        nargs='?',
        default='leads_images',
        help='Folder name (on Desktop) or absolute path to images (default: leads_images)'
    )
    
    args = parser.parse_args()
    folder_path = Path(args.folder)
    
    if folder_path.is_absolute():
        input_dir = folder_path
    else:
        input_dir = Path.home() / "Desktop" / args.folder
    
    return input_dir


def load_existing_usernames():
    existing_usernames = set()
    
    if VERIFIED_FILE.exists():
        with open(VERIFIED_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^\d+\.\s+(\w+(?:[._]\w+)*)\s+-\s+https?://.+?(?:\s+\[.+\])?$', line)
                if match:
                    existing_usernames.add(match.group(1))
    
    if REVIEW_FILE.exists():
        with open(REVIEW_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^\d+\.\s+\*\*(\w+(?:[._]\w+)*)\*\*\s+-\s+', line)
                if match:
                    existing_usernames.add(match.group(1))
    
    return existing_usernames


def preprocess_balanced(img_cv):
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    bilateral = cv2.bilateralFilter(enhanced, 9, 75, 75)
    upscaled = cv2.resize(bilateral, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
    median = cv2.medianBlur(upscaled, 3)
    thresh = cv2.adaptiveThreshold(median, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 8)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)


def preprocess_aggressive(img_cv):
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    upscaled = cv2.resize(enhanced, None, fx=4, fy=4, interpolation=cv2.INTER_LANCZOS4)
    _, thresh = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)


def preprocess_minimal(img_cv):
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    upscaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
    denoised = cv2.fastNlMeansDenoising(upscaled, None, 10, 7, 21)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)
    return thresh


PREPROCESS_VARIANTS = [
    ('balanced', preprocess_balanced),
    ('aggressive', preprocess_aggressive),
    ('minimal', preprocess_minimal),
]


def initialize_ocr_reader(use_gpu=True):
    return easyocr.Reader(
        ['en'],
        gpu=use_gpu,
        verbose=False,
        quantize=False,
        download_enabled=True
    )


_ocr_reader = None

def get_ocr_reader(use_gpu=True):
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = initialize_ocr_reader(use_gpu)
    return _ocr_reader


def ocr_extract_username(img_cv, use_gpu=True):
    reader = get_ocr_reader(use_gpu)
    results_per_variant = []

    for variant_name, preprocessor in PREPROCESS_VARIANTS:
        try:
            processed = preprocessor(img_cv)
            ocr_results = reader.readtext(processed)

            best_username = None
            best_confidence = 0

            for (bbox, text, confidence) in ocr_results:
                username = clean_username(text)
                if username and confidence > best_confidence:
                    best_username = username
                    best_confidence = confidence * 100

            if best_username:
                results_per_variant.append({
                    'username': best_username,
                    'confidence': best_confidence,
                    'variant': variant_name,
                })
        except Exception:
            continue

    if not results_per_variant:
        return None, 0

    votes = {}
    for r in results_per_variant:
        u = r['username']
        if u not in votes:
            votes[u] = {'count': 0, 'total_conf': 0, 'max_conf': 0}
        votes[u]['count'] += 1
        votes[u]['total_conf'] += r['confidence']
        votes[u]['max_conf'] = max(votes[u]['max_conf'], r['confidence'])

    for username, v in sorted(votes.items(), key=lambda x: x[1]['count'], reverse=True):
        if v['count'] >= 2:
            return username, v['total_conf'] / v['count']

    best = max(results_per_variant, key=lambda x: x['confidence'])
    return best['username'], best['confidence']


def clean_username(text):
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


CHAR_CONFUSION = {
    'l': ['1', 'i'],
    '1': ['l', 'i'],
    'i': ['l', '1'],
    'o': ['0'],
    '0': ['o'],
}

MULTI_CHAR_CONFUSION = [
    ('rn', 'm'),
    ('m', 'rn'),
    ('vv', 'w'),
    ('w', 'vv'),
    ('cl', 'd'),
    ('ii', 'u'),
]


def generate_username_candidates(username):
    if not username:
        return []

    candidates = [username]

    for i, char in enumerate(username):
        if char in CHAR_CONFUSION:
            for replacement in CHAR_CONFUSION[char]:
                candidate = username[:i] + replacement + username[i+1:]
                cleaned = clean_username(candidate)
                if cleaned and cleaned not in candidates:
                    candidates.append(cleaned)

    for wrong, right in MULTI_CHAR_CONFUSION:
        if wrong in username:
            candidate = username.replace(wrong, right, 1)
            cleaned = clean_username(candidate)
            if cleaned and cleaned not in candidates:
                candidates.append(cleaned)

    return candidates[:10]


def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_similar_existing(username, existing_usernames, max_distance=2):
    if not username or not existing_usernames:
        return None

    best_match = None
    best_dist = max_distance + 1

    for existing in existing_usernames:
        if abs(len(existing) - len(username)) > max_distance:
            continue
        dist = levenshtein_distance(username, existing)
        if 0 < dist < best_dist:
            best_match = existing
            best_dist = dist

    if best_match:
        return best_match, best_dist
    return None


def calculate_image_quality(img_cv):
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness = min(laplacian_var / 500, 1.0)
    contrast = min(gray.std() / 60, 1.0)
    mean_brightness = gray.mean()
    brightness = 1.0 - abs(mean_brightness - 128) / 128
    return sharpness * 0.4 + contrast * 0.4 + brightness * 0.2


def adjust_confidence(confidence, quality_score):
    if quality_score > 0.7:
        adjusted = confidence * (1 + (quality_score - 0.7) * 0.3)
    elif quality_score < 0.5:
        adjusted = confidence * (0.7 + quality_score * 0.6)
    else:
        adjusted = confidence
    return min(adjusted, 100)


def check_instagram_exists(username, max_retries=3):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    for attempt in range(max_retries):
        try:
            response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                return True
            elif response.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            else:
                return False
        except requests.RequestException:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return None

    return None


def extract_username_from_image_parallel(args):
    image_path, image_index, total_images, existing_usernames, use_gpu = args

    result = extract_username_from_image(image_path, use_gpu, save_debug=(image_index <= 5))
    result['filename'] = image_path.name
    result['index'] = image_index
    result['is_duplicate'] = False
    result['is_near_duplicate'] = False
    result['similar_to'] = None

    if result['username']:
        if result['username'] in existing_usernames:
            result['is_duplicate'] = True
        else:
            similar = find_similar_existing(result['username'], existing_usernames)
            if similar:
                result['is_near_duplicate'] = True
                result['similar_to'] = similar[0]
                result['edit_distance'] = similar[1]

    if result['is_duplicate']:
        status_icon = "⏭️"
        username_display = result['username']
        detail_text = " (duplicate)"

    elif result['is_near_duplicate']:
        status_icon = "🔍"
        username_display = result['username']
        detail_text = f" (near-duplicate of {result['similar_to']})"

    elif not result['username']:
        status_icon = "❌"
        username_display = "Failed"
        detail_text = ""

    else:
        username_display = result['username']

        if result['status'] == 'verified':
            status_icon = "✅"
            detail_text = f" ({result['confidence']:.0f}% | URL: ✅)"

        elif result['status'] == 'unverified':
            status_icon = "⚠️"
            detail_text = f" ({result['confidence']:.0f}% | URL: ⚠️ network error)"

        else:
            status_icon = "⚠️"
            url_icon = "✅" if result['verified'] is True else "❌" if result['verified'] is False else "⚠️"
            detail_text = f" ({result['confidence']:.0f}% | URL: {url_icon})"

    print(f"[{image_index}/{total_images}] {image_path.name} -> {status_icon} {username_display}{detail_text}")

    return result


def extract_username_from_image(image_path, use_gpu=True, save_debug=False):
    try:
        img_cv = cv2.imread(str(image_path))
        height, width = img_cv.shape[:2]

        left = LEFT_MARGIN
        top = TOP_OFFSET
        right = width - RIGHT_MARGIN
        bottom = top + CROP_HEIGHT

        cropped = img_cv[top:bottom, left:right]

        if save_debug:
            debug_path = DEBUG_DIR / f"{image_path.stem}_crop.png"
            preprocessed = preprocess_balanced(cropped)
            cv2.imwrite(str(debug_path), preprocessed)

        username, confidence = ocr_extract_username(cropped, use_gpu)

        if not username:
            return {
                'username': None,
                'confidence': 0,
                'verified': False,
                'status': 'failed',
                'quality': 0,
            }

        quality = calculate_image_quality(cropped)
        confidence = adjust_confidence(confidence, quality)

        candidates = generate_username_candidates(username)
        best_username = username
        url_verified = None

        for candidate in candidates:
            result = check_instagram_exists(candidate)
            if result is True:
                best_username = candidate
                url_verified = True
                break
            elif result is False and url_verified is None:
                url_verified = False
            elif result is None and url_verified is None:
                url_verified = None

        username = best_username

        if confidence >= 85 and url_verified is True:
            status = 'verified'
        elif confidence >= 70 and url_verified is True:
            status = 'verified'
        elif confidence >= 70 and url_verified is None:
            status = 'unverified'
        else:
            status = 'review'

        return {
            'username': username,
            'confidence': confidence,
            'verified': url_verified,
            'status': status,
            'quality': quality,
        }

    except Exception as e:
        return {
            'username': None,
            'confidence': 0,
            'verified': False,
            'status': 'error',
            'error': str(e),
            'quality': 0,
        }


def append_to_files(new_results, existing_usernames):
    new_verified = [r for r in new_results
                    if r['status'] == 'verified'
                    and not r.get('is_duplicate', False)
                    and not r.get('is_near_duplicate', False)]

    new_review = [r for r in new_results
                  if (r['status'] in ['review', 'unverified', 'error']
                      or r.get('is_near_duplicate', False))
                  and not r.get('is_duplicate', False)]

    if new_verified:
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
                conf = item['confidence']
                tier = "HIGH" if conf >= 85 else "MED"
                f.write(f"{i}. {item['username']} - {url} [{tier} {conf:.0f}%]\n")

        update_file_header(VERIFIED_FILE, current_count + len(new_verified))

    if new_review:
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
                verified = "✅" if item.get('verified') is True else "❌" if item.get('verified') is False else "⚠️"
                filename = item.get('filename', 'Unknown')
                quality = item.get('quality', 0)

                f.write(f"{i}. **{username}** - {url}\n")
                f.write(f"   - **Image:** `{filename}`\n")
                f.write(f"   - Confidence: {confidence:.0f}% | URL: {verified} | Quality: {quality:.2f}\n")
                if item.get('is_near_duplicate'):
                    f.write(f"   - **Near-duplicate of:** {item.get('similar_to', '?')} (edit distance: {item.get('edit_distance', '?')})\n")
                f.write("\n")

        update_file_header(REVIEW_FILE, current_count + len(new_review))

    return len(new_verified), len(new_review)


def update_file_header(file_path, new_total):
    if not file_path.exists():
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    timestamp = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    
    updated_lines = []
    for line in lines:
        if line.startswith('**Last Updated:**'):
            updated_lines.append(f"**Last Updated:** {timestamp}\n")
        elif line.startswith('**Total:**'):
            updated_lines.append(f"**Total:** {new_total}\n")
        else:
            updated_lines.append(line)
    
    if '**Total:**' not in ''.join(updated_lines):
        for i, line in enumerate(updated_lines):
            if line.startswith('**Last Updated:**'):
                updated_lines.insert(i + 1, f"**Total:** {new_total}\n")
                break
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)


def generate_report(hardware_info, input_dir, results, elapsed_time, new_verified, new_review):
    total = len(results)
    verified = sum(1 for r in results if r['status'] == 'verified'
                   and not r.get('is_duplicate') and not r.get('is_near_duplicate'))
    review = sum(1 for r in results if r['status'] in ['review', 'unverified']
                 or r.get('is_near_duplicate', False))
    failed = sum(1 for r in results if r['status'] in ['failed', 'error'])
    duplicates = sum(1 for r in results if r.get('is_duplicate', False))
    near_dupes = sum(1 for r in results if r.get('is_near_duplicate', False))
    high_conf = sum(1 for r in results if r['status'] == 'verified' and r['confidence'] >= 85)
    med_conf = sum(1 for r in results if r['status'] == 'verified' and 70 <= r['confidence'] < 85)

    extracted = [r for r in results if r['username']]
    avg_confidence = sum(r['confidence'] for r in extracted) / max(1, len(extracted))
    avg_quality = sum(r.get('quality', 0) for r in extracted) / max(1, len(extracted))
    images_per_second = total / elapsed_time if elapsed_time > 0 else 0

    report = f"""# Instagram Username Extraction Report

**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

---

## Hardware Configuration

- **Device:** {hardware_info['device_name']}
- **GPU Available:** {'Yes' if hardware_info['gpu_available'] else 'No'}
- **GPU Type:** {hardware_info['gpu_type'] or 'N/A'}
- **Architecture:** {hardware_info['architecture']}
- **Platform:** {hardware_info['platform']}
- **CPU Cores:** {hardware_info['cpu_cores']}
- **Worker Processes:** {hardware_info['optimal_workers']}

---

## Input

- **Directory:** `{input_dir}`
- **Total Images:** {total}

---

## Results Summary

- ✅ **Verified:** {verified} ({verified/max(1,total)*100:.1f}%)
  - HIGH confidence (>=85%): {high_conf}
  - MED confidence (70-84%): {med_conf}
- ⚠️ **Needs Review:** {review} ({review/max(1,total)*100:.1f}%)
- ❌ **Failed:** {failed} ({failed/max(1,total)*100:.1f}%)
- ⏭️ **Duplicates:** {duplicates} ({duplicates/max(1,total)*100:.1f}%)
- 🔍 **Near-Duplicates:** {near_dupes} ({near_dupes/max(1,total)*100:.1f}%)

---

## New Entries Added

- **Verified List:** {new_verified} new usernames
- **Review List:** {new_review} new usernames

---

## Performance Metrics

- **Total Time:** {elapsed_time:.2f} seconds
- **Average Time per Image:** {elapsed_time/max(1,total):.2f} seconds
- **Processing Speed:** {images_per_second:.2f} images/second
- **Average Confidence:** {avg_confidence:.1f}%
- **Average Image Quality:** {avg_quality:.2f}

---

## Pipeline Configuration

- **OCR Engine:** EasyOCR (multi-pass, 3 preprocessing variants)
- **Preprocessing:** Balanced + Aggressive + Minimal (voting)
- **Confidence Tiers:** HIGH >=85% | MED >=70% | REVIEW <70%
- **Character Correction:** Enabled (confusion map + candidates)
- **Near-Duplicate Detection:** Enabled (Levenshtein distance <=2)

---

## Output Files

- ✅ **Verified Usernames:** `{VERIFIED_FILE}`
- ⚠️ **Needs Review:** `{REVIEW_FILE}`
- 📊 **This Report:** `{REPORT_FILE}`

---

**Next Steps:**
1. Review usernames in `needs_review.md` (especially near-duplicates)
2. Verify low-confidence results manually
3. Use verified list for your workflow
"""

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)


def main():
    print("\n" + "="*70)
    print("Instagram Username Extractor - Universal GPU/CPU Acceleration")
    print("="*70 + "\n")
    
    input_dir = parse_arguments()
    
    if not input_dir.exists():
        print(f"❌ Error: Directory not found: {input_dir}")
        print(f"\n💡 Tip: Place images in ~/Desktop/leads_images or specify custom path")
        return
    
    print("🔍 Detecting hardware...\n")
    hardware_info = detect_hardware()
    
    print(f"   Device: {hardware_info['device_name']}")
    print(f"   GPU: {'✅ ' + hardware_info['gpu_type'] if hardware_info['gpu_available'] else '❌ Not available'}")
    print(f"   Workers: {hardware_info['optimal_workers']} parallel processes")
    print()
    
    print(f"📁 Scanning directory: {input_dir}\n")
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_paths = [p for p in input_dir.iterdir() 
                  if p.suffix.lower() in image_extensions]
    
    if not image_paths:
        print(f"❌ No images found in {input_dir}")
        print(f"   Supported formats: {', '.join(image_extensions)}")
        return
    
    print(f"   Found {len(image_paths)} images\n")
    
    print("🔄 Loading existing usernames...")
    existing_usernames = load_existing_usernames()
    print(f"   Loaded {len(existing_usernames)} existing usernames\n")
    
    use_gpu = hardware_info['gpu_available']
    args_list = [
        (path, idx, len(image_paths), existing_usernames, use_gpu)
        for idx, path in enumerate(image_paths, 1)
    ]
    
    print(f"🚀 Processing {len(image_paths)} images...\n")
    start_time = time.time()
    
    with Pool(processes=hardware_info['optimal_workers']) as pool:
        results = pool.map(extract_username_from_image_parallel, args_list)
    
    elapsed_time = time.time() - start_time
    
    print(f"\n💾 Saving results...")
    new_verified, new_review = append_to_files(results, existing_usernames)
    
    generate_report(hardware_info, input_dir, results, elapsed_time, new_verified, new_review)
    
    if DEBUG_DIR.exists():
        shutil.rmtree(DEBUG_DIR)
    
    print(f"\n{'='*70}")
    print("✅ EXTRACTION COMPLETE")
    print(f"{'='*70}\n")
    
    print(f"📊 Results:")
    print(f"   • New verified: {new_verified}")
    print(f"   • New for review: {new_review}")
    print(f"   • Processing time: {elapsed_time:.2f}s")
    print(f"   • Speed: {len(image_paths)/elapsed_time:.2f} images/sec\n")
    
    print(f"📁 Output files:")
    print(f"   • {VERIFIED_FILE}")
    print(f"   • {REVIEW_FILE}")
    print(f"   • {REPORT_FILE}\n")


if __name__ == '__main__':
    main()
