#!/usr/bin/env python3
"""
WordPress REST API Import Script - SAFE VERSION
Imports Senior Place listings to WordPress with safety features:
- Batch processing (small chunks)
- Checkpoint/resume capability
- Error recovery
- Rate limiting
- Detailed logging
- Rollback tracking

Usage:
    # Test with 5 listings first
    python3 import_to_wordpress_api_safe.py UT_seniorplace_data_20251030.csv --limit=5

    # Import in batches of 50
    python3 import_to_wordpress_api_safe.py UT_seniorplace_data_20251030.csv --batch-size=50

    # Resume from checkpoint
    python3 import_to_wordpress_api_safe.py UT_seniorplace_data_20251030.csv --resume
"""

import requests
import csv
import argparse
import sys
import json
import time
import re
import os
import mimetypes
from pathlib import Path
from datetime import datetime
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
 
# WordPress Configuration (loaded from environment)
#   Required: WP_USER (or WP_USERNAME) and WP_PASS (or WP_PASSWORD)
#   Optional: WP_URL, FRONTEND_BASE_URL
WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
WP_USER = os.getenv("WP_USER") or os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "https://communities.aplaceforseniors.org").rstrip("/")

def _require_wp_credentials():
    if not WP_USER or not WP_PASS:
        print("❌ Missing WordPress credentials. Please set environment variables:")
        print("   - WP_USER (or WP_USERNAME)")
        print("   - WP_PASS (or WP_PASSWORD)")
        print(f"Optional: WP_URL (default: {WP_URL})")
        print(f"Optional: FRONTEND_BASE_URL (default: {FRONTEND_BASE_URL})")
        sys.exit(1)

# Safety settings
DEFAULT_BATCH_SIZE = 50  # Process in small batches
RATE_LIMIT_DELAY = 2.0  # Seconds between requests (increased to reduce server load)
CHECKPOINT_INTERVAL = 25  # Save checkpoint every N listings
BATCH_PAUSE = 10  # Seconds to pause between batches

# Care type mapping to taxonomy term IDs
CARE_TYPE_MAPPING = {
    'Assisted Living Community': 5,
    'Assisted Living Home': 162,
    'Independent Living': 6,
    'Memory Care': 3,
    'Nursing Home': 7,
    'Home Care': 488,
}

# State abbreviation to full name mapping
STATE_NAMES = {
    'AZ': 'Arizona',
    'CA': 'California',
    'CO': 'Colorado',
    'ID': 'Idaho',
    'NM': 'New Mexico',
    'UT': 'Utah',
}

# Cache for term IDs (to avoid repeated lookups)
_term_cache = {'state': {}, 'type': {}, 'location': {}}
_media_cache: dict = {}

# Blocklist patterns for titles that should never be imported
BLOCKLIST_PATTERNS = [
    r"\bdo\s+not\s+refer\b",
    r"\bdo\s+not\s+use\b",
    r"\bnot\s+signing\b",
    r"\bsurgery\b",
    r"\bsurgical\b",
    r"\beye\s+surgery\b",
]


def is_blocklisted_title(title: str) -> bool:
    if not title:
        return False
    for pat in BLOCKLIST_PATTERNS:
        if re.search(pat, title, flags=re.IGNORECASE):
            return True
    return False


