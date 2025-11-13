#!/usr/bin/env python3
"""
Test different methods to update state association for location taxonomy terms.
"""

import requests
from requests.auth import HTTPBasicAuth
import json

base_url = 'https://aplaceforseniorscms.kinsta.cloud'
username = 'nicholas_editor'
password = 'E3sK TONb VsB2 DEzh bdBe X6Ug'
auth = HTTPBasicAuth(username, password)

# Test with Muscoy (ID from earlier)
print("🔍 Finding Muscoy term ID...")
response = requests.get(
    f"{base_url}/wp-json/wp/v2/location?search=Muscoy",
    auth=auth
)
muscoy = response.json()[0] if response.json() else None

if not muscoy:
    print("❌ Muscoy not found")
    exit(1)

muscoy_id = muscoy['id']
print(f"✅ Found Muscoy (ID: {muscoy_id})")
print()

# Try different update methods
print("🧪 Test 1: Update with meta field...")
response = requests.post(
    f"{base_url}/wp-json/wp/v2/location/{muscoy_id}",
    auth=auth,
    json={
        'meta': {
            'state': 490,
            '_state': 490
        }
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json().get('meta', {})}")
print()

print("🧪 Test 2: Check if ACF REST API is enabled...")
response = requests.get(
    f"{base_url}/wp-json/acf/v3/location/{muscoy_id}",
    auth=auth
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"ACF data: {json.dumps(response.json(), indent=2)}")
else:
    print(f"ACF REST API not available or not enabled")
print()

print("🧪 Test 3: Try updating via ACF REST endpoint...")
if response.status_code == 200:
    response = requests.post(
        f"{base_url}/wp-json/acf/v3/location/{muscoy_id}",
        auth=auth,
        json={
            'fields': {
                'field_685dbc92bad4d': [490]
            }
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
else:
    print("Skipping - ACF REST API not available")
print()

print("📋 Final check - current state:")
response = requests.get(
    f"{base_url}/wp-json/wp/v2/location/{muscoy_id}",
    auth=auth
)
data = response.json()
print(f"Description: {data.get('description', '')[:80]}...")
print(f"Meta: {data.get('meta', {})}")
print(f"ACF: {data.get('acf', {})}")

