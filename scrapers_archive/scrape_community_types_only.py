#!/usr/bin/env python3
"""
Scrape ONLY the Community Types from Senior Place, not services or other attributes.
Focus on the "Community Type(s)" section specifically.
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

# Valid community types (not services)
VALID_COMMUNITY_TYPES = {
    'continuing care retirement community',
    'independent living',
    'assisted living facility',
    'assisted living home',
    'memory care',
    'skilled nursing',
    'in-home care',
    'home health',
    'hospice',
    'respite care'
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

async def scrape_community_types_only(context, url, title):
    """Scrape ONLY community types from Senior Place (not services)"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="networkidle", timeout=20000)
        
        # Wait for community type section
        await page.wait_for_selector('text=Community Type', timeout=10000)
        
        # Extract ONLY community types using proven method from memory
        community_types = await page.evaluate("""
            () => {
                const communityTypes = [];
                const validTypes = [
                    'continuing care retirement community',
                    'independent living', 
                    'assisted living facility',
                    'assisted living home',
                    'memory care',
                    'skilled nursing',
                    'in-home care',
                    'home health',
                    'hospice',
                    'respite care'
                ];
                
                // Use the proven selector logic from memory
                const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                for (const label of labels) {
                    const textEl = label.querySelector("div.ml-2");
                    const input = label.querySelector('input[type="checkbox"]');
                    
                    if (!textEl || !input) continue;
                    if (!input.checked) continue; // ONLY checked boxes
                    
                    const name = (textEl.textContent || "").trim();
                    const nameLower = name.toLowerCase();
                    
                    // Only include if it's a valid community type (not services)
                    if (validTypes.includes(nameLower)) {
                        communityTypes.push(name);
                    }
                }
                
                return communityTypes;
            }
        """)
        
        await page.close()
        
        # Filter to only valid community types (double-check)
        filtered_types = []
        for ct in community_types:
            ct_lower = ct.lower()
            if ct_lower in VALID_COMMUNITY_TYPES:
                filtered_types.append(ct)
        
        if filtered_types:
            print(f"  ✅ Community Types: {filtered_types}")
            return filtered_types
        else:
            print(f"  ⚠️  No valid community types found")
            if community_types:
                print(f"      (Found these but filtered out: {community_types})")
            return []
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        if 'page' in locals():
            await page.close()
        return []

def decode_current_wp_type(type_field):
    """Decode current WordPress type field"""
    if not type_field or type_field == '0':
        return 'Other/Unknown'
    
    # Handle multiple types
    if 'i:0;i:5;' in type_field and 'i:1;i:162;' in type_field:
        return 'Assisted Living Community, Assisted Living Home'
    elif 'i:0;i:5;' in type_field:
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

async def scrape_all_community_types(username, password, limit=None):
    """Scrape community types for all Senior Place listings"""
    
    print("🏘️  COMMUNITY TYPES ONLY SCRAPER")
    print("=" * 50)
    print("Getting ONLY community types (not services) from Senior Place")
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
        corrections_needed = []
        all_results = []
        
        for i, listing in enumerate(all_listings):
            print(f"📋 {i+1}/{len(all_listings)}: {listing['title']}")
            
            # Scrape community types only
            community_types = await scrape_community_types_only(context, listing['url'], listing['title'])
            
            if community_types:
                # Map to canonical types (ALL types, no primary/secondary)
                canonical_types = []
                for sp_type in community_types:
                    sp_lower = sp_type.lower()
                    if sp_lower in CANONICAL_MAPPING:
                        canonical = CANONICAL_MAPPING[sp_lower]
                        if canonical not in canonical_types:
                            canonical_types.append(canonical)
                
                if canonical_types:
                    # Generate correct WordPress type field
                    correct_type_field = generate_wp_type_field(canonical_types)
                    should_be_types = ', '.join(canonical_types)
                    
                    # Check if this differs from current WordPress data
                    if listing['current_type_field'] != correct_type_field:
                        print(f"  🚨 NEEDS CORRECTION!")
                        print(f"    Current WP: {listing['current_wp_type']}")
                        print(f"    Should be: {should_be_types}")
                        
                        corrections_needed.append({
                            'ID': listing['wp_id'],
                            'Title': listing['title'],
                            'type': correct_type_field,
                            'normalized_types': should_be_types,
                            'senior_place_community_types': ', '.join(community_types),
                            'current_wp_type': listing['current_wp_type'],
                            'correction_reason': f'SP Community Types: {", ".join(community_types)}'
                        })
                    else:
                        print(f"  ✅ Already correct: {should_be_types}")
                
                all_results.append({
                    'wp_id': listing['wp_id'],
                    'title': listing['title'],
                    'url': listing['url'],
                    'community_types': community_types,
                    'canonical_types': canonical_types,
                    'current_wp_type': listing['current_wp_type']
                })
            else:
                print(f"  ❌ No community types found")
            
            print()
            
            # Small delay to be nice to Senior Place
            await asyncio.sleep(0.5)
        
        await browser.close()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save corrections needed
        if corrections_needed:
            corrections_file = f"organized_csvs/COMMUNITY_TYPES_CORRECTIONS_{timestamp}.csv"
            with open(corrections_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=corrections_needed[0].keys())
                writer.writeheader()
                writer.writerows(corrections_needed)
            
            print(f"💾 Community type corrections: {corrections_file}")
            
            print(f"\n🎯 RESULTS:")
            print(f"  Total scraped: {len(all_results)}")
            print(f"  Corrections needed: {len(corrections_needed)}")
            
            print(f"\n📋 Sample corrections:")
            for corr in corrections_needed[:5]:
                print(f"  • {corr['Title']}")
                print(f"    SP Community Types: {corr['senior_place_community_types']}")
                print(f"    Should be: {corr['normalized_types']}")
                print()
            
            print(f"🚀 Import {corrections_file} to WordPress!")
        else:
            print(f"\n✅ All {len(all_results)} listings are correctly mapped!")
        
        # Save all scraped data for reference
        if all_results:
            all_data_file = f"organized_csvs/ALL_COMMUNITY_TYPES_DATA_{timestamp}.csv"
            with open(all_data_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['wp_id', 'title', 'community_types', 'canonical_types', 'current_wp_type']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for result in all_results:
                    # Only include fields that are in fieldnames
                    output_row = {
                        'wp_id': result['wp_id'],
                        'title': result['title'],
                        'community_types': ', '.join(result['community_types']) if result['community_types'] else '',
                        'canonical_types': ', '.join(result['canonical_types']) if result['canonical_types'] else '',
                        'current_wp_type': result['current_wp_type']
                    }
                    writer.writerow(output_row)
            
            print(f"💾 All data saved: {all_data_file}")

def main():
    parser = argparse.ArgumentParser(description="Scrape community types only from Senior Place")
    parser.add_argument('--username', default='allison@aplaceforseniors.org', help='Senior Place username')
    parser.add_argument('--password', default='Hugomax2023!', help='Senior Place password')
    parser.add_argument('--limit', type=int, help='Limit for testing (default: all)')
    
    args = parser.parse_args()
    
    print("🏘️  Starting Community Types Only scraper...")
    print("This will get ONLY community types following our mapping system")
    print()
    
    asyncio.run(scrape_all_community_types(args.username, args.password, args.limit))

if __name__ == "__main__":
    main()
