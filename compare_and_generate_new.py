#!/usr/bin/env python3
"""
Compare scraped Senior Place data with WordPress
Generate CSVs with ONLY NEW listings (not already on site)
Run this AFTER scraping completes
"""

import csv
import json
import requests
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
import argparse

# WordPress credentials
WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
WP_USERNAME = os.getenv("WP_USER") or os.getenv("WP_USERNAME") or "nicholas_editor"
WP_PASSWORD = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")

def fetch_wordpress_listings() -> Dict[str, Dict]:
    """
    Fetch ALL existing WordPress listings
    Returns dict keyed by normalized title for fast lookup
    """
    print("📥 Fetching existing WordPress listings...")
    
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
            
            print(f"  Page {page}: {len(locations)} listings")
            page += 1
            
        except Exception as e:
            print(f"⚠️ Error fetching page {page}: {e}")
            break
    
    print(f"✅ Found {len(all_wp_listings)} existing WordPress listings\n")
    return all_wp_listings

def normalize_title(title: str) -> str:
    """
    Normalize title for comparison
    Remove special chars, lowercase, strip whitespace
    """
    import re
    normalized = title.lower().strip()
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def load_scraped_data(state_code: str) -> List[Dict]:
    """Load scraped data for a specific state"""
    
    # Look for file in current_scraped_data/
    date_str = datetime.now().strftime("%Y%m%d")
    csv_file = Path(f"current_scraped_data/{state_code}_seniorplace_data_{date_str}.csv")
    
    if not csv_file.exists():
        # Try without date
        csv_file = Path(f"current_scraped_data/{state_code}_seniorplace_data.csv")
    
    if not csv_file.exists():
        print(f"⚠️ No scraped data found for {state_code}")
        return []
    
    print(f"📂 Loading scraped data: {csv_file}")
    
    listings = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            listings.append(row)
    
    print(f"  Found {len(listings)} scraped {state_code} listings")
    return listings

def compare_and_find_new(scraped: List[Dict], wp_listings: Dict[str, Dict]) -> List[Dict]:
    """
    Compare scraped data with WordPress
    Return only NEW listings (not in WordPress)
    """
    new_listings = []
    
    for listing in scraped:
        title = listing.get('title', '').strip()
        normalized = normalize_title(title)
        
        if normalized not in wp_listings:
            new_listings.append(listing)
    
    return new_listings

def save_new_listings_csv(new_listings: List[Dict], state_code: str):
    """Save new listings to CSV for WordPress import"""
    
    if not new_listings:
        print(f"✅ No new {state_code} listings to import")
        return None
    
    output_file = f"NEW_{state_code}_LISTINGS_{datetime.now().strftime('%Y%m%d')}.csv"
    
    fieldnames = ['title', 'address', 'city', 'state', 'zip', 'url', 
                 'featured_image', 'care_types', 'care_types_raw']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_listings)
    
    print(f"✅ Saved {len(new_listings)} NEW {state_code} listings to: {output_file}\n")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Compare scraped data with WordPress")
    parser.add_argument('--states', nargs='+', default=['AZ', 'CA', 'CO', 'ID', 'NM', 'UT'],
                       help='State codes to process')
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔍 SENIOR PLACE NEW LISTINGS FINDER")
    print("=" * 70)
    print(f"States: {', '.join(args.states)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Fetch ALL WordPress listings once
    wp_listings = fetch_wordpress_listings()
    
    # Process each state
    results = {}
    total_new = 0
    
    for state_code in args.states:
        print(f"\n{'='*70}")
        print(f"Processing {state_code}")
        print('='*70)
        
        # Load scraped data
        scraped = load_scraped_data(state_code)
        
        if not scraped:
            continue
        
        # Compare and find new
        new_listings = compare_and_find_new(scraped, wp_listings)
        
        print(f"  📊 Scraped: {len(scraped)} listings")
        print(f"  ✨ NEW: {len(new_listings)} listings")
        
        # Save to CSV
        output_file = save_new_listings_csv(new_listings, state_code)
        
        results[state_code] = {
            'scraped': len(scraped),
            'new': len(new_listings),
            'file': output_file
        }
        
        total_new += len(new_listings)
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 SUMMARY")
    print("=" * 70)
    print(f"WordPress listings: {len(wp_listings)}")
    print(f"\nNew listings by state:")
    for state, data in results.items():
        if data['new'] > 0:
            print(f"  {state}: {data['new']} new (from {data['scraped']} scraped) → {data['file']}")
        else:
            print(f"  {state}: 0 new (all {data['scraped']} already in WordPress)")
    
    print(f"\n🎯 TOTAL NEW LISTINGS: {total_new}")
    print("\n✅ Ready to import to WordPress!")
    print("=" * 70)

if __name__ == "__main__":
    main()

