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
import re
from requests.auth import HTTPBasicAuth
from pathlib import Path
import os
import tempfile
import mimetypes

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

# Load wp_config.env if it exists
def load_env_file():
    env_file = Path(__file__).parent / 'wp_config.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    # Handle inline comments
                    if '#' in line:
                        line = line[:line.index('#')].strip()
                    key, value = line.split('=', 1)
                    # Remove quotes
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value

load_env_file()

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

# State mapping to taxonomy term IDs (state taxonomy, not location)
STATE_MAPPING = {
    'AZ': 207,   # Arizona
    'CA': 490,   # California
    'CO': 211,   # Colorado
    'ID': 209,   # Idaho
    'NM': 215,   # New Mexico
    'UT': 224,   # Utah
}

# Cache for location (city) term IDs
LOCATION_CACHE = {}


def get_location_term_id(city):
    """Look up or create a location term ID for a city"""
    if not city or not city.strip():
        return None
    
    city = city.strip()
    
    # Check cache first
    if city in LOCATION_CACHE:
        return LOCATION_CACHE[city]
    
    # Search for existing term
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/location",
            params={'search': city, 'per_page': 10},
            auth=HTTPBasicAuth(WP_USER, WP_PASS)
        )
        
        if response.status_code == 200:
            terms = response.json()
            # Look for exact match (case insensitive)
            for term in terms:
                if term['name'].lower() == city.lower():
                    LOCATION_CACHE[city] = term['id']
                    return term['id']
        
        # Term not found - don't create new ones, just return None
        LOCATION_CACHE[city] = None
        return None
        
    except Exception as e:
        print(f"⚠️  Error looking up location for '{city}': {e}")
        return None


def clean_title(title):
    """Remove business suffixes like LLC, Inc, DBA from title"""
    if not title:
        return title
    
    # Patterns to remove (case insensitive)
    # Order matters - check longer patterns first
    patterns = [
        r'\s*,?\s*L\s*L\s*C\.?\s*$',      # L L C, LLC, L.L.C.
        r'\s*,?\s*LLC\.?\s*$',             # LLC
        r'\s*,?\s*L\.?L\.?C\.?\s*$',       # L.L.C, L.L.C.
        r'\s*,?\s*Inc\.?\s*$',             # Inc, Inc.
        r'\s*,?\s*Incorporated\s*$',       # Incorporated
        r'\s*,?\s*DBA\s+.*$',              # DBA and everything after
        r'\s*,?\s*D\.?B\.?A\.?\s+.*$',     # D.B.A. and everything after
        r'\s*,?\s*Corp\.?\s*$',            # Corp, Corp.
        r'\s*,?\s*Corporation\s*$',        # Corporation
        r'\s*,?\s*Co\.?\s*$',              # Co, Co.
        r'\s*,?\s*Company\s*$',            # Company
        r'\s*,?\s*Ltd\.?\s*$',             # Ltd, Ltd.
        r'\s*,?\s*Limited\s*$',            # Limited
        r'\s*,?\s*PLLC\.?\s*$',            # PLLC
        r'\s*,?\s*P\.?L\.?L\.?C\.?\s*$',   # P.L.L.C.
    ]
    
    cleaned = title.strip()
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up any trailing punctuation or whitespace
    cleaned = re.sub(r'[\s,;-]+$', '', cleaned)
    
    return cleaned.strip()


def upload_image_to_wordpress(image_url, title):
    """Download image from URL and upload to WordPress media library"""
    if not image_url or image_url.strip() == '':
        return None

    try:
        # Download the image
        print(f"Downloading image: {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        # Get image content and content type
        image_content = response.content
        content_type = response.headers.get('content-type', '')

        # If content type not provided or is generic, guess from URL
        if not content_type or content_type == 'application/octet-stream':
            guessed_type, _ = mimetypes.guess_type(image_url)
            if guessed_type:
                content_type = guessed_type

        # Accept common image types
        valid_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if content_type not in valid_image_types:
            # Try to determine from file extension
            ext = image_url.split('.')[-1].lower().split('?')[0]
            ext_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
            if ext in ext_map:
                content_type = ext_map[ext]
            else:
                print(f"⚠️  Invalid content type for image: {content_type}")
                return None

        # Get filename from URL
        filename = image_url.split('/')[-1]
        if '?' in filename:
            filename = filename.split('?')[0]
        if not filename:
            filename = f"{title.replace(' ', '_')}.jpg"

        # Upload to WordPress
        print(f"Uploading to WordPress: {filename}")

        files = {
            'file': (filename, image_content, content_type)
        }

        upload_response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            files=files,
            auth=HTTPBasicAuth(WP_USER, WP_PASS)
        )

        if upload_response.status_code == 201:
            media_data = upload_response.json()
            media_id = media_data['id']
            print(f"Image uploaded successfully, ID: {media_id}")
            return media_id
        else:
            print(f"Failed to upload image: {upload_response.status_code} - {upload_response.text}")
            return None

    except Exception as e:
        print(f"Error uploading image: {e}")
        return None


