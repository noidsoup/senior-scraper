#!/usr/bin/env python3
"""
Fix the state assignments in the CSV by looking up listings for each city.
"""

import requests
from requests.auth import HTTPBasicAuth
import csv
import time

base_url = 'https://aplaceforseniorscms.kinsta.cloud'
username = 'nicholas_editor'
password = 'E3sK TONb VsB2 DEzh bdBe X6Ug'
auth = HTTPBasicAuth(username, password)

# State ID to name mapping
state_names = {
    207: 'Arizona',
    483: 'Arkansas',
    490: 'California',
    211: 'Colorado',
    468: 'Connecticut',
    209: 'Idaho',
    215: 'New Mexico',
    224: 'Utah',
    374: 'Wyoming'
}

print("🔍 Finding correct state for each city...")
print()

# Read the generated CSV
cities_data = []
with open('missing_city_descriptions_generated.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cities_data.append(row)

# For each city, find its correct state from listings
fixed_data = []
for i, row in enumerate(cities_data, 1):
    city = row['city']
    description = row['description']
    
    print(f"[{i}/{len(cities_data)}] {city}...", end=' ', flush=True)
    
    # Get location term
    response = requests.get(
        f"{base_url}/wp-json/wp/v2/location?search={city}&per_page=1",
        auth=auth
    )
    
    if response.json():
        term_id = response.json()[0]['id']
        
        # Get listings for this location
        response2 = requests.get(
            f"{base_url}/wp-json/wp/v2/listing?location={term_id}&per_page=1",
            auth=auth
        )
        
        if response2.json():
            listing = response2.json()[0]
            state_ids = listing.get('state', [])
            
            if state_ids:
                state_id = state_ids[0]
                state_name = state_names.get(state_id, 'California')
                fixed_data.append({
                    'city': city,
                    'state': state_name,
                    'description': description
                })
                print(f"✅ {state_name}")
            else:
                # No state on listing, default to California
                fixed_data.append({
                    'city': city,
                    'state': 'California',
                    'description': description
                })
                print(f"⚠️  No state (defaulting to California)")
        else:
            # No listings, default to California
            fixed_data.append({
                'city': city,
                'state': 'California',
                'description': description
            })
            print(f"⚠️  No listings (defaulting to California)")
    else:
        # Term not found, default to California
        fixed_data.append({
            'city': city,
            'state': 'California',
            'description': description
        })
        print(f"⚠️  Term not found (defaulting to California)")
    
    time.sleep(0.2)  # Small delay

# Write fixed CSV
with open('missing_city_descriptions_FIXED.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['city', 'state', 'description'])
    writer.writeheader()
    writer.writerows(fixed_data)

print()
print("=" * 80)
print(f"✅ Fixed {len(fixed_data)} cities")
print(f"📄 Output: missing_city_descriptions_FIXED.csv")
print()

# Show state breakdown
state_counts = {}
for row in fixed_data:
    state = row['state']
    state_counts[state] = state_counts.get(state, 0) + 1

print("State breakdown:")
for state, count in sorted(state_counts.items()):
    print(f"  {state}: {count} cities")

