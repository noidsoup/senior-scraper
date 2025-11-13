#!/usr/bin/env python3
"""
WordPress REST API Import Script
Imports Senior Place listings to WordPress using REST API

Usage:
    python3 import_to_wordpress_api.py <csv_file> [--test-only] [--limit=N]

Example:
    # Test: Create one listing
    python3 import_to_wordpress_api.py UT_seniorplace_data_20251030.csv --test-only

    # Import all new listings
    python3 import_to_wordpress_api.py UT_seniorplace_data_20251030.csv

    # Import first 10 listings
    python3 import_to_wordpress_api.py UT_seniorplace_data_20251030.csv --limit=10
"""

import requests
import csv
import argparse
import sys
from requests.auth import HTTPBasicAuth
from pathlib import Path
import os

# WordPress Configuration
WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
WP_USER = os.getenv("WP_USER") or os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")

# Care type mapping to taxonomy term IDs
# These may need to be looked up via WP-CLI: wp term list listing_type --format=json
CARE_TYPE_MAPPING = {
    'Assisted Living Community': 5,
    'Assisted Living Home': 162,
    'Independent Living': 6,
    'Memory Care': 3,
    'Nursing Home': 7,
    'Home Care': 488,
}

# State mapping to taxonomy term IDs
# These may need to be looked up via WP-CLI: wp term list location --format=json
STATE_MAPPING = {
    'AZ': 0,  # Need to lookup
    'CA': 0,  # Need to lookup
    'CO': 0,  # Need to lookup
    'ID': 0,  # Need to lookup
    'NM': 0,  # Need to lookup
    'UT': 953,  # Known from earlier test
}


def get_existing_urls():
    """Fetch all existing Senior Place URLs from WordPress"""
    print("📥 Fetching existing listings from WordPress...")
    wp_urls = set()
    page = 1
    
    while True:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/listing?per_page=100&page={page}",
            auth=HTTPBasicAuth(WP_USER, WP_PASS)
        )
        
        if response.status_code != 200:
            break
        
        listings = response.json()
        if not listings:
            break
        
        for listing in listings:
            url = listing.get('acf', {}).get('senior_place_url', '')
            if url:
                wp_urls.add(url)
        
        print(f"   Fetched page {page}: {len(listings)} listings (total URLs: {len(wp_urls)})")
        page += 1
        
        if len(listings) < 100:
            break
    
    print(f"✅ Found {len(wp_urls)} existing listings\n")
    return wp_urls


def create_listing(listing, wp_urls, test_mode=False):
    """Create a WordPress listing via REST API"""
    
    title = listing['title']
    url = listing['url']
    address = listing['address']
    city = listing['city']
    state = listing['state']
    zip_code = listing['zip']
    featured_image = listing['featured_image']
    care_types = listing['care_types']
    
    # Check if already exists
    if url in wp_urls:
        return {'status': 'skipped', 'reason': 'already_exists'}
    
    # Prepare post data
    post_data = {
        'title': title,
        'status': 'draft',  # Create as draft for review
        'acf': {
            'senior_place_url': url,
            'address': address,
        }
    }
    
    # Add optional fields if available
    if city:
        post_data['acf']['city'] = city
    if zip_code:
        post_data['acf']['zip'] = zip_code
    
    # Set state taxonomy (if we have the term ID)
    if state in STATE_MAPPING and STATE_MAPPING[state] > 0:
        post_data['acf']['state'] = STATE_MAPPING[state]
    
    # Set care type taxonomy (if we have the term IDs)
    if care_types:
        care_type_ids = []
        for care_type in care_types.split(','):
            care_type = care_type.strip()
            if care_type in CARE_TYPE_MAPPING:
                care_type_ids.append(CARE_TYPE_MAPPING[care_type])
        
        if care_type_ids:
            post_data['acf']['type'] = care_type_ids if len(care_type_ids) > 1 else care_type_ids[0]
    
    # Set featured image URL (note: would need to download and upload for full import)
    if featured_image:
        post_data['acf']['photos'] = featured_image
    
    if test_mode:
        print(f"  ✅ Would create: {title}")
        print(f"     URL: {url}")
        print(f"     Address: {address}")
        print(f"     State: {state}")
        print(f"     Care Types: {care_types}")
        return {'status': 'test', 'data': post_data}
    
    # POST to WordPress
    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/listing",
        json=post_data,
        auth=HTTPBasicAuth(WP_USER, WP_PASS)
    )
    
    if response.status_code == 201:
        result = response.json()
        return {
            'status': 'created',
            'id': result['id'],
            'title': result['title']['rendered'],
            'link': result['link']
        }
    else:
        return {
            'status': 'error',
            'code': response.status_code,
            'message': response.text[:200]
        }


