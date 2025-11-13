#!/usr/bin/env python3
"""
Dry run to check feasibility of backfilling images for existing listings.
Checks how many listings have image URLs available and tests download success rate.
"""

import csv
import glob
import requests
from requests.auth import HTTPBasicAuth
from import_to_wordpress_api_safe import _download_image_bytes
import os
import sys

WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
WP_USER = os.getenv("WP_USER") or os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")

def build_image_map():
    """Build URL -> image mapping from all CSV files"""
    files = []
    files += glob.glob('data/processed/monthly_candidates_*.csv')
    for st in ['AZ','CA','CO','ID','NM','UT']:
        files += glob.glob(f'{st}_seniorplace_data_*.csv')
    
    url_to_img = {}
    url_to_title = {}
    
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    u = (row.get('url') or '').strip()
                    img = (row.get('featured_image') or '').strip()
                    t = (row.get('title') or '').strip()
                    if u and img and u not in url_to_img:
                        url_to_img[u] = img
                        url_to_title[u] = t
        except Exception:
            continue
    
    return url_to_img, url_to_title


def get_listings_without_images(limit=500):
    """Fetch listings without featured images"""
    no_img_ids = []
    page = 1
    
    while len(no_img_ids) < limit and page <= 20:  # Max 20 pages = 2000 listings
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/listing",
                params={
                    'per_page': 100,
                    'orderby': 'date',
                    'order': 'desc',
                    'page': page
                },
                auth=HTTPBasicAuth(WP_USER, WP_PASS),
                timeout=20
            )
            if r.status_code != 200:
                break
            
            listings = r.json()
            if not listings:
                break
            
            for p in listings:
                if not p.get('featured_media'):
                    no_img_ids.append({
                        'id': p['id'],
                        'title': (p.get('title', {}) or {}).get('rendered', ''),
                        'sp_url': ((p.get('acf') or {}).get('senior_place_url') or '').strip()
                    })
            
            if len(listings) < 100:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
    
    return no_img_ids


def test_image_download(image_url):
    """Test if image URL is accessible"""
    try:
        data = _download_image_bytes(image_url)
        if data:
            return True, len(data)
        return False, 0
    except Exception as e:
        return False, 0


def main():
    if not WP_USER or not WP_PASS:
        print("❌ Missing WordPress credentials. Please set WP_USER/WP_PASS (or WP_USERNAME/WP_PASSWORD).")
        sys.exit(1)
    print("=" * 80)
    print("IMAGE BACKFILL DRY RUN")
    print("=" * 80)
    print()
    
    # Build image map
    print("📥 Building image URL map from CSVs...")
    url_to_img, url_to_title = build_image_map()
    print(f"✅ Found {len(url_to_img)} image URLs in CSVs\n")
    
    # Get listings without images
    print("📥 Fetching listings without featured images...")
    listings = get_listings_without_images(limit=500)
    print(f"✅ Found {len(listings)} listings without images\n")
    
    # Analyze
    print("🔍 Analyzing...")
    print()
    
    has_image_url = 0
    no_image_url = 0
    download_tests = []
    
    for listing in listings:
        sp_url = listing['sp_url']
        if not sp_url:
            no_image_url += 1
            continue
        
        img_url = url_to_img.get(sp_url)
        if img_url:
            has_image_url += 1
            # Test download for first 50
            if len(download_tests) < 50:
                success, size = test_image_download(img_url)
                download_tests.append((success, size))
        else:
            no_image_url += 1
    
    # Results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total listings without images: {len(listings)}")
    print(f"  ✅ Have image URL in CSV: {has_image_url} ({has_image_url/len(listings)*100:.1f}%)")
    print(f"  ❌ No image URL found: {no_image_url} ({no_image_url/len(listings)*100:.1f}%)")
    print()
    
    if download_tests:
        successful = sum(1 for s, _ in download_tests if s)
        total_size = sum(s for _, s in download_tests if s)
        avg_size = total_size / successful if successful > 0 else 0
        
        print(f"Image download test (sampled {len(download_tests)} URLs):")
        print(f"  ✅ Downloadable: {successful}/{len(download_tests)} ({successful/len(download_tests)*100:.1f}%)")
        print(f"  ❌ Failed: {len(download_tests) - successful}")
        if successful > 0:
            print(f"  📊 Average size: {avg_size/1024:.1f} KB")
        print()
    
    # Estimate
    if download_tests and successful > 0:
        success_rate = successful / len(download_tests)
        estimated_successful = int(has_image_url * success_rate)
        print("=" * 80)
        print("ESTIMATE")
        print("=" * 80)
        print(f"Estimated backfillable listings: ~{estimated_successful} out of {len(listings)}")
        print(f"Estimated time: ~{estimated_successful * 2 / 60:.1f} minutes (2 sec per image)")
        print()
    
    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    if has_image_url > 0 and (not download_tests or successful / len(download_tests) > 0.7):
        print("✅ Feasible! Most listings have image URLs and they're accessible.")
        print("   Run the actual backfill script to process them.")
    elif has_image_url > 0:
        print("⚠️  Some listings have URLs but many may be inaccessible.")
        print("   Worth trying a batch to see actual success rate.")
    else:
        print("❌ Not feasible - most listings don't have image URLs in our CSVs.")
    print()


if __name__ == '__main__':
    main()