def normalize_title(title):
    """
    Normalize title to match WordPress format:
    1. Strip business suffixes (LLC, INC, DBA, etc.)
    2. Convert to Title Case
    """
    if not title:
        return title
    
    # Strip common business suffixes
    suffixes = [
        r'\s+LLC\.?$',
        r'\s+L\.L\.C\.?$',
        r'\s+INC\.?$',
        r'\s+INCORPORATED\.?$',
        r'\s+CORP\.?$',
        r'\s+CORPORATION\.?$',
        r'\s+CO\.?$',
        r'\s+LTD\.?$',
        r'\s+LIMITED\.?$',
        r'\s+LP\.?$',
        r'\s+LLP\.?$',
    ]
    
    cleaned = title.strip()
    
    # Strip DBA (Doing Business As) patterns FIRST - removes everything after DBA
    # Handle "LLC Dba Centennial", "DBA Business Name", etc.
    dba_patterns = [
        r'\s+D\.?B\.?A\.?\s+.*$',  # DBA, D.B.A., DBA. followed by business name
        r'\s+D/B/A\s+.*$',         # D/B/A followed by business name
        r'\s+DBA\s+.*$',           # DBA followed by business name
        r'\s+Dba\s+.*$',           # Dba followed by business name (capitalized)
        r'\s+Doing Business As\s+.*$',  # "Doing Business As XYZ" - remove entire phrase
    ]
    
    for pattern in dba_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Then strip common business suffixes
    for suffix in suffixes:
        cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)
    
    # Handle "(The)" pattern - move to beginning
    # Examples: "Aristocrat Assisted Living (The)" -> "The Aristocrat Assisted Living"
    the_pattern = r'\s*\([Tt]he\)\s*$'
    if re.search(the_pattern, cleaned):
        cleaned = re.sub(the_pattern, '', cleaned)
        cleaned = f"The {cleaned}"
    
    # Clean up trailing commas and extra whitespace
    cleaned = re.sub(r',?\s*$', '', cleaned).strip()
    
    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Convert to title case
    cleaned = cleaned.title()
    
    # Fix common issues with title case
    # "Of", "At", "The", "By", etc. should be lowercase unless at start
    words = cleaned.split()
    for i in range(1, len(words)):
        if words[i].lower() in ['of', 'the', 'at', 'by', 'in', 'on', 'for', 'and', 'or']:
            words[i] = words[i].lower()
    
    return ' '.join(words)


def load_checkpoint(csv_file):
    """Load checkpoint if exists"""
    checkpoint_file = f"{Path(csv_file).stem}.import_checkpoint.json"
    if Path(checkpoint_file).exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return None


def save_checkpoint(csv_file, created_ids, processed_count, error_log):
    """Save checkpoint"""
    checkpoint_file = f"{Path(csv_file).stem}.import_checkpoint.json"
    checkpoint = {
        'timestamp': datetime.now().isoformat(),
        'processed_count': processed_count,
        'created_ids': created_ids,
        'error_log': error_log[-10:]  # Keep last 10 errors
    }
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    print(f"💾 Checkpoint saved: {len(created_ids)} listings created")


def get_state_term_id(state_abbrev):
    """Get state taxonomy term ID"""
    if state_abbrev in _term_cache['state']:
        return _term_cache['state'][state_abbrev]
    
    state_name = STATE_NAMES.get(state_abbrev)
    if not state_name:
        return None
    
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/state?search={state_name}",
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            timeout=5
        )
        if response.status_code == 200:
            states = response.json()
            for state in states:
                if state_name.lower() in state.get('name', '').lower():
                    term_id = state['id']
                    _term_cache['state'][state_abbrev] = term_id
                    return term_id
    except:
        pass
    
    return None


def get_care_type_term_ids(care_types_str):
    """Get care type taxonomy term IDs"""
    if not care_types_str:
        return []
    
    term_ids = []
    for care_type in care_types_str.split(','):
        care_type = care_type.strip()
        if care_type in CARE_TYPE_MAPPING:
            term_ids.append(CARE_TYPE_MAPPING[care_type])
    
    return term_ids


def get_or_create_location_term(city_name: str):
    """Get or create the 'location' (city) taxonomy term ID"""
    if not city_name:
        return None
    cached = _term_cache['location'].get(city_name.lower())
    if cached:
        return cached
    try:
        # Try to find existing term
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/location?per_page=100&search={city_name}",
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            timeout=5
        )
        if resp.status_code == 200:
            for term in resp.json():
                if term.get('name', '').strip().lower() == city_name.lower():
                    _term_cache['location'][city_name.lower()] = term['id']
                    return term['id']
        # Create if not found
        create = requests.post(
            f"{WP_URL}/wp-json/wp/v2/location",
            json={'name': city_name},
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            timeout=10
        )
        if create.status_code == 201:
            term_id = create.json()['id']
            _term_cache['location'][city_name.lower()] = term_id
            return term_id
    except:
        return None
    return None

