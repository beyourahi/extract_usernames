#!/usr/bin/env python3

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
                match = re.match(r'^\d+\.\s+(\w+(?:[._]\w+)*)\s+-\s+https?://', line)
                if match:
                    existing_usernames.add(match.group(1))
    
    if REVIEW_FILE.exists():
        with open(REVIEW_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^\d+\.\s+\*\*(\w+(?:[._]\w+)*)\*\*\s+-\s+', line)
                if match:
                    existing_usernames.add(match.group(1))
    
    return existing_usernames


def preprocess_image(img_cv):
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    upscaled = cv2.resize(denoised, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    thresh = cv2.adaptiveThreshold(upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 8)
    kernel = np.ones((2, 2), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    return processed


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
    try:
        reader = get_ocr_reader(use_gpu)
        processed = preprocess_image(img_cv)
        results = reader.readtext(processed)
        
        best_username = None
        best_confidence = 0
        
        for (bbox, text, confidence) in results:
            username = clean_username(text)
            if username and confidence > best_confidence:
                best_username = username
                best_confidence = confidence * 100
        
        return best_username, best_confidence
        
    except Exception as e:
        print(f"   OCR Error: {e}")
        return None, 0


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


def check_instagram_exists(username):
    try:
        url = f"https://www.instagram.com/{username}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        return None


def extract_username_from_image_parallel(args):
    image_path, image_index, total_images, existing_usernames, use_gpu = args
    
    result = extract_username_from_image(image_path, use_gpu, save_debug=(image_index <= 5))
    result['filename'] = image_path.name
    result['index'] = image_index
    
    if result['username'] and result['username'] in existing_usernames:
        result['is_duplicate'] = True
    else:
        result['is_duplicate'] = False
    
    if result['is_duplicate']:
        status_icon = "⏭️"
        username_display = result['username']
        detail_text = " (duplicate)"
        
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
            url_icon = "✅" if result['verified'] == True else "❌" if result['verified'] == False else "⚠️"
            detail_text = f" ({result['confidence']:.0f}% | URL: {url_icon})"
    
    print(f"[{image_index}/{total_images}] {image_path.name} → {status_icon} {username_display}{detail_text}")
    
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
            preprocessed = preprocess_image(cropped)
            cv2.imwrite(str(debug_path), preprocessed)
        
        username, confidence = ocr_extract_username(cropped, use_gpu)
        
        if not username:
            return {
                'username': None,
                'confidence': 0,
                'verified': False,
                'status': 'failed'
            }
        
        url_verified = check_instagram_exists(username)
        
        if confidence >= 60 and url_verified == True:
            status = 'verified'
        elif confidence >= 60 and url_verified == None:
            status = 'unverified'
        else:
            status = 'review'
        
        return {
            'username': username,
            'confidence': confidence,
            'verified': url_verified,
            'status': status
        }
        
    except Exception as e:
        return {
            'username': None,
            'confidence': 0,
            'verified': False,
            'status': 'error',
            'error': str(e)
        }


def append_to_files(new_results, existing_usernames):
    new_verified = [r for r in new_results 
                   if r['status'] == 'verified' 
                   and not r.get('is_duplicate', False)]
    
    new_review = [r for r in new_results 
                 if r['status'] in ['review', 'unverified', 'error'] 
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
                f.write(f"{i}. {item['username']} - {url}\n")
        
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
                verified = "✅" if item['verified'] == True else "❌" if item['verified'] == False else "⚠️"
                filename = item.get('filename', 'Unknown')
                
                f.write(f"{i}. **{username}** - {url}\n")
                f.write(f"   - **Image:** `{filename}`\n")
                f.write(f"   - Confidence: {confidence:.0f}% | URL: {verified}\n\n")
        
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
    verified = sum(1 for r in results if r['status'] == 'verified')
    review = sum(1 for r in results if r['status'] in ['review', 'unverified'])
    failed = sum(1 for r in results if r['status'] in ['failed', 'error'])
    duplicates = sum(1 for r in results if r.get('is_duplicate', False))
    
    avg_confidence = sum(r['confidence'] for r in results if r['username']) / max(1, total - failed)
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
- ⚠️ **Needs Review:** {review} ({review/max(1,total)*100:.1f}%)
- ❌ **Failed:** {failed} ({failed/max(1,total)*100:.1f}%)
- ⏭️ **Duplicates:** {duplicates} ({duplicates/max(1,total)*100:.1f}%)

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

---

## Output Files

- ✅ **Verified Usernames:** `{VERIFIED_FILE}`
- ⚠️ **Needs Review:** `{REVIEW_FILE}`
- 📊 **This Report:** `{REPORT_FILE}`

---

**Next Steps:**
1. Review usernames in `needs_review.md`
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
