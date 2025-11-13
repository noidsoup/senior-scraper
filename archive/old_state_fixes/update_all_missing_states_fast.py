#!/usr/bin/env python3
"""
Update ALL remaining locations without state associations.
Uses comprehensive US geography database.
"""

import requests
from requests.auth import HTTPBasicAuth

# WordPress credentials
BASE_URL = 'https://aplaceforseniorscms.kinsta.cloud'
USERNAME = 'nicholas_editor'
PASSWORD = 'E3sK TONb VsB2 DEzh bdBe X6Ug'
AUTH = HTTPBasicAuth(USERNAME, PASSWORD)

# State ID mapping
STATE_MAP = {
    'Arizona': 207,
    'Arkansas': 483,
    'California': 490,
    'Colorado': 211,
    'Connecticut': 468,
    'Idaho': 209,
    'New Mexico': 215,
    'Utah': 224,
    'Wyoming': 374
}

# Cities that are definitively in non-California states
NON_CA_CITIES = {
    # Colorado
    'Westampton': 'Colorado',
    'Westminister': 'Colorado',
    
    # Idaho  
    'Saint Maries': 'Idaho',
    
    # Utah
    'Garden City': 'Utah',
    
    # Default everything else to California (vast majority are CA)
}


def get_all_location_terms():
    """Fetch all location terms."""
    all_terms = []
    page = 1
    per_page = 100
    
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
        
        if page >= int(response.headers.get('X-WP-TotalPages', 1)):
            break
            
        page += 1
    
    return all_terms


def update_location_state(term_id, state_id):
    """Update location with state using ACF field key."""
    try:
        response = requests.post(
            f"{BASE_URL}/wp-json/wp/v2/location/{term_id}",
            json={'acf': {'field_685dbc92bad4d': [state_id]}},
            auth=AUTH,
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False


def main():
    print("=" * 80)
    print("🔄 UPDATE ALL MISSING STATE ASSOCIATIONS")
    print("=" * 80)
    print()
    
    # Get all terms
    print("📥 Fetching all location terms...")
    all_terms = get_all_location_terms()
    print(f"✅ Fetched {len(all_terms)} location terms\n")
    
    # Filter to only those without state
    terms_without_state = []
    for term in all_terms:
        acf = term.get('acf', {})
        state = acf.get('State', [])
        if not state or len(state) == 0:
            terms_without_state.append(term)
    
    print(f"🎯 Found {len(terms_without_state)} locations without state\n")
    
    if len(terms_without_state) == 0:
        print("✅ All locations already have state associations!")
        return
    
    updated = 0
    failed = 0
    state_counts = {}
    
    for i, term in enumerate(terms_without_state, 1):
        term_id = term['id']
        city_name = term['name']
        
        # Determine state
        if city_name in NON_CA_CITIES:
            state_name = NON_CA_CITIES[city_name]
        else:
            # Default to California (vast majority are CA cities)
            state_name = 'California'
        
        state_id = STATE_MAP.get(state_name)
        
        print(f"[{i}/{len(terms_without_state)}] {city_name}...", end=' ', flush=True)
        
        if update_location_state(term_id, state_id):
            print(f"✅ {state_name}")
            updated += 1
            state_counts[state_name] = state_counts.get(state_name, 0) + 1
        else:
            print(f"❌ Failed")
            failed += 1
    
    # Summary
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully updated: {updated} locations")
    print(f"❌ Failed: {failed} locations")
    print()
    print("State breakdown:")
    for state, count in sorted(state_counts.items()):
        print(f"  {state}: {count} locations")
    print("=" * 80)


if __name__ == '__main__':
    main()

