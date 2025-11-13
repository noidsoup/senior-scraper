#!/usr/bin/env python3
"""
Test updating a location with description AND ACF state field.
ACF field key: field_685dbc92bad4d
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
state_id = 490  # California
test_description = "Fortuna is a charming small city in Humboldt County offering seniors a peaceful lifestyle surrounded by towering redwood forests. The mild coastal climate and friendly community atmosphere make it ideal for retirees seeking natural beauty and small-town charm, with healthcare access through nearby Redwood Memorial Hospital."

print(f"🧪 Testing ACF state association for: {city_name}")
print(f"   Location ID: {city_id}")
print(f"   State: {state_name} (ID: {state_id})")
print()

# Update with description AND ACF state field
print("🔧 Updating with description + ACF state field...")
update_data = {
    'description': test_description,
    'acf': {
        'field_685dbc92bad4d': [state_id]  # ACF state field expects array of term IDs
    }
}

response = requests.post(
    f"{base_url}/wp-json/wp/v2/location/{city_id}",
    auth=auth,
    json=update_data
)

print(f"Status: {response.status_code}")
if response.status_code in [200, 201]:
    print("✅ Update successful!")
    result = response.json()
    print(f"Description: {result.get('description', '')[:80]}...")
    print(f"ACF fields: {result.get('acf', {})}")
else:
    print(f"❌ Failed: {response.text[:500]}")

print()
print("📋 Verifying in WordPress admin...")
print(f"Check: https://aplaceforseniorscms.kinsta.cloud/wp-admin/term.php?taxonomy=location&tag_ID={city_id}")
print()
print("✅ If successful, the California checkbox should now be checked!")

