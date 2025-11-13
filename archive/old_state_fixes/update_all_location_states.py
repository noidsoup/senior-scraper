#!/usr/bin/env python3
"""
Update ALL location terms with correct state associations.
Queries WordPress listings to determine each city's actual state.
Also handles duplicate/typo terms like "Colorado Springsgs".
"""

import requests
from requests.auth import HTTPBasicAuth
import time
import sys

# WordPress credentials
BASE_URL = 'https://aplaceforseniorscms.kinsta.cloud'
USERNAME = 'nicholas_editor'
PASSWORD = 'E3sK TONb VsB2 DEzh bdBe X6Ug'
AUTH = HTTPBasicAuth(USERNAME, PASSWORD)

# State ID mapping (always use "California" 490, never "CA" 953)
STATE_MAP = {
    'Arizona': 207,
    'Arkansas': 483,
    'CA': 490,  # Map CA to California
    'California': 490,
    'Colorado': 211,
    'Connecticut': 468,
    'Idaho': 209,
    'New Mexico': 215,
    'Utah': 224,
    'Wyoming': 374
}

# Known duplicate/typo terms to DELETE after moving their listings
TERMS_TO_DELETE = {
    429: 'Colorado Springsgs',  # Typo, should be "Colorado Springs" (219)
}

# Mapping of typo term ID -> correct term ID
TYPO_CORRECTIONS = {
    429: 219,  # Colorado Springsgs -> Colorado Springs
}


def get_all_location_terms():
    """Fetch all location taxonomy terms from WordPress."""
    all_terms = []
    page = 1
    per_page = 100
    
    print("📥 Fetching all location terms from WordPress...")
    
    while True:
        response = requests.get(
            f"{BASE_URL}/wp-json/wp/v2/location",
            params={'page': page, 'per_page': per_page},
            auth=AUTH
        )
        
        if response.status_code != 200:
            break
            
        terms = response.json()
        if not terms:
            break
            
        all_terms.extend(terms)
        
        # Check if there are more pages
        total_pages = int(response.headers.get('X-WP-TotalPages', 1))
        print(f"  Page {page}/{total_pages} - {len(terms)} terms")
        
        if page >= total_pages:
            break
            
        page += 1
        time.sleep(0.5)
    
    print(f"✅ Fetched {len(all_terms)} total location terms\n")
    return all_terms


def get_city_state_from_listings(city_name, term_id):
    """
    Determine a city's state by querying listings associated with it.
    
    Args:
        city_name: Name of the city
        term_id: WordPress term ID for the city
        
    Returns:
        State name (e.g., "California", "Colorado") or None if not found
    """
    try:
        # Query listings that belong to this location
        response = requests.get(
            f"{BASE_URL}/wp-json/wp/v2/listing",
            params={'location': term_id, 'per_page': 5},
            auth=AUTH,
            timeout=10
        )
        
        if response.status_code != 200 or not response.json():
            return None
        
        listings = response.json()
        
        # Extract state IDs from listings
        state_ids = set()
        for listing in listings:
            if 'state' in listing and listing['state']:
                state_ids.update(listing['state'])
        
        if not state_ids:
            return None
        
        # Find most common state (should only be one)
        state_id = list(state_ids)[0]
        
        # Map state ID to state name
        for state_name, sid in STATE_MAP.items():
            if sid == state_id:
                return state_name if state_name != 'CA' else 'California'
        
        return None
        
    except Exception as e:
        print(f"    ⚠️  Error querying listings: {e}")
        return None


def update_location_state(term_id, city_name, state_name):
    """
    Update a location term's state association via ACF field.
    
    Args:
        term_id: WordPress term ID
        city_name: City name (for logging)
        state_name: State name (e.g., "California")
        
    Returns:
        True if successful, False otherwise
    """
    state_id = STATE_MAP.get(state_name)
    if not state_id:
        print(f"  ❌ Unknown state: {state_name}")
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/wp-json/wp/v2/location/{term_id}",
            json={'acf': {'field_685dbc92bad4d': [state_id]}},  # Use field KEY not field name
            auth=AUTH,
            timeout=10
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"  ❌ Failed to update {city_name} (ID: {term_id}): {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error updating {city_name}: {e}")
        return False