def check_url_exists(url):
    """Check if a specific URL already exists in WordPress (faster than loading all)"""
    try:
        # Search for listings with this exact URL
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/listing?per_page=100&search={url}",
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            timeout=5
        )
        if response.status_code == 200:
            listings = response.json()
            for listing in listings:
                if listing.get('acf', {}).get('senior_place_url') == url:
                    return True
    except:
        pass
    return False


def normalize_address(address):
    """Normalize address for comparison"""
    if not address:
        return None
    # Convert to uppercase, remove punctuation, normalize spaces
    normalized = address.upper().strip()
    normalized = normalized.replace(',', ' ').replace('.', ' ')
    normalized = ' '.join(normalized.split())  # Normalize multiple spaces
    return normalized

def get_existing_urls(limit_pages=None):
    """Fetch existing Senior Place URLs, Seniorly URLs, AND addresses from WordPress (published + drafts)"""
    print("📥 Fetching existing listings from WordPress...")
    wp_sp_urls = set()  # Senior Place URLs
    wp_seniorly_urls = set()  # Seniorly URLs (from website field)
    wp_addresses = set()  # Also track addresses for duplicate detection
    
    # Fetch BOTH published AND draft listings to prevent duplicates
    for status in ['publish', 'draft']:
        page = 1
        max_pages = limit_pages if limit_pages else 999999
        
        while page <= max_pages:
            try:
                response = requests.get(
                    f"{WP_URL}/wp-json/wp/v2/listing?status={status}&per_page=100&page={page}",
                    auth=HTTPBasicAuth(WP_USER, WP_PASS),
                    timeout=10
                )
                
                if response.status_code != 200:
                    break
                
                listings = response.json()
                if not listings:
                    break
                
                for listing in listings:
                    acf = listing.get('acf', {})
                    
                    # Senior Place URL
                    sp_url = acf.get('senior_place_url', '').strip()
                    if sp_url:
                        wp_sp_urls.add(sp_url)
                    
                    # Seniorly URL (from website field)
                    website = acf.get('website', '').strip()
                    if website and 'seniorly.com' in website.lower():
                        wp_seniorly_urls.add(website)
                    
                    # Also track addresses (many published listings don't have URLs)
                    address = acf.get('address', '')
                    normalized_addr = normalize_address(address)
                    if normalized_addr:
                        wp_addresses.add(normalized_addr)
                
                if page % 10 == 0:
                    print(f"   Fetched {page} pages ({status}): {len(wp_sp_urls)} SP URLs, {len(wp_seniorly_urls)} Seniorly URLs, {len(wp_addresses)} addresses")
                
                page += 1
                
                if len(listings) < 100:
                    break
                    
                time.sleep(0.2)  # Rate limit
                
            except Exception as e:
                print(f"   ⚠️  Error fetching {status} page {page}: {e}")
                break
    
    print(f"✅ Found {len(wp_sp_urls)} SP URLs, {len(wp_seniorly_urls)} Seniorly URLs, {len(wp_addresses)} addresses (published + drafts)\n")
    return wp_sp_urls, wp_seniorly_urls, wp_addresses


def _download_image_bytes(image_url: str):
    try:
        resp = requests.get(image_url, timeout=20)
        if resp.status_code == 200:
            return resp.content
    except Exception:
        return None
    return None


def _upload_media_to_wordpress(filename: str, data: bytes, mime_type: str, title: str):
    try:
        files = {
            'file': (filename, data, mime_type or 'application/octet-stream')
        }
        resp = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            files=files,
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            timeout=30
        )
        if resp.status_code in (200, 201):
            media = resp.json()
            media_id = media.get('id')
            if media_id:
                # Set title and alt text
                try:
                    requests.post(
                        f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
                        json={'title': title, 'alt_text': title},
                        auth=HTTPBasicAuth(WP_USER, WP_PASS),
                        timeout=10
                    )
                except Exception:
                    pass
                return media_id
    except Exception:
        return None
    return None


