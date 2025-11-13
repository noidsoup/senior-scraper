#!/usr/bin/env python3
"""
Test updating a single location with description AND state meta/association.
"""

import requests
from requests.auth import HTTPBasicAuth
import json

# WordPress credentials
base_url = 'https://aplaceforseniorscms.kinsta.cloud'
username = 'nicholas_editor'
password = 'E3sK TONb VsB2 DEzh bdBe X6Ug'

auth = HTTPBasicAuth(username, password)

# Test city: Fortuna, CA
city_name = "Fortuna"
city_id = 512
state_name = "California"
state_id = 490
test_description = "Fortuna is a charming small city in Humboldt County offering seniors a peaceful lifestyle surrounded by towering redwood forests. The mild coastal climate and friendly community atmosphere make it ideal for retirees seeking natural beauty and small-town charm, with healthcare access through nearby Redwood Memorial Hospital."

print(f"🧪 Testing update for: {city_name}")
print(f"   Location ID: {city_id}")
print(f"   State: {state_name} (ID: {state_id})")
print()

# First, let's see what fields we can update
print("📋 Checking current location data...")
response = requests.get(
    f"{base_url}/wp-json/wp/v2/location/{city_id}",
    auth=auth
)
print(f"Current data: {json.dumps(response.json(), indent=2)}")
print()

# Attempt 1: Update with description and meta field for state
print("🔧 Attempt 1: Update with description + meta field for state...")
update_data = {
    'description': test_description,
    'meta': {
        'state': state_id,
        'state_id': state_id,
        '_state': state_id
    }
}

response = requests.put(
    f"{base_url}/wp-json/wp/v2/location/{city_id}",
    auth=auth,
    json=update_data
)

print(f"Status: {response.status_code}")
if response.status_code in [200, 201]:
    print("✅ Update successful!")
    result = response.json()
    print(f"Description updated: {result.get('description', '')[:100]}...")
    print(f"Meta fields: {result.get('meta', {})}")
else:
    print(f"❌ Failed: {response.text}")

print()
print("📋 Checking updated location data...")
response = requests.get(
    f"{base_url}/wp-json/wp/v2/location/{city_id}",
    auth=auth
)
updated = response.json()
print(f"Description: {updated.get('description', '')[:100]}...")
print(f"Meta: {updated.get('meta', {})}")
print(f"ACF: {updated.get('acf', {})}")

