#!/usr/bin/env python3
"""
Move all listings from duplicate "CA" term (953) to "California" (490)
and then delete the CA term.
"""

import requests
from requests.auth import HTTPBasicAuth
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


def update_listing_state(listing_id, new_state_id):
    """Update a listing's state to the correct California term."""
    try:
        response = requests.post(
            f"{BASE_URL}/wp-json/wp/v2/listing/{listing_id}",
            json={'state': [new_state_id]},
            auth=AUTH,
            timeout=5
        )
        return response.status_code == 200
    except Exception:
        return False


def delete_state_term(term_id):
    """Delete the duplicate CA state term."""
    try:
        response = requests.delete(
            f"{BASE_URL}/wp-json/wp/v2/state/{term_id}",
            auth=AUTH,
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False


def main():
    print("=" * 80)
    print("🔄 FIX DUPLICATE 'CA' STATE TERM")
    print("=" * 80)
    print()
    print(f"Moving all listings from 'CA' (ID: {CA_DUPLICATE_ID})")
    print(f"                       to 'California' (ID: {CALIFORNIA_ID})")
    print()
    
    # Get all listings with the duplicate CA term
    ca_listings = get_listings_with_state(CA_DUPLICATE_ID)
    
    print(f"\n✅ Found {len(ca_listings)} listings with 'CA' state\n")
    
    if len(ca_listings) == 0:
        print("✅ No listings found with duplicate CA term!")
        return
    
    # Update each listing (fast mode - no delays)
    updated = 0
    failed = 0
    
    for i, listing in enumerate(ca_listings, 1):
        listing_id = listing['id']
        listing_title = listing.get('title', {}).get('rendered', 'Unknown')
        
        # Print progress every 100 listings
        if i % 100 == 0 or i == 1:
            print(f"[{i}/{len(ca_listings)}] Processing...")
        
        if update_listing_state(listing_id, CALIFORNIA_ID):
            updated += 1
        else:
            failed += 1
            print(f"  ❌ Failed: {listing_title[:50]}")
    
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully moved: {updated} listings")
    print(f"❌ Failed: {failed} listings")
    print()
    
    if failed == 0:
        print(f"🗑️  Attempting to delete duplicate 'CA' term (ID: {CA_DUPLICATE_ID})...")
        if delete_state_term(CA_DUPLICATE_ID):
            print("✅ Successfully deleted duplicate 'CA' term!")
        else:
            print("⚠️  Could not delete term (may need manual deletion)")
    
    print("=" * 80)


if __name__ == '__main__':
    main()

