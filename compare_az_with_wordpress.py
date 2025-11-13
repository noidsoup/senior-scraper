#!/usr/bin/env python3
"""
Compare Arizona scraped data with WordPress to find NEW listings
"""

import csv
import requests
import os
from datetime import datetime

WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
WP_USERNAME = os.getenv("WP_USER") or os.getenv("WP_USERNAME") or "nicholas_editor"
WP_PASSWORD = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")

def fetch_wordpress_seniorplace_urls():
    """Fetch all Senior Place URLs from WordPress"""
    print("📥 Fetching WordPress Senior Place URLs...")
    
    wp_urls = set()
    page = 1
    total_listings = 0
    
    while True:
        url = f"{WP_URL}/wp-json/wp/v2/listing?per_page=100&page={page}"
        
        try:
            response = requests.get(url, auth=(WP_USERNAME, WP_PASSWORD), timeout=30)
            
            if response.status_code == 400:
                break
                
            response.raise_for_status()
            listings = response.json()
            
            if not listings:
                break
            
            for listing in listings:
                total_listings += 1
                acf = listing.get('acf', {})
                
                if isinstance(acf, dict):
                    sp_url = acf.get('senior_place_url', '') or acf.get('website', '')
                    
                    if sp_url and 'seniorplace.com' in sp_url:
                        wp_urls.add(sp_url.strip())
            
            print(f"   Page {page}: {len(listings)} listings, {len(wp_urls)} with Senior Place URLs")
            page += 1
            
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            break
    
    print(f"   ✅ Total WordPress locations: {total_listings}")
    print(f"   ✅ With Senior Place URLs: {len(wp_urls)}\n")
    return wp_urls

def load_arizona_data():
    """Load Arizona scraped data"""
    print("📂 Loading Arizona scraped data...")
    
    listings = []
    with open('AZ_seniorplace_data_20251029.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            listings.append(row)
    
    print(f"   ✅ Loaded {len(listings)} AZ listings\n")
    return listings

def compare_and_find_new(scraped, wp_urls):
    """Find listings NOT in WordPress"""
    print("🔍 Comparing Arizona with WordPress...")
    
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

def save_new_listings(new_listings):
    """Save new listings to CSV"""
    if not new_listings:
        print("✅ No new Arizona listings - all are already in WordPress!")
        return None
    
    output_file = f"NEW_AZ_LISTINGS_{datetime.now().strftime('%Y%m%d')}.csv"
    
    fieldnames = ['title', 'address', 'city', 'state', 'zip', 'url', 
                 'featured_image', 'care_types', 'care_types_raw']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_listings)
    
    print(f"💾 Saved {len(new_listings)} NEW AZ listings to: {output_file}\n")
    return output_file

def main():
    print("="*70)
    print("ARIZONA vs WORDPRESS COMPARISON")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")
    
    # Fetch WordPress URLs
    wp_urls = fetch_wordpress_seniorplace_urls()
    
    # Load Arizona data
    az_data = load_arizona_data()
    
    # Compare
    new_listings, existing = compare_and_find_new(az_data, wp_urls)
    
    # Save new listings
    output_file = save_new_listings(new_listings)
    
    # Summary
    print("="*70)
    print("COMPARISON COMPLETE!")
    print("="*70)
    print(f"📊 WordPress has: {len(wp_urls):,} Senior Place listings")
    print(f"📊 Arizona scraped: {len(az_data):,} listings")
    print(f"✨ NEW (not in WP): {len(new_listings):,} listings")
    print(f"♻️  Already in WP: {len(existing):,} listings")
    
    if new_listings:
        print(f"\n📁 Import file ready: {output_file}")
        print(f"\n📋 Sample NEW Arizona listings:")
        for listing in new_listings[:10]:
            care = listing['care_types'] or 'No care types'
            print(f"   • {listing['title']}")
            print(f"     {listing['city']}, AZ - {care}")
    
    if existing:
        print(f"\n✓ Sample EXISTING listings (already on site):")
        for listing in existing[:5]:
            print(f"   ✓ {listing['title']} ({listing['city']}, AZ)")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()

