#!/usr/bin/env python3
"""
Comprehensive sync of ALL Senior Place community types.
Scrapes live data and corrects WordPress listings that don't match.
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

ID_TO_CANONICAL = {v: k for k, v in CANONICAL_TO_ID.items()}

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
        return []
    
    # Extract all type IDs from serialized format
    type_ids = re.findall(r'i:\d+;i:(\d+);', type_field)
    type_names = []
    
    for type_id in type_ids:
        type_id_int = int(type_id)
        if type_id_int in ID_TO_CANONICAL:
            type_names.append(ID_TO_CANONICAL[type_id_int])
    
    return type_names

def extract_senior_place_url(row):
    """Extract Senior Place URL from website or senior_place_url fields"""
    
    # Check website field first
    website = row.get('website', '') or row.get('_website', '')
    if website and 'seniorplace.com' in website:
        return website
    
    # Check senior_place_url field
    sp_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
    if sp_url and 'seniorplace.com' in sp_url:
        return sp_url
    
    return None

async def scrape_community_types_from_seniorplace(context, url):
    """Scrape live community types from Senior Place attributes page"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="domcontentloaded", timeout=15000)
        
        # Wait for community types section
        await page.wait_for_selector('div:has-text("Community Type(s)")', timeout=10000)
        
        # Extract community types using exact HTML structure
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

async def sync_all_seniorplace_types():
    """Sync ALL Senior Place community types with live data"""
    
    print("🔄 COMPREHENSIVE SENIOR PLACE TYPE SYNC")
    print("=" * 50)
    print("Syncing ALL WordPress listings with live Senior Place data")
    print("Checking both 'website' and 'senior_place_url' fields")
    print()
    
    # Read ALL WordPress listings
    all_listings = []
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '').strip('"')
            sp_url = extract_senior_place_url(row)
            
            if sp_url:
                current_wp_types = decode_current_wp_type(row.get('type', ''))
                
                all_listings.append({
                    'wp_id': row.get('ID', ''),
                    'title': title,
                    'url': sp_url,
                    'current_wp_types': current_wp_types,
                    'current_type_field': row.get('type', ''),
                    'website_field': row.get('website', ''),
                    'sp_url_field': row.get('senior_place_url', ''),
                })
    
    print(f"📊 Found {len(all_listings)} listings with Senior Place URLs")
    print("🏃‍♂️ Starting live sync (fast mode with 0.3s delays)")
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
        matches = 0
        
        for i, listing in enumerate(all_listings):
            processed += 1
            print(f"📋 {processed}/{len(all_listings)}: {listing['title']}")
            print(f"    URL: {listing['url']}")
            print(f"    Current WP: {', '.join(listing['current_wp_types']) if listing['current_wp_types'] else 'None'}")
            
            # Scrape live community types
            live_community_types = await scrape_community_types_from_seniorplace(context, listing['url'])
            
            if live_community_types:
                print(f"    🔍 Live SP: {live_community_types}")
                
                # Map to canonical WordPress types (ALL types, no prioritization yet)
                canonical_types = []
                for sp_type in live_community_types:
                    sp_lower = sp_type.lower()
                    if sp_lower in CANONICAL_MAPPING:
                        canonical = CANONICAL_MAPPING[sp_lower]
                        if canonical not in canonical_types:
                            canonical_types.append(canonical)
                
                if canonical_types:
                    print(f"    🎯 Should be: {', '.join(canonical_types)}")
                    
                    # Compare with current WordPress types
                    current_set = set(listing['current_wp_types'])
                    correct_set = set(canonical_types)
                    
                    if current_set != correct_set:
                        print(f"    🚨 MISMATCH - UPDATE NEEDED!")
                        
                        # Generate correct WordPress fields
                        correct_type_field = generate_wp_type_field(canonical_types)
                        correct_normalized_types = ', '.join(canonical_types)
                        
                        updates_needed.append({
                            'ID': listing['wp_id'],
                            'Title': listing['title'],
                            'type': correct_type_field,
                            'normalized_types': correct_normalized_types,
                            'live_senior_place_types': ', '.join(live_community_types),
                            'current_wp_types': ', '.join(listing['current_wp_types']) if listing['current_wp_types'] else 'None',
                            'correct_wp_types': correct_normalized_types,
                            'url': listing['url'],
                            'source_field': 'website' if 'seniorplace.com' in listing['website_field'] else 'senior_place_url'
                        })
                        
                        print(f"    📝 Added to updates")
                    else:
                        matches += 1
                        print(f"    ✅ Already correct")
                else:
                    print(f"    ⚠️  No canonical mapping found")
            else:
                failed += 1
                print(f"    ❌ Failed to scrape live data")
            
            print()
            
            # Fast pace but not too aggressive
            await asyncio.sleep(0.3)
            
            # Progress update every 25
            if processed % 25 == 0:
                print(f"🏃‍♂️ Progress: {processed}/{len(all_listings)} | Updates: {len(updates_needed)} | Matches: {matches} | Failed: {failed}")
                print()
        
        await browser.close()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n🎯 SYNC COMPLETE!")
        print(f"  Total processed: {processed}")
        print(f"  Updates needed: {len(updates_needed)}")
        print(f"  Already correct: {matches}")
        print(f"  Failed scrapes: {failed}")
        print()
        
        if updates_needed:
            # Save updates CSV
            updates_file = f"organized_csvs/SENIORPLACE_TYPE_SYNC_{timestamp}.csv"
            with open(updates_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=updates_needed[0].keys())
                writer.writeheader()
                writer.writerows(updates_needed)
            
            print(f"💾 SYNC UPDATES: {updates_file}")
            print(f"🚀 Import this file to WordPress using ID matching!")
            print()
            
            print(f"📋 SAMPLE MISMATCHES:")
            for i, update in enumerate(updates_needed[:5]):
                print(f"  {i+1}. {update['Title']}")
                print(f"     Live Senior Place: {update['live_senior_place_types']}")
                print(f"     Current WordPress: {update['current_wp_types']}")
                print(f"     Should be: {update['correct_wp_types']}")
                print(f"     Source: {update['source_field']}")
                print()
            
            if len(updates_needed) > 5:
                print(f"   ... and {len(updates_needed) - 5} more updates")
                
        else:
            print(f"✅ PERFECT SYNC!")
            print(f"   All {matches} Senior Place listings are correctly synced!")

def main():
    print("🚀 Starting comprehensive Senior Place type sync...")
    print("This will sync ALL listings with live Senior Place data")
    print()
    
    asyncio.run(sync_all_seniorplace_types())

if __name__ == "__main__":
    main()