def move_listings_from_typo(typo_term_id, correct_term_id):
    """
    Move all listings from a typo term to the correct term.
    
    Args:
        typo_term_id: WordPress term ID of the typo
        correct_term_id: WordPress term ID of the correct term
        
    Returns:
        Number of listings moved
    """
    try:
        # Get all listings with the typo term
        response = requests.get(
            f"{BASE_URL}/wp-json/wp/v2/listing",
            params={'location': typo_term_id, 'per_page': 100},
            auth=AUTH,
            timeout=10
        )
        
        if response.status_code != 200:
            return 0
        
        listings = response.json()
        moved = 0
        
        for listing in listings:
            # Get current location IDs
            location_ids = listing.get('location', [])
            
            # Replace typo ID with correct ID
            if typo_term_id in location_ids:
                location_ids.remove(typo_term_id)
                if correct_term_id not in location_ids:
                    location_ids.append(correct_term_id)
                
                # Update listing
                update_response = requests.post(
                    f"{BASE_URL}/wp-json/wp/v2/listing/{listing['id']}",
                    json={'location': location_ids},
                    auth=AUTH,
                    timeout=10
                )
                
                if update_response.status_code == 200:
                    moved += 1
                    time.sleep(0.3)
        
        return moved
        
    except Exception as e:
        print(f"    ⚠️  Error moving listings: {e}")
        return 0


def delete_term(term_id, term_name):
    """
    Delete a taxonomy term.
    
    Args:
        term_id: WordPress term ID
        term_name: Term name (for logging)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.delete(
            f"{BASE_URL}/wp-json/wp/v2/location/{term_id}",
            params={'force': True},
            auth=AUTH,
            timeout=10
        )
        
        return response.status_code in [200, 204]
        
    except Exception as e:
        print(f"  ❌ Error deleting {term_name}: {e}")
        return False


def main():
    print("=" * 80)
    print("🚀 UPDATE ALL LOCATION STATES")
    print("=" * 80)
    print()
    
    # Step 1: Handle typo terms
    if TYPO_CORRECTIONS:
        print("🔧 STEP 1: Clean up typo/duplicate terms")
        print("-" * 80)
        
        for typo_id, correct_id in TYPO_CORRECTIONS.items():
            typo_name = TERMS_TO_DELETE[typo_id]
            print(f"\n🗑️  Fixing typo: {typo_name} (ID: {typo_id})")
            
            # Move listings
            moved = move_listings_from_typo(typo_id, correct_id)
            print(f"  📦 Moved {moved} listings to correct term (ID: {correct_id})")
            
            # Delete typo term
            if delete_term(typo_id, typo_name):
                print(f"  ✅ Deleted typo term: {typo_name}")
            else:
                print(f"  ⚠️  Could not delete {typo_name} - may need manual cleanup")
            
            time.sleep(1)
        
        print("\n✅ Typo cleanup complete\n")
    
    # Step 2: Get all location terms
    print("🔧 STEP 2: Update all location states")
    print("-" * 80)
    print()
    
    all_terms = get_all_location_terms()
    
    # Filter out deleted typo terms
    terms = [t for t in all_terms if t['id'] not in TERMS_TO_DELETE]
    
    print(f"🔄 Processing {len(terms)} location terms...\n")
    
    # Track statistics
    updated = 0
    skipped = 0
    failed = 0
    state_counts = {}
    
    for i, term in enumerate(terms, 1):
        term_id = term['id']
        city_name = term['name']
        
        print(f"[{i}/{len(terms)}] {city_name}...", end=' ', flush=True)
        
        # Determine state from listings
        state = get_city_state_from_listings(city_name, term_id)
        
        if not state:
            print("⚠️  No listings found (skipped)")
            skipped += 1
            continue
        
        # Update state association
        if update_location_state(term_id, city_name, state):
            print(f"✅ {state}")
            updated += 1
            state_counts[state] = state_counts.get(state, 0) + 1
        else:
            print(f"❌ Failed")
            failed += 1
        
        # Rate limiting - removed for speed
        # time.sleep(0.5)
    
    # Summary
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully updated: {updated} locations")
    print(f"⚠️  Skipped (no listings): {skipped} locations")
    print(f"❌ Failed: {failed} locations")
    print()
    print("State breakdown:")
    for state, count in sorted(state_counts.items()):
        print(f"  {state}: {count} locations")
    print("=" * 80)


if __name__ == '__main__':
    main()