def import_csv(csv_file, test_only=False, limit=None):
    """Import listings from CSV file"""
    
    if not Path(csv_file).exists():
        print(f"❌ Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    print("=" * 80)
    print("WordPress REST API Import")
    print("=" * 80)
    print(f"CSV File: {csv_file}")
    print(f"Test Mode: {test_only}")
    print(f"Limit: {limit or 'All'}")
    print("=" * 80)
    print()
    
    # Test connection
    print("🔍 Testing WordPress connection...")
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/listing?per_page=1",
        auth=HTTPBasicAuth(WP_USER, WP_PASS)
    )
    
    if response.status_code == 200:
        print(f"✅ Connected to WordPress: {WP_URL}\n")
    else:
        print(f"❌ Failed to connect: {response.status_code}")
        print(f"   {response.text[:200]}")
        sys.exit(1)
    
    # Get existing URLs (unless test only)
    if not test_only:
        wp_urls = get_existing_urls()
    else:
        wp_urls = set()
        print("⚠️  Test mode: Skipping duplicate check\n")
    
    # Read CSV
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        listings = list(reader)
    
    if limit:
        listings = listings[:int(limit)]
    
    total = len(listings)
    created = 0
    skipped = 0
    errors = 0
    
    print(f"📊 Processing {total} listings\n")
    
    for i, listing in enumerate(listings, 1):
        title = listing['title'][:60]
        print(f"[{i}/{total}] {title}")
        
        result = create_listing(listing, wp_urls, test_mode=test_only)
        
        if result['status'] == 'created':
            print(f"  ✅ Created: ID {result['id']} - {result['title']}")
            print(f"     Link: {result['link']}")
            created += 1
            wp_urls.add(listing['url'])  # Add to set to prevent duplicates
        elif result['status'] == 'skipped':
            print(f"  ⏭️  Skipped: {result['reason']}")
            skipped += 1
        elif result['status'] == 'test':
            created += 1
        elif result['status'] == 'error':
            print(f"  ❌ Error {result['code']}: {result['message']}")
            errors += 1
        
        # Progress update every 25 listings
        if i % 25 == 0:
            print()
            print(f"📈 Progress: {i}/{total} (Created: {created}, Skipped: {skipped}, Errors: {errors})")
            print()
    
    # Final summary
    print()
    print("=" * 80)
    print("✅ Import Complete!")
    print("=" * 80)
    print(f"Total processed: {total}")
    print(f"Created: {created}")
    print(f"Skipped (duplicates): {skipped}")
    print(f"Errors: {errors}")
    print("=" * 80)
    
    if test_only:
        print("\n⚠️  This was a TEST. No listings were created.")
        print("   Remove --test-only flag to perform actual import.")
    else:
        print(f"\n✅ Created {created} new listings as DRAFTS")
        print("   Review them in WordPress admin and publish when ready.")


def main():
    parser = argparse.ArgumentParser(description='Import Senior Place listings to WordPress via REST API')
    parser.add_argument('csv_file', help='CSV file to import')
    parser.add_argument('--test-only', action='store_true', help='Test mode - preview without creating')
    parser.add_argument('--limit', type=int, help='Limit number of listings to import')
    
    args = parser.parse_args()
    
    import_csv(args.csv_file, test_only=args.test_only, limit=args.limit)


if __name__ == '__main__':
    main()

