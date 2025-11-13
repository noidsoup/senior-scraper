#!/usr/bin/env python3
"""
Verify state associations for ALL 946 location terms.
"""

import requests
from requests.auth import HTTPBasicAuth

# WordPress credentials
BASE_URL = 'https://aplaceforseniorscms.kinsta.cloud'
USERNAME = 'nicholas_editor'
PASSWORD = 'E3sK TONb VsB2 DEzh bdBe X6Ug'
AUTH = HTTPBasicAuth(USERNAME, PASSWORD)


def get_all_location_terms():
    """Fetch all location terms with ACF data."""
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


def main():
    print("=" * 80)
    print("🔍 VERIFY ALL LOCATION STATES")
    print("=" * 80)
    print()
    
    all_terms = get_all_location_terms()
    print(f"📊 Total locations: {len(all_terms)}\n")
    
    with_state = 0
    without_state = 0
    unknown_cities = []
    
    for term in all_terms:
        city_name = term['name']
        acf = term.get('acf', {})
        state = acf.get('State', [])
        
        if state and len(state) > 0:
            with_state += 1
        else:
            without_state += 1
            unknown_cities.append((term['id'], city_name, term['count']))
    
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Locations WITH state: {with_state}")
    print(f"❌ Locations WITHOUT state: {without_state}")
    print()
    
    if unknown_cities:
        print("Cities missing state association:")
        for term_id, city, listing_count in unknown_cities:
            print(f"  - {city} (ID: {term_id}, {listing_count} listings)")
    
    print("=" * 80)


if __name__ == '__main__':
    main()

