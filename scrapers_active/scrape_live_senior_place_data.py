#!/usr/bin/env python3
"""
Scrape LIVE Senior Place data to get the actual current care types.
No more relying on outdated exports!
"""

import csv
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import argparse

# Canonical mapping (from memory.md)
CANONICAL_MAPPING = {
    'assisted living facility': 'Assisted Living Community',
    'assisted living home': 'Assisted Living Home',
    'independent living': 'Independent Living',
    'memory care': 'Memory Care',
    'skilled nursing': 'Nursing Home',
    'continuing care retirement community': 'Assisted Living Community',
    'in-home care': 'Home Care',
    'home health': 'Home Care',
    'hospice': 'Home Care',
    'respite care': 'Assisted Living Community',
}

CANONICAL_TO_ID = {
    'Assisted Living Community': 5,
    'Assisted Living Home': 162,
    'Independent Living': 6,
    'Memory Care': 3,
    'Nursing Home': 7,
    'Home Care': 488,
}

def generate_wp_type_field(canonical_types):
    """Generate WordPress serialized type field for multiple types"""
    if not canonical_types:
        return 'a:1:{i:0;i:1;}'  # Uncategorized
    
    type_ids = [CANONICAL_TO_ID[t] for t in canonical_types if t in CANONICAL_TO_ID]
    
    if len(type_ids) == 1:
        return f'a:1:{{i:0;i:{type_ids[0]};}}'
    else:
        # Multiple types: a:N:{i:0;i:ID1;i:1;i:ID2;...}
        items = ''.join(f'i:{i};i:{type_ids[i]};' for i in range(len(type_ids)))
        return f'a:{len(type_ids)}:{{{items}}}'

