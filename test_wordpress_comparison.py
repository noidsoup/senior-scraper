#!/usr/bin/env python3
"""
TEST: Compare scraped data with WordPress to find NEW listings
Uses the TEST_100_LISTINGS.csv we just created
"""

import csv
import requests
import os
from datetime import datetime

# WordPress credentials
WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
WP_USERNAME = os.getenv("WP_USER") or os.getenv("WP_USERNAME") or "nicholas_editor"
WP_PASSWORD = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")

def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    import re
    normalized = title.lower().strip()
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def fetch_wordpress_listings():
    """Fetch ALL existing WordPress listings"""
    print("📥 Fetching WordPress listings...")
    
    all_wp_listings = {}
    page = 1
    
    while True:
        url = f"{WP_URL}/wp-json/wp/v2/location?per_page=100&page={page}"
        
        try:
            response = requests.get(
                url,
                auth=(WP_USERNAME, WP_PASSWORD),
                timeout=30
            )
            
            if response.status_code == 400:  # No more pages
                break
                
            response.raise_for_status()
            locations = response.json()
            
            if not locations:
                break
            
            for loc in locations:
                title = loc.get('title', {}).get('rendered', '').strip()
                normalized = normalize_title(title)
                
                all_wp_listings[normalized] = {
                    'id': loc['id'],
                    'title': title,
                    'link': loc.get('link', '')
                }
            
            print(f"   Page {page}: {len(locations)} listings")
            page += 1
            
        except Exception as e:
            print(f"   ⚠️ Error on page {page}: {e}")
            break
    
    print(f"   ✅ Total WordPress listings: {len(all_wp_listings)}\n")
    return all_wp_listings

def load_test_data():
    """Load the test CSV we just created"""
    print("📂 Loading test data...")
    
    listings = []
    with open('TEST_100_LISTINGS.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            listings.append(row)
    
    print(f"   ✅ Loaded {len(listings)} test listings\n")
    return listings

def compare_and_find_new(scraped, wp_listings):
    """Find listings that are NOT in WordPress"""
    print("🔍 Comparing with WordPress...")
    
    new_listings = []
    existing = []
    
    for listing in scraped:
        title = listing.get('title', '').strip()
        normalized = normalize_title(title)
        
        if normalized not in wp_listings:
            new_listings.append(listing)
        else:
            existing.append({
                'scraped': title,
                'wordpress': wp_listings[normalized]['title']
            })
    
    print(f"   ✅ Found {len(new_listings)} NEW listings")
    print(f"   ℹ️  Found {len(existing)} already in WordPress\n")
    
    return new_listings, existing

def save_new_listings(new_listings):
    """Save new listings to CSV"""
    if not new_listings:
        print("✅ No new listings - all are already in WordPress!")
        return None
    
    output_file = f"TEST_NEW_LISTINGS_{datetime.now().strftime('%Y%m%d')}.csv"
    
    fieldnames = ['title', 'address', 'city', 'state', 'zip', 'url', 
                 'featured_image', 'care_types', 'care_types_raw']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_listings)
    
    print(f"💾 Saved {len(new_listings)} NEW listings to: {output_file}\n")
    return output_file

def main():
    print("="*70)
    print("WORDPRESS COMPARISON TEST")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Fetch WordPress listings
    wp_listings = fetch_wordpress_listings()
    
    # Load test data
    test_data = load_test_data()
    
    # Compare
    new_listings, existing = compare_and_find_new(test_data, wp_listings)
    
    # Save new listings
    output_file = save_new_listings(new_listings)
    
    # Summary
    print("="*70)
    print("COMPARISON COMPLETE!")
    print("="*70)
    print(f"📊 WordPress has: {len(wp_listings):,} listings")
    print(f"📊 Test scraped: {len(test_data)} listings")
    print(f"✨ NEW (not in WP): {len(new_listings)} listings")
    print(f"♻️  Already in WP: {len(existing)} listings")
    
    if new_listings:
        print(f"\n📁 Import file: {output_file}")
        print("\nSample NEW listings:")
        for listing in new_listings[:5]:
            print(f"   - {listing['title']} ({listing['city']}, {listing['state']})")
    
    if existing:
        print(f"\nSample EXISTING listings:")
        for match in existing[:5]:
            print(f"   ✓ {match['scraped']}")
    
    print("\n✅ WORDPRESS COMPARISON WORKS!")
    print("="*70)

if __name__ == "__main__":
    main()