def ensure_media_from_url(image_url: str, title: str):
    """Download an external image and upload to WordPress media library.
    Returns a media attachment ID or None on failure. Caches per-run by URL.
    """
    if not image_url:
        return None
    cached = _media_cache.get(image_url)
    if cached is not None:
        return cached

    parsed = urlparse(image_url)
    filename = os.path.basename(parsed.path) or 'image.jpg'
    mime_type, _ = mimetypes.guess_type(filename)

    data = _download_image_bytes(image_url)
    if not data:
        _media_cache[image_url] = None
        return None

    media_id = _upload_media_to_wordpress(filename, data, mime_type or 'image/jpeg', title)
    _media_cache[image_url] = media_id
    return media_id


def create_listing_safe(listing, wp_sp_urls, wp_seniorly_urls, wp_addresses, retry_count=3):
    """Create a WordPress listing with retry logic"""
    
    sp_url = listing.get('url', '')  # Senior Place URL
    title = normalize_title(listing['title'])  # Normalize title
    url = sp_url
    
    # Check if already exists by Senior Place URL
    if sp_url and sp_url in wp_sp_urls:
        return {'status': 'skipped', 'reason': 'already_exists_sp_url'}
    
    # Check if already exists by Seniorly URL (if provided)
    seniorly_url = listing.get('seniorly_url', '') or listing.get('website', '')
    if seniorly_url and 'seniorly.com' in seniorly_url.lower():
        if seniorly_url in wp_seniorly_urls:
            return {'status': 'skipped', 'reason': 'already_exists_seniorly_url'}
    
    # Check if already exists by address (many published listings don't have URLs)
    address = listing.get('address', '')
    normalized_addr = normalize_address(address)
    if normalized_addr and normalized_addr in wp_addresses:
        return {'status': 'skipped', 'reason': 'already_exists_address'}
    
    # Skip blocklisted titles (safety net)
    if is_blocklisted_title(title):
        return {'status': 'skipped', 'reason': 'blocked_title'}

    # Prepare post data with all fields
    post_data = {
        'title': title,
        'status': 'draft',  # Always draft for safety
        'acf': {
            'senior_place_url': url,
            'address': listing['address'],
        }
    }
    
    # Add optional ACF fields
    # Note: WordPress doesn't have separate 'city' or 'zip' ACF fields
    # City is handled via 'location' taxonomy (set below)
    # Zip is embedded in the 'address' field
    # Featured image handling: upload to WordPress and set as featured_media
    if listing.get('featured_image'):
        media_id = ensure_media_from_url(listing['featured_image'], title)
        if media_id:
            post_data['featured_media'] = media_id
        # Store original URL in ACF 'photos' (field expects string)
        post_data['acf']['photos'] = listing['featured_image']
    
    # Set care type taxonomy
    care_type_ids = get_care_type_term_ids(listing.get('care_types', ''))
    if care_type_ids:
        post_data['acf']['type'] = care_type_ids if len(care_type_ids) > 1 else care_type_ids[0]
    
    # Set state taxonomy
    state_abbrev = listing.get('state', '').upper()
    state_term_id = get_state_term_id(state_abbrev)
    if state_term_id:
        post_data['state'] = [state_term_id]
    
    # Set location taxonomy (city)
    city_name = listing.get('city', '').strip()
    location_term_id = get_or_create_location_term(city_name)
    if location_term_id:
        post_data['location'] = [location_term_id]
    
    # Retry logic
    for attempt in range(retry_count):
        try:
            response = requests.post(
                f"{WP_URL}/wp-json/wp/v2/listing",
                json=post_data,
                auth=HTTPBasicAuth(WP_USER, WP_PASS),
                timeout=15
            )
            
            if response.status_code == 201:
                result = response.json()
                slug = result.get('slug', '')
                if not slug:
                    # Generate slug from title if missing
                    slug = result['title']['rendered'].lower()
                    slug = slug.replace('&#8211;', ' ').replace('&amp;', 'and').replace('&', 'and')
                    slug = ''.join(c if c.isalnum() or c == ' ' else ' ' for c in slug)
                    slug = '-'.join(slug.split())  # This handles multiple spaces properly
                
                # Clean up multiple consecutive dashes
                import re
                slug = re.sub(r'-+', '-', slug)  # Replace multiple dashes with single dash
                slug = slug.strip('-')  # Remove leading/trailing dashes
                
                frontend_url = f"{FRONTEND_BASE_URL}/listings/{slug}/"
                
                return {
                    'status': 'created',
                    'id': result['id'],
                    'title': result['title']['rendered'],
                    'link': result['link'],
                    'frontend_url': frontend_url
                }
            elif response.status_code == 400:
                # Bad request - don't retry
                return {
                    'status': 'error',
                    'code': response.status_code,
                    'message': response.text[:200]
                }
            else:
                # Server error - retry
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return {
                        'status': 'error',
                        'code': response.status_code,
                        'message': response.text[:200]
                    }
                    
        except requests.exceptions.Timeout:
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
                continue
            return {'status': 'error', 'code': 'timeout', 'message': 'Request timeout'}
        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
                continue
            return {'status': 'error', 'code': 'exception', 'message': str(e)}
    
    return {'status': 'error', 'code': 'unknown', 'message': 'Max retries exceeded'}