def get_existing_urls():
    """Fetch all existing Senior Place URLs from WordPress"""
    print("Fetching existing listings from WordPress...")
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
    
    print(f"Found {len(wp_urls)} existing listings\n")
    return wp_urls


def create_listing(listing, wp_urls, test_mode=False):
    """Create a WordPress listing via REST API"""
    
    title = clean_title(listing['title'])
    url = listing.get('url') or listing.get('senior_place_url', '')
    address = listing['address']
    city = listing['city']
    state = listing['state']
    zip_code = listing['zip']
    featured_image = listing.get('featured_image', '')
    care_types = listing.get('care_types') or listing.get('normalized_types', '')
    description = listing.get('description', '')
    
    # Check if already exists
    if url in wp_urls:
        return {'status': 'skipped', 'reason': 'already_exists'}
    
    # Prepare post data - CREATE WITHOUT ACF FIRST to avoid auto-publish
    post_data = {
        'title': title,
        'status': 'draft',  # Create as draft for review
        'content': description,
    }
    
    # ACF fields will be added separately after creation to avoid auto-publish
    
    if test_mode:
        print(f"  Would create: {title}")
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
        listing_id = result['id']
        actual_status = result.get('status', 'unknown')
        print(f"✅ Created listing ID {listing_id} with status: {actual_status}")

        # NOW ADD ACF FIELDS SEPARATELY to avoid auto-publish
        acf_data = {
            'acf': {
                'senior_place_url': url,
                'address': address,
            }
        }

        # Set location (city) taxonomy term
        if city:
            location_id = get_location_term_id(city)
            if location_id:
                acf_data['acf']['location'] = [location_id]
        
        # Set state taxonomy (if we have the term ID)
        if state in STATE_MAPPING and STATE_MAPPING[state] > 0:
            acf_data['acf']['state'] = STATE_MAPPING[state]

        # Set care type taxonomy (if we have the term IDs)
        if care_types:
            care_type_ids = []
            for care_type in care_types.split(','):
                care_type = care_type.strip()
                if care_type in CARE_TYPE_MAPPING:
                    care_type_ids.append(CARE_TYPE_MAPPING[care_type])

            if care_type_ids:
                acf_data['acf']['type'] = care_type_ids if len(care_type_ids) > 1 else care_type_ids[0]

        # Handle featured image
        if featured_image and featured_image.strip():
            print(f"🖼️  Processing featured image for: {title}")
            media_id = upload_image_to_wordpress(featured_image, title)
            if media_id:
                acf_data['featured_media'] = media_id

        if featured_image:
            acf_data['acf']['photos'] = featured_image

        # UPDATE THE LISTING WITH ACF FIELDS
        acf_response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/listing/{listing_id}",
            json=acf_data,
            auth=HTTPBasicAuth(WP_USER, WP_PASS)
        )

        if acf_response.status_code == 200:
            acf_result = acf_response.json()
            final_status = acf_result.get('status', 'unknown')
            print(f"✅ ACF fields added, final status: {final_status}")

            if final_status != 'draft':
                print(f"⚠️  ACF update changed status to {final_status} - forcing back to draft")

                # Force back to draft
                force_draft = requests.post(
                    f"{WP_URL}/wp-json/wp/v2/listing/{listing_id}",
                    json={'status': 'draft'},
                    auth=HTTPBasicAuth(WP_USER, WP_PASS)
                )

                if force_draft.status_code == 200:
                    print("✅ Successfully forced back to draft status")
                else:
                    print(f"❌ Failed to force draft: {force_draft.status_code}")
        else:
            print(f"❌ Failed to add ACF fields: {acf_response.status_code}")

        return {
            'status': 'created',
            'id': listing_id,
            'title': result['title']['rendered'],
            'link': result['link']
        }
    else:
        return {
            'status': 'error',
            'code': response.status_code,
            'message': response.text[:200]
        }


def import_csv(csv_file, test_only=False, limit=None, batch_size=25):
    """Import listings from CSV file"""
    
    if not Path(csv_file).exists():
        print(f"Error: CSV file not found: {csv_file}")
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
    print("Testing WordPress connection...")
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/listing?per_page=1",
        auth=HTTPBasicAuth(WP_USER, WP_PASS)
    )
    
    if response.status_code == 200:
        print(f"Connected to WordPress: {WP_URL}\n")
    else:
        print(f"Failed to connect: {response.status_code}")
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
            print(f"  Created: ID {result['id']} - {result['title']}")
            print(f"     Link: {result['link']}")
            created += 1
            wp_urls.add(listing.get('url') or listing.get('senior_place_url', ''))  # Add to set to prevent duplicates
        elif result['status'] == 'skipped':
            print(f"  ⏭️  Skipped: {result['reason']}")
            skipped += 1
        elif result['status'] == 'test':
            created += 1
        elif result['status'] == 'error':
            print(f"  Error {result['code']}: {result['message']}")
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
    parser.add_argument('--batch-size', type=int, default=25, help='Batch size for processing (web interface compatibility)')
    
    args = parser.parse_args()
    
    import_csv(args.csv_file, test_only=args.test_only, limit=args.limit, batch_size=args.batch_size)


if __name__ == '__main__':
    main()

