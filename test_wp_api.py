#!/usr/bin/env python3
"""
Test WordPress API access
"""

import requests
import os

# Load WordPress credentials
WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud")
WP_USER = os.getenv("WP_USER", "nicholas_editor")
WP_PASS = os.getenv("WP_PASS", "3oiO dmah Ao7w Y8M7 5RKF rVrk")

print(f"Testing WordPress API access to: {WP_URL}")
print(f"Using user: {WP_USER}")
print(f"Password length: {len(WP_PASS) if WP_PASS else 0}")

# Test basic API access
try:
    url = f"{WP_URL}/wp-json/wp/v2/listing"
    params = {'per_page': 1, '_fields': 'id,title,status'}

    print(f"\nTesting GET request to: {url}")
    response = requests.get(url, params=params, timeout=10)
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Response: {len(data)} items returned")
        if data:
            item = data[0]
            print(f"Sample item: ID={item['id']}, Status={item.get('status', 'unknown')}, Title={item['title']['rendered'][:50] if isinstance(item['title'], dict) else item['title'][:50]}")

        # Test with auth for drafts
        print("\nTesting authenticated request for drafts...")
        from requests.auth import HTTPBasicAuth
        auth_response = requests.get(url, params={'status': 'draft', 'per_page': 5}, auth=HTTPBasicAuth(WP_USER, WP_PASS), timeout=10)
        print(f"Auth request status: {auth_response.status_code}")
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            print(f"Auth response: {len(auth_data)} draft items")
        else:
            print(f"Auth response error: {auth_response.text[:200]}")

    else:
        print(f"Error: {response.status_code} - {response.text[:200]}")

except Exception as e:
    print(f"Exception: {e}")