async def scrape_care_types_from_url(context, url, title):
    """Scrape actual care types from a Senior Place URL"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page where care types are shown
        attributes_url = f"{url.rstrip('/')}/attributes"
        print(f"  🔍 Scraping: {attributes_url}")
        
        await page.goto(attributes_url, wait_until="networkidle", timeout=20000)
        
        # Wait for community type section
        await page.wait_for_selector('text=Community Type', timeout=10000)
        
        # Extract ALL checked care types
        care_types = await page.evaluate("""
            () => {
                const careTypes = [];
                const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                
                for (const label of labels) {
                    const textEl = label.querySelector("div.ml-2");
                    const input = label.querySelector('input[type="checkbox"]');
                    
                    if (!textEl || !input) continue;
                    if (!input.checked) continue; // Only checked boxes
                    
                    const name = (textEl.textContent || "").trim();
                    if (name) careTypes.push(name);
                }
                
                return careTypes;
            }
        """)
        
        await page.close()
        
        if care_types:
            print(f"  ✅ Found: {care_types}")
            return care_types
        else:
            print(f"  ⚠️  No care types found")
            return []
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        if 'page' in locals():
            await page.close()
        return []

def decode_current_wp_type(type_field):
    """Decode current WordPress type field"""
    if 'i:0;i:5;' in type_field:
        return 'Assisted Living Community'
    elif 'i:0;i:162;' in type_field:
        return 'Assisted Living Home'
    elif 'i:0;i:6;' in type_field:
        return 'Independent Living'
    elif 'i:0;i:3;' in type_field:
        return 'Memory Care'
    elif 'i:0;i:7;' in type_field:
        return 'Nursing Home'
    elif 'i:0;i:488;' in type_field:
        return 'Home Care'
    else:
        return 'Other/Unknown'

async def scrape_all_live_data(username, password, limit=None):
    """Scrape live care types for all Senior Place listings"""
    
    print("🔥 LIVE SENIOR PLACE SCRAPER")
    print("=" * 50)
    print("Getting ACTUAL current data from Senior Place website")
    print()
    
    # Get all Senior Place URLs from WordPress export
    all_listings = []
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '').strip('"')
            senior_place_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
            
            if senior_place_url and 'seniorplace.com' in senior_place_url:
                all_listings.append({
                    'wp_id': row.get('ID', ''),
                    'title': title,
                    'url': senior_place_url,
                    'current_wp_type': decode_current_wp_type(row.get('type', '')),
                    'current_type_field': row.get('type', ''),
                })
    
    if limit:
        all_listings = all_listings[:limit]
    
    print(f"📊 Found {len(all_listings)} Senior Place listings to scrape")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Login to Senior Place
        print("🔐 Logging into Senior Place...")
        page = await context.new_page()
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', username)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_selector('text=Communities', timeout=15000)
        await page.close()
        print("✅ Successfully logged in")
        print()
        
        # Scrape all listings
        results = []
        corrections_needed = []
        
        for i, listing in enumerate(all_listings):
            print(f"📋 {i+1}/{len(all_listings)}: {listing['title']}")
            
            # Scrape live care types
            live_care_types = await scrape_care_types_from_url(context, listing['url'], listing['title'])
            
            if live_care_types:
                # Map to canonical types (ALL types, no primary/secondary)
                canonical_types = []
                for sp_type in live_care_types:
                    sp_lower = sp_type.lower()
                    if sp_lower in CANONICAL_MAPPING:
                        canonical = CANONICAL_MAPPING[sp_lower]
                        if canonical not in canonical_types:
                            canonical_types.append(canonical)
                
                if canonical_types:
                    # Generate correct WordPress type field
                    correct_type_field = generate_wp_type_field(canonical_types)
                    
                    # Check if this differs from current WordPress data
                    if listing['current_type_field'] != correct_type_field:
                        print(f"  🚨 NEEDS CORRECTION!")
                        print(f"    Current WP: {listing['current_wp_type']}")
                        print(f"    Should be: {', '.join(canonical_types)}")
                        
                        corrections_needed.append({
                            'ID': listing['wp_id'],
                            'Title': listing['title'],
                            'type': correct_type_field,
                            'normalized_types': ', '.join(canonical_types),
                            'live_senior_place_types': ', '.join(live_care_types),
                            'current_wp_type': listing['current_wp_type'],
                            'correction_reason': f'Live SP shows: {", ".join(live_care_types)}'
                        })
                    else:
                        print(f"  ✅ Already correct: {', '.join(canonical_types)}")
                
                # Store all results
                results.append({
                    'wp_id': listing['wp_id'],
                    'title': listing['title'],
                    'url': listing['url'],
                    'live_care_types': live_care_types,
                    'canonical_types': canonical_types,
                    'current_wp_type': listing['current_wp_type']
                })
            else:
                print(f"  ❌ Failed to scrape")
            
            print()
            
            # Small delay to be nice to Senior Place
            await asyncio.sleep(0.5)
        
        await browser.close()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save all scraped data
        all_data_file = f"organized_csvs/LIVE_SENIOR_PLACE_DATA_{timestamp}.csv"
        if results:
            with open(all_data_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['wp_id', 'title', 'url', 'live_care_types', 'canonical_types', 'current_wp_type']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for result in results:
                    result['live_care_types'] = ', '.join(result['live_care_types'])
                    result['canonical_types'] = ', '.join(result['canonical_types'])
                    writer.writerow(result)
            
            print(f"💾 All live data saved: {all_data_file}")
        
        # Save corrections needed
        if corrections_needed:
            corrections_file = f"organized_csvs/LIVE_DATA_CORRECTIONS_{timestamp}.csv"
            with open(corrections_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=corrections_needed[0].keys())
                writer.writeheader()
                writer.writerows(corrections_needed)
            
            print(f"💾 Corrections needed: {corrections_file}")
            
            print(f"\n🎯 RESULTS:")
            print(f"  Total scraped: {len(results)}")
            print(f"  Corrections needed: {len(corrections_needed)}")
            
            print(f"\n📋 Sample corrections needed:")
            for corr in corrections_needed[:5]:
                print(f"  • {corr['Title']}")
                print(f"    Live SP: {corr['live_senior_place_types']}")
                print(f"    Should be: {corr['normalized_types']}")
                print()
            
            print(f"🚀 Import {corrections_file} to fix these!")
        else:
            print(f"\n✅ All {len(results)} listings are already correctly mapped!")

def main():
    parser = argparse.ArgumentParser(description="Scrape live Senior Place data")
    parser.add_argument('--username', default=os.getenv('SP_USERNAME', ''), help='Senior Place username (or set SP_USERNAME env)')
    parser.add_argument('--password', default=os.getenv('SP_PASSWORD', ''), help='Senior Place password (or set SP_PASSWORD env)')
    parser.add_argument('--limit', type=int, help='Limit for testing (default: all)')
    
    args = parser.parse_args()
    
    print("🔥 Starting LIVE Senior Place scraper...")
    print("This will get the ACTUAL current data from Senior Place")
    print()
    
    asyncio.run(scrape_all_live_data(args.username, args.password, args.limit))

if __name__ == "__main__":
    main()
