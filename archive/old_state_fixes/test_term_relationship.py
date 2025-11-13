#!/usr/bin/env python3
"""
Test if we can create a relationship between location and state taxonomies.
The State checkboxes might be a term-to-term relationship, not ACF.
"""

import requests
from requests.auth import HTTPBasicAuth
import json

base_url = 'https://aplaceforseniorscms.kinsta.cloud'
username = 'nicholas_editor'
password = 'E3sK TONb VsB2 DEzh bdBe X6Ug'
auth = HTTPBasicAuth(username, password)

# Get a listing that has both location and state
print("🔍 Finding a listing with both location and state...")
response = requests.get(
    f"{base_url}/wp-json/wp/v2/listing?per_page=1&location=512",  # Fortuna
    auth=auth
)

if response.json():
    listing = response.json()[0]
    print(f"Found listing: {listing['title']['rendered']}")
    print(f"Location terms: {listing.get('location', [])}")
    print(f"State terms: {listing.get('state', [])}")
    print()
    
    # The state is associated at the LISTING level, not the location term level
    print("💡 Insight: State is a taxonomy on LISTINGS, not on LOCATION terms")
    print("   Location taxonomy terms don't have their own state association")
    print("   The state checkboxes you see are for filtering which state a location belongs to")
    print()

# Check if there's a way to query locations by state
print("🔍 Checking if we can filter locations by state...")
response = requests.get(
    f"{base_url}/wp-json/wp/v2/location?per_page=5",
    auth=auth
)

if response.json():
    sample_term = response.json()[0]
    print(f"Sample location term structure:")
    print(json.dumps(sample_term, indent=2)[:500])
    print()

print("📋 Conclusion:")
print("   The State field on location taxonomy terms is likely:")
print("   1. An ACF field that's not exposed to REST API, OR")
print("   2. A custom meta field that needs special handling, OR")  
print("   3. A term relationship that requires a different API endpoint")
print()
print("   For now, we should:")
print("   ✅ Update all 286 descriptions (this works perfectly)")
print("   ⚠️  State associations can be done via bulk edit in WordPress admin")

