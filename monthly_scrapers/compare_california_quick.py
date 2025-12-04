#!/usr/bin/env python3
"""
Quick compare: California scraped data vs WordPress
Find NEW California listings not in WordPress yet
"""

import json
import csv
import os
import requests

# Fetch WordPress listings
print("📥 Fetching WordPress listings...")
wp_urls = set()
page = 1
while True:
    response = requests.get(
        "https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2/listing",
        params={'per_page': 100, 'page': page},
        auth=(os.getenv('WP_USER', 'nicholas_editor'), os.getenv('WP_PASSWORD', '')),
        timeout=30
    )
    
    if response.status_code == 400:
        break
        
    listings = response.json()
    if not listings:
        break
    
    for listing in listings:
        # Get Senior Place URL
        if 'acf' in listing:
            sp_url = listing['acf'].get('senior_place_url') or listing['acf'].get('url')
            if sp_url and 'seniorplace.com' in sp_url:
                wp_urls.add(sp_url)
        
        if 'meta' in listing:
            sp_url = listing['meta'].get('_senior_place_url', [''])[0]
            if sp_url and 'seniorplace.com' in sp_url:
                wp_urls.add(sp_url)
    
    print(f"  Page {page}: {len(wp_urls)} total Senior Place URLs", end='\r')
    page += 1

print(f"\n✅ Found {len(wp_urls)} Senior Place URLs in WordPress")

# Load California scraped data
print("\n📂 Loading California scraped data...")
ca_listings = []
with open('california_expansion/california_seniorplace_data.jsonl', 'r') as f:
    for line in f:
        ca_listings.append(json.loads(line))

print(f"✅ Loaded {len(ca_listings)} California listings")

# Compare
print("\n🔍 Comparing...")
new_listings = []
for listing in ca_listings:
    url = listing.get('url', '')
    if url and url not in wp_urls:
        new_listings.append(listing)

print(f"\n🆕 Found {len(new_listings)} NEW California listings!")

# Save to CSV
if new_listings:
    output_file = 'NEW_CALIFORNIA_LISTINGS.csv'
    fieldnames = ['title', 'address', 'location-name', 'state', 'url', 'featured_image', 'type', 'price']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for listing in new_listings:
            writer.writerow({
                'title': listing.get('title', ''),
                'address': listing.get('address', ''),
                'location-name': listing.get('location-name', ''),
                'state': listing.get('state', 'CA'),
                'url': listing.get('url', ''),
                'featured_image': listing.get('featured_image', ''),
                'type': ', '.join(listing.get('type', [])),
                'price': listing.get('price', '')
            })
    
    print(f"💾 Saved to: {output_file}")
    print(f"\n📋 Sample new listings:")
    for listing in new_listings[:10]:
        print(f"  • {listing.get('title')} - {listing.get('location-name', '')}")
else:
    print("✅ All California listings are already in WordPress!")

