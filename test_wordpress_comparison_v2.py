#!/usr/bin/env python3
"""
TEST: Compare by Senior Place URL (much more accurate!)
"""

import csv
import requests
import os
from datetime import datetime

WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
WP_USERNAME = os.getenv("WP_USER") or os.getenv("WP_USERNAME") or "nicholas_editor"
WP_PASSWORD = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")

def fetch_wordpress_seniorplace_urls():
    """Fetch all Senior Place URLs from WordPress ACF fields"""
    print("📥 Fetching WordPress Senior Place URLs...")
    
    wp_urls = set()
    page = 1
    total_listings = 0
    
    while True:
        # Fetch LISTING posts (not location taxonomy!)
        url = f"{WP_URL}/wp-json/wp/v2/listing?per_page=100&page={page}"
        
        try:
            response = requests.get(
                url,
                auth=(WP_USERNAME, WP_PASSWORD),
                timeout=30
            )
            
            if response.status_code == 400:  # No more pages
                break
                
            response.raise_for_status()
            listings = response.json()
            
            if not listings:
                break
            
            for listing in listings:
                total_listings += 1
                # Get Senior Place URL from ACF
                acf = listing.get('acf', {})
                
                if isinstance(acf, dict):
                    sp_url = acf.get('senior_place_url', '') or acf.get('website', '')
                    
                    if sp_url and 'seniorplace.com' in sp_url:
                        wp_urls.add(sp_url.strip())
            
            print(f"   Page {page}: {len(listings)} listings, {len(wp_urls)} with Senior Place URLs so far")
            page += 1
            
        except Exception as e:
            print(f"   ⚠️ Error on page {page}: {e}")
            break
    
    print(f"   ✅ Total WordPress locations: {total_listings}")
    print(f"   ✅ With Senior Place URLs: {len(wp_urls)}\n")
    return wp_urls

def load_test_data():
    """Load test CSV"""
    print("📂 Loading test scraped data...")
    
    listings = []
    with open('TEST_100_LISTINGS.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            listings.append(row)
    
    print(f"   ✅ Loaded {len(listings)} test listings\n")
    return listings

def compare_by_url(scraped, wp_urls):
    """Compare by Senior Place URL"""
    print("🔍 Comparing by Senior Place URL...")
    
    new_listings = []
    existing = []
    
    for listing in scraped:
        url = listing.get('url', '').strip()
        
        if url not in wp_urls:
            new_listings.append(listing)
        else:
            existing.append(listing)
    
    print(f"   ✅ NEW (not in WordPress): {len(new_listings)}")
    print(f"   ♻️  Already in WordPress: {len(existing)}\n")
    
    return new_listings, existing

def main():
    print("="*70)
    print("WORDPRESS COMPARISON TEST V2 (URL-based)")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Fetch WordPress URLs
    wp_urls = fetch_wordpress_seniorplace_urls()
    
    # Load test data
    test_data = load_test_data()
    
    # Compare by URL
    new_listings, existing = compare_by_url(test_data, wp_urls)
    
    # Save new
    if new_listings:
        output_file = f"TEST_NEW_BY_URL_{datetime.now().strftime('%Y%m%d')}.csv"
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(new_listings[0].keys()))
            writer.writeheader()
            writer.writerows(new_listings)
        
        print(f"💾 Saved {len(new_listings)} NEW listings to: {output_file}\n")
    
    # Summary
    print("="*70)
    print("COMPARISON COMPLETE!")
    print("="*70)
    print(f"📊 WordPress Senior Place URLs: {len(wp_urls):,}")
    print(f"📊 Test scraped: {len(test_data)}")
    print(f"✨ NEW (not in WP): {len(new_listings)}")
    print(f"♻️  Already in WP: {len(existing)}")
    
    if new_listings:
        print(f"\n📋 Sample NEW listings (need to import):")
        for listing in new_listings[:10]:
            print(f"   - {listing['title']} ({listing['city']}, {listing['state']})")
    
    if existing:
        print(f"\n✓ Sample EXISTING listings (already on site):")
        for listing in existing[:5]:
            print(f"   ✓ {listing['title']} ({listing['city']}, {listing['state']})")
    
    print("\n✅ URL-BASED COMPARISON IS MORE ACCURATE!")
    print("="*70)

if __name__ == "__main__":
    main()

