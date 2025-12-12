#!/usr/bin/env python3
"""
Move all listings from duplicate "CA" term (953) to "California" (490)
using concurrent requests for maximum speed.
"""

import requests
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# WordPress credentials
BASE_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
USERNAME = os.getenv("WP_USER") or os.getenv("WP_USERNAME") or "nicholas_editor"
PASSWORD = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")
if not PASSWORD:
    raise RuntimeError("Missing WP_PASS/WP_PASSWORD environment variable.")
AUTH = HTTPBasicAuth(USERNAME, PASSWORD)

# State IDs
CA_DUPLICATE_ID = 953  # The "CA" term that should NOT exist
CALIFORNIA_ID = 490    # The correct "California" term

# Max concurrent workers
MAX_WORKERS = 20


def get_listings_with_state(state_id):
    """Get all listings associated with a state term."""
    all_listings = []
    page = 1
    
    print(f"📥 Fetching listings with state ID {state_id}...")
    
    while True:
        response = requests.get(
            f"{BASE_URL}/wp-json/wp/v2/listing",
            params={
                'state': state_id,
                'per_page': 100,
                'page': page
            },
            auth=AUTH
        )
        
        if response.status_code != 200:
            break
            
        listings = response.json()
        if not listings:
            break
            
        all_listings.extend(listings)
        print(f"  Page {page}: {len(listings)} listings")
        
        if page >= int(response.headers.get('X-WP-TotalPages', 1)):
            break
            
        page += 1
    
    return all_listings


def update_single_listing(listing_id):
    """Update a single listing's state."""
    try:
        response = requests.post(
            f"{BASE_URL}/wp-json/wp/v2/listing/{listing_id}",
            json={'state': [CALIFORNIA_ID]},
            auth=AUTH,
            timeout=10
        )
        return (listing_id, response.status_code == 200)
    except Exception as e:
        return (listing_id, False)


def main():
    print("=" * 80)
    print("🔄 FIX DUPLICATE 'CA' STATE TERM (CONCURRENT)")
    print("=" * 80)
    print()
    print(f"Moving all listings from 'CA' (ID: {CA_DUPLICATE_ID})")
    print(f"                       to 'California' (ID: {CALIFORNIA_ID})")
    print(f"Using {MAX_WORKERS} concurrent workers for maximum speed")
    print()
    
    # Get all listings with the duplicate CA term
    ca_listings = get_listings_with_state(CA_DUPLICATE_ID)
    
    print(f"\n✅ Found {len(ca_listings)} listings with 'CA' state\n")
    
    if len(ca_listings) == 0:
        print("✅ No listings found with duplicate CA term!")
        return
    
    # Extract listing IDs
    listing_ids = [listing['id'] for listing in ca_listings]
    
    # Update all listings concurrently
    print(f"🚀 Starting concurrent updates with {MAX_WORKERS} workers...\n")
    
    updated = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_id = {executor.submit(update_single_listing, lid): lid for lid in listing_ids}
        
        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_id), 1):
            listing_id, success = future.result()
            
            if success:
                updated += 1
            else:
                failed += 1
            
            # Progress update every 100
            if i % 100 == 0:
                print(f"[{i}/{len(listing_ids)}] ✅ {updated} | ❌ {failed}")
    
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully moved: {updated} listings")
    print(f"❌ Failed: {failed} listings")
    print("=" * 80)


if __name__ == '__main__':
    main()