def import_csv_safe(csv_file, batch_size=DEFAULT_BATCH_SIZE, limit=None, resume=False):
    """Import listings safely with checkpointing"""
    
    if not Path(csv_file).exists():
        print(f"❌ Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    # Ensure credentials are present
    _require_wp_credentials()
    
    print("=" * 80)
    print("WordPress REST API Import - SAFE MODE")
    print("=" * 80)
    print(f"CSV File: {csv_file}")
    print(f"Batch Size: {batch_size}")
    print(f"Limit: {limit or 'All'}")
    print(f"Resume: {resume}")
    print("=" * 80)
    print()
    
    # Test connection
    print("🔍 Testing WordPress connection...")
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/listing?per_page=1",
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Connected to WordPress: {WP_URL}\n")
        else:
            print(f"❌ Failed to connect: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)
    
    # Load checkpoint if resuming
    checkpoint = None
    start_index = 0
    created_ids = []
    
    if resume:
        checkpoint = load_checkpoint(csv_file)
        if checkpoint:
            start_index = checkpoint['processed_count']
            created_ids = checkpoint.get('created_ids', [])
            print(f"📂 Resuming from checkpoint:")
            print(f"   Already processed: {start_index}")
            print(f"   Already created: {len(created_ids)}")
            print()
    
    # Get ALL existing URLs and addresses to prevent duplicates
    print("📥 Fetching ALL existing listings to build duplicate cache...")
    print("   (This prevents creating duplicates - may take 2-3 minutes)")
    wp_sp_urls, wp_seniorly_urls, wp_addresses = get_existing_urls(limit_pages=None)  # Fetch ALL pages
    print(f"✅ Duplicate cache built: {len(wp_sp_urls)} SP URLs, {len(wp_seniorly_urls)} Seniorly URLs, {len(wp_addresses)} addresses\n")
    
    # Read CSV
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_listings = list(reader)
    
    # Apply limit
    if limit:
        all_listings = all_listings[:int(limit)]
    
    total = len(all_listings)
    listings_to_process = all_listings[start_index:]
    
    print(f"📊 Processing {len(listings_to_process)} listings (starting at #{start_index + 1})\n")
    
    created = 0
    skipped = 0
    errors = 0
    error_log = []
    
    # Process in batches
    for batch_start in range(0, len(listings_to_process), batch_size):
        batch_end = min(batch_start + batch_size, len(listings_to_process))
        batch = listings_to_process[batch_start:batch_end]
        
        print(f"📦 Processing batch {batch_start // batch_size + 1}: listings {batch_start + start_index + 1}-{batch_end + start_index}")
        
        for i, listing in enumerate(batch):
            current_index = start_index + batch_start + i + 1
            title = listing['title'][:60]
            
            print(f"  [{current_index}/{total}] {title}")
            
            result = create_listing_safe(listing, wp_sp_urls, wp_seniorly_urls, wp_addresses)
            
            if result['status'] == 'created':
                frontend_url = result.get('frontend_url', 'N/A')
                print(f"    ✅ Created: ID {result['id']}")
                print(f"       🌐 {frontend_url}")
                created += 1
                created_ids.append(result['id'])
                # Prevent duplicates in same run
                sp_url = listing.get('url', '')
                if sp_url:
                    wp_sp_urls.add(sp_url)
                seniorly_url = listing.get('seniorly_url', '') or listing.get('website', '')
                if seniorly_url and 'seniorly.com' in seniorly_url.lower():
                    wp_seniorly_urls.add(seniorly_url)
                address = listing.get('address', '')
                normalized_addr = normalize_address(address)
                if normalized_addr:
                    wp_addresses.add(normalized_addr)
            elif result['status'] == 'skipped':
                print(f"    ⏭️  Skipped: {result['reason']}")
                skipped += 1
            elif result['status'] == 'error':
                print(f"    ❌ Error: {result.get('code', 'unknown')} - {result.get('message', '')[:100]}")
                errors += 1
                error_log.append({
                    'index': current_index,
                    'title': title,
                    'error': result
                })
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            
            # Save checkpoint periodically
            if current_index % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(csv_file, created_ids, current_index, error_log)
        
        # Batch summary
        print(f"\n  📊 Batch complete: Created {created}, Skipped {skipped}, Errors {errors}")
        print()
        
        # Save checkpoint after each batch
        save_checkpoint(csv_file, created_ids, start_index + batch_end, error_log)
        
        # Pause between batches
        if batch_end < len(listings_to_process):
            print(f"⏸️  Pausing {BATCH_PAUSE} seconds before next batch...\n")
            time.sleep(BATCH_PAUSE)
    
    # Final summary
    print()
    print("=" * 80)
    print("✅ Import Complete!")
    print("=" * 80)
    print(f"Total processed: {len(listings_to_process)}")
    print(f"Created: {created}")
    print(f"Skipped (duplicates): {skipped}")
    print(f"Errors: {errors}")
    print("=" * 80)
    
    if errors > 0:
        print(f"\n⚠️  {errors} errors occurred. Check error log:")
        for err in error_log[-5:]:  # Show last 5 errors
            print(f"   - {err['title']}: {err['error'].get('message', 'Unknown error')}")
    
    print(f"\n✅ Created {created} new listings as DRAFTS")
    print("   Review them in WordPress admin before publishing.")
    print(f"\n💾 Checkpoint saved. To resume: --resume")
    
    # Clean up checkpoint if everything succeeded
    if errors == 0:
        checkpoint_file = f"{Path(csv_file).stem}.import_checkpoint.json"
        if Path(checkpoint_file).exists():
            print(f"\n✅ All listings imported successfully!")
            print(f"   Checkpoint file can be deleted: {checkpoint_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Import Senior Place listings to WordPress (SAFE MODE)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 5 listings
  python3 import_to_wordpress_api_safe.py UT_seniorplace_data_20251030.csv --limit=5

  # Import in small batches
  python3 import_to_wordpress_api_safe.py UT_seniorplace_data_20251030.csv --batch-size=25

  # Resume interrupted import
  python3 import_to_wordpress_api_safe.py UT_seniorplace_data_20251030.csv --resume
        """
    )
    parser.add_argument('csv_file', help='CSV file to import')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                       help=f'Process in batches (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--limit', type=int, help='Limit number of listings to import')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    
    args = parser.parse_args()
    
    # Safety confirmation for large imports
    if not args.limit and not args.resume:
        print("⚠️  WARNING: You're about to import ALL listings from this CSV!")
        print(f"   File: {args.csv_file}")
        
        # Count listings
        with open(args.csv_file, 'r') as f:
            count = sum(1 for _ in csv.DictReader(f))
        
        print(f"   Total listings: {count}")
        print(f"   This will create ~{count} draft posts in WordPress")
        print()
        response = input("Type 'yes' to continue, or Ctrl+C to cancel: ")
        if response.lower() != 'yes':
            print("❌ Import cancelled.")
            sys.exit(0)
        print()
    
    import_csv_safe(args.csv_file, batch_size=args.batch_size, limit=args.limit, resume=args.resume)


if __name__ == '__main__':
    main()

