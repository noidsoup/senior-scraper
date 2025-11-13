#!/usr/bin/env python3
"""
Fast sync of community types for ALL Senior Place listings.
Goes through every row, finds Senior Place URLs, scrapes live types, creates update CSV.
"""

import csv
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import re

# Canonical mapping from memory.md
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

def decode_current_wp_type(type_field):
    """Decode current WordPress type field to human readable"""
    if not type_field or type_field == '0':
        return 'Other/Unknown'
    
    # Extract all type IDs from serialized format
    type_ids = re.findall(r'i:\d+;i:(\d+);', type_field)
    type_names = []
    
    for type_id in type_ids:
        for name, id_val in CANONICAL_TO_ID.items():
            if str(id_val) == type_id:
                type_names.append(name)
                break
    
    return ', '.join(type_names) if type_names else 'Other/Unknown'

def extract_senior_place_url(row):
    """Extract Senior Place URL from various possible fields"""
    
    # Check website field first
    website = row.get('website', '') or row.get('_website', '')
    if website and 'seniorplace.com' in website:
        return website
    
    # Check senior_place_url field
    sp_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
    if sp_url and 'seniorplace.com' in sp_url:
        return sp_url
    
    return None

async def scrape_community_types_fast(context, url):
    """Fast scrape of community types only"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="domcontentloaded", timeout=15000)
        
        # Wait for community types section
        await page.wait_for_selector('div:has-text("Community Type(s)")', timeout=8000)
        
        # Fast extract of community types
        community_types = await page.evaluate("""
            () => {
                const communityTypes = [];
                
                // Find Community Type(s) section
                const communityTypeDiv = Array.from(document.querySelectorAll('div')).find(div => 
                    div.textContent && div.textContent.trim() === 'Community Type(s)' && 
                    div.classList.contains('font-bold')
                );
                
                if (!communityTypeDiv) {
                    return [];
                }
                
                // Get options container
                let optionsContainer = communityTypeDiv.parentElement.querySelector('.options');
                if (!optionsContainer) {
                    return [];
                }
                
                // Get all checked checkboxes
                const checkedInputs = optionsContainer.querySelectorAll('input[type="checkbox"]:checked');
                
                for (const input of checkedInputs) {
                    const labelDiv = input.parentElement.querySelector('div.ml-2');
                    if (labelDiv && labelDiv.textContent) {
                        const typeText = labelDiv.textContent.trim();
                        if (typeText) {
                            communityTypes.push(typeText);
                        }
                    }
                }
                
                return communityTypes;
            }
        """)
        
        await page.close()
        return community_types
            
    except Exception as e:
        if 'page' in locals():
            await page.close()
        return []

async def sync_all_community_types():
    """Sync community types for ALL Senior Place listings - FAST"""
    
    print("🚀 FAST SYNC ALL SENIOR PLACE COMMUNITY TYPES")
    print("=" * 55)
    print("Processing ALL rows to find and sync Senior Place community types")
    print()
    
    # Read ALL WordPress listings
    all_listings = []
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '').strip('"')
            sp_url = extract_senior_place_url(row)
            
            if sp_url:
                all_listings.append({
                    'wp_id': row.get('ID', ''),
                    'title': title,
                    'url': sp_url,
                    'current_wp_type': decode_current_wp_type(row.get('type', '')),
                    'current_type_field': row.get('type', ''),
                })
    
    print(f"📊 Found {len(all_listings)} Senior Place listings to process")
    print("🏃‍♂️ Running FAST mode - minimal delays")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Login to Senior Place
        print("🔐 Logging into Senior Place...")
        page = await context.new_page()
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', 'allison@aplaceforseniors.org')
        await page.fill('input[name="password"]', 'Hugomax2023!')
        await page.click('button[type="submit"]')
        await page.wait_for_selector('text=Communities', timeout=15000)
        await page.close()
        print("✅ Logged in")
        print()
        
        # Process ALL listings
        updates_needed = []
        processed = 0
        failed = 0
        
        for i, listing in enumerate(all_listings):
            processed += 1
            print(f"📋 {processed}/{len(all_listings)}: {listing['title']}")
            print(f"    URL: {listing['url']}")
            
            # Scrape community types
            community_types = await scrape_community_types_fast(context, listing['url'])
            
            if community_types:
                print(f"    🔍 Senior Place: {community_types}")
                
                # Map to canonical types (ALL types per memory rules)
                canonical_types = []
                for sp_type in community_types:
                    sp_lower = sp_type.lower()
                    if sp_lower in CANONICAL_MAPPING:
                        canonical = CANONICAL_MAPPING[sp_lower]
                        if canonical not in canonical_types:
                            canonical_types.append(canonical)
                
                if canonical_types:
                    # Generate correct WordPress fields
                    correct_type_field = generate_wp_type_field(canonical_types)
                    should_be_types = ', '.join(canonical_types)
                    
                    print(f"    🎯 Should be: {should_be_types}")
                    
                    # Check if update needed
                    if listing['current_type_field'] != correct_type_field:
                        print(f"    🚨 UPDATE NEEDED!")
                        print(f"      Current: {listing['current_wp_type']}")
                        print(f"      New: {should_be_types}")
                        
                        updates_needed.append({
                            'ID': listing['wp_id'],
                            'Title': listing['title'],
                            'type': correct_type_field,
                            'normalized_types': should_be_types,
                            'senior_place_types': ', '.join(community_types),
                            'current_wp_types': listing['current_wp_type'],
                            'url': listing['url']
                        })
                    else:
                        print(f"    ✅ Already correct")
                else:
                    print(f"    ⚠️  No canonical mapping")
            else:
                failed += 1
                print(f"    ❌ Failed to scrape")
            
            # Fast pace - minimal delay
            await asyncio.sleep(0.2)
            
            # Progress update every 50
            if processed % 50 == 0:
                print(f"\n🏃‍♂️ Progress: {processed}/{len(all_listings)} | Updates: {len(updates_needed)} | Failed: {failed}\n")
        
        await browser.close()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n🎯 FINAL RESULTS:")
        print(f"  Total processed: {processed}")
        print(f"  Updates needed: {len(updates_needed)}")
        print(f"  Failed scrapes: {failed}")
        print()
        
        if updates_needed:
            # Save updates CSV
            updates_file = f"organized_csvs/ALL_COMMUNITY_TYPE_UPDATES_{timestamp}.csv"
            with open(updates_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=updates_needed[0].keys())
                writer.writeheader()
                writer.writerows(updates_needed)
            
            print(f"💾 UPDATES CSV: {updates_file}")
            print(f"🚀 Import this file to WordPress using ID matching!")
            print()
            
            print(f"📋 SAMPLE UPDATES:")
            for i, update in enumerate(updates_needed[:5]):
                print(f"  {i+1}. {update['Title']}")
                print(f"     Senior Place: {update['senior_place_types']}")
                print(f"     Current: {update['current_wp_types']}")
                print(f"     New: {update['normalized_types']}")
                print()
            
            if len(updates_needed) > 5:
                print(f"   ... and {len(updates_needed) - 5} more updates")
        else:
            print(f"✅ ALL COMMUNITY TYPES ARE ALREADY CORRECT!")
            print(f"   No updates needed - your data is perfectly synced!")

def main():
    print("🚀 Starting FAST sync of ALL Senior Place community types...")
    print("This will process every single Senior Place listing")
    print()
    
    asyncio.run(sync_all_community_types())

if __name__ == "__main__":
    main()
