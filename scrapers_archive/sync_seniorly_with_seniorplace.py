#!/usr/bin/env python3
"""
Sync Seniorly listings with Senior Place community types.
Uses the matched pairs to scrape Senior Place and update Seniorly listings.
Records both Seniorly and Senior Place URLs for tracking.
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

async def sync_seniorly_with_seniorplace():
    """Sync Seniorly listings with Senior Place community types"""
    
    print("🔄 SYNCING SENIORLY LISTINGS WITH SENIOR PLACE TYPES")
    print("=" * 60)
    print("Using matched pairs to scrape Senior Place and update Seniorly categories")
    print("Recording both Seniorly and Senior Place URLs for tracking")
    print()
    
    # Read the matches file
    matches = []
    matches_file = None
    
    # Find the most recent matches file
    import os
    import glob
    
    match_files = glob.glob('organized_csvs/SENIORLY_TO_SENIORPLACE_MATCHES_*.csv')
    if match_files:
        matches_file = max(match_files, key=os.path.getctime)
        print(f"📁 Using matches file: {matches_file}")
    else:
        print("❌ No matches file found! Run analyze_seniorly_listings.py first.")
        return
    
    with open(matches_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        matches = list(reader)
    
    print(f"📊 Found {len(matches)} Seniorly → Senior Place matches")
    print()
    
    # Get current WordPress data for the Seniorly listings (match by Seniorly URL)
    wp_data = {}
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        for row in reader:
            seniorly_url = row.get('website', '')  # Seniorly URL is in the website field
            wp_id = row.get('ID', '')
            if seniorly_url and wp_id:
                wp_data[seniorly_url] = {
                    'wp_id': wp_id,
                    'current_types': decode_current_wp_type(row.get('type', '')),
                    'current_type_field': row.get('type', '')
                }
    
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
        
        # Process all matched pairs
        updates_needed = []
        processed = 0
        failed = 0
        matches_found = 0
        
        for i, match in enumerate(matches):
            processed += 1
            seniorly_wp_id = match['seniorly_wp_id']
            seniorly_title = match['seniorly_title']
            seniorly_url = match['seniorly_url']
            senior_place_url = match['senior_place_url']
            
            print(f"📋 {processed}/{len(matches)}: {seniorly_title}")
            print(f"    Seniorly URL: {seniorly_url}")
            print(f"    Senior Place URL: {senior_place_url}")
            
            # Get current WordPress types for this Seniorly listing (match by URL)
            current_wp_data = wp_data.get(seniorly_url, {})
            current_wp_types = current_wp_data.get('current_types', [])
            current_type_field = current_wp_data.get('current_type_field', '')
            actual_wp_id = current_wp_data.get('wp_id', seniorly_wp_id)
            
            print(f"    Current WP: {', '.join(current_wp_types) if current_wp_types else 'None'}")
            
            # Scrape live community types from Senior Place
            live_community_types = await scrape_community_types_from_seniorplace(context, senior_place_url)
            
            if live_community_types:
                print(f"    🔍 Live SP: {live_community_types}")
                
                # Map to canonical WordPress types (ALL types, no prioritization for now)
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
                    current_set = set(current_wp_types)
                    correct_set = set(canonical_types)
                    
                    if current_set != correct_set:
                        print(f"    🚨 MISMATCH - UPDATE NEEDED!")
                        
                        # Generate correct WordPress fields
                        correct_type_field = generate_wp_type_field(canonical_types)
                        correct_normalized_types = ', '.join(canonical_types)
                        
                        updates_needed.append({
                            'ID': actual_wp_id,
                            'Title': seniorly_title,
                            'type': correct_type_field,
                            'normalized_types': correct_normalized_types,
                            'seniorly_url': seniorly_url,
                            'senior_place_url': senior_place_url,
                            'live_senior_place_types': ', '.join(live_community_types),
                            'current_wp_types': ', '.join(current_wp_types) if current_wp_types else 'None',
                            'correct_wp_types': correct_normalized_types,
                            'match_score': match.get('match_score', ''),
                            'city': match.get('city', ''),
                            'state': match.get('state', ''),
                            'correction_reason': f'Synced from Senior Place: {", ".join(live_community_types)}'
                        })
                        
                        print(f"    📝 Added to updates")
                    else:
                        matches_found += 1
                        print(f"    ✅ Already correct")
                else:
                    print(f"    ⚠️  No canonical mapping found")
            else:
                failed += 1
                print(f"    ❌ Failed to scrape Senior Place data")
            
            print()
            
            # Fast pace but not too aggressive
            await asyncio.sleep(0.3)
            
            # Progress update every 25
            if processed % 25 == 0:
                print(f"🏃‍♂️ Progress: {processed}/{len(matches)} | Updates: {len(updates_needed)} | Matches: {matches_found} | Failed: {failed}")
                print()
        
        await browser.close()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n🎯 SENIORLY SYNC COMPLETE!")
        print(f"  Total processed: {processed}")
        print(f"  Updates needed: {len(updates_needed)}")
        print(f"  Already correct: {matches_found}")
        print(f"  Failed scrapes: {failed}")
        print()
        
        if updates_needed:
            # Save updates CSV
            updates_file = f"organized_csvs/SENIORLY_SYNC_UPDATES_{timestamp}.csv"
            with open(updates_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=updates_needed[0].keys())
                writer.writeheader()
                writer.writerows(updates_needed)
            
            print(f"💾 SENIORLY UPDATES: {updates_file}")
            print(f"🚀 Import this file to WordPress using ID matching!")
            print()
            
            print(f"📋 SAMPLE UPDATES:")
            for i, update in enumerate(updates_needed[:5]):
                print(f"  {i+1}. {update['Title']}")
                print(f"     Seniorly URL: {update['seniorly_url']}")
                print(f"     Senior Place URL: {update['senior_place_url']}")
                print(f"     Live Senior Place: {update['live_senior_place_types']}")
                print(f"     Current WordPress: {update['current_wp_types']}")
                print(f"     Should be: {update['correct_wp_types']}")
                print(f"     Match Score: {update['match_score']}")
                print()
            
            if len(updates_needed) > 5:
                print(f"   ... and {len(updates_needed) - 5} more updates")
                
        else:
            print(f"✅ PERFECT SYNC!")
            print(f"   All {matches_found} matched Seniorly listings are correctly synced!")
        
        print(f"\n📊 SUMMARY:")
        print(f"  • Seniorly listings with Senior Place matches: {len(matches)}")
        print(f"  • Successfully scraped Senior Place data: {processed - failed}")
        print(f"  • Updates needed: {len(updates_needed)}")
        print(f"  • Already correct: {matches_found}")
        print(f"  • Both URLs recorded for all processed listings")

def main():
    print("🚀 Starting Seniorly → Senior Place community type sync...")
    print("This will sync categories for all matched Seniorly listings")
    print()
    
    asyncio.run(sync_seniorly_with_seniorplace())

if __name__ == "__main__":
    main()
