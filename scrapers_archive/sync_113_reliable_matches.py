#!/usr/bin/env python3
"""
Sync community types for the 113 highly reliable Seniorly-Senior Place matches.
These are facilities with ≥0.8 title similarity and exact address matches.
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

def decode_current_wp_type(type_field):
    """Decode current WordPress type field to human readable"""
    if not type_field or type_field == '0':
        return []
    
    type_ids = re.findall(r'i:\d+;i:(\d+);', type_field)
    type_names = []
    
    for type_id in type_ids:
        type_id_int = int(type_id)
        if type_id_int in ID_TO_CANONICAL:
            type_names.append(ID_TO_CANONICAL[type_id_int])
    
    return type_names

def generate_wp_type_field(canonical_types):
    """Generate WordPress serialized type field for multiple types"""
    if not canonical_types:
        return 'a:1:{i:0;i:1;}'  # Uncategorized
    
    type_ids = [CANONICAL_TO_ID[t] for t in canonical_types if t in CANONICAL_TO_ID]
    
    if len(type_ids) == 1:
        return f'a:1:{{i:0;i:{type_ids[0]};}}'
    else:
        items = ''.join(f'i:{i};i:{type_ids[i]};' for i in range(len(type_ids)))
        return f'a:{len(type_ids)}:{{{items}}}'

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
                const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                for (const label of labels) {
                    const textEl = label.querySelector("div.ml-2");
                    const input = label.querySelector('input[type="checkbox"]');
                    if (!textEl || !input) continue;
                    if (!input.checked) continue;
                    const name = (textEl.textContent || "").trim();
                    const nameLower = name.toLowerCase();
                    if (validTypes.includes(nameLower)) {
                        communityTypes.push(name);
                    }
                }
                return communityTypes;
            }
        """)
        
        await page.close()
        return community_types
        
    except Exception as e:
        print(f"    ❌ Error scraping {url}: {str(e)}")
        return []

async def sync_reliable_matches():
    """Sync community types for the 113 reliable matches"""
    
    print("🔄 SYNCING 113 HIGHLY RELIABLE SENIORLY-SENIOR PLACE MATCHES")
    print("=" * 65)
    print("Scraping live Senior Place community types for facilities with:")
    print("  • ≥0.8 title similarity")
    print("  • Exact address matches")
    print("  • High confidence they're the same facilities")
    print()
    
    # Load reliable matches
    matches = []
    with open('organized_csvs/HIGHLY_RELIABLE_SENIORLY_SENIORPLACE_MATCHES.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        matches = list(reader)
    
    if not matches:
        print("❌ No reliable matches found!")
        return
    
    print(f"📊 Found {len(matches)} reliable matches to sync")
    print()
    
    # Get current WordPress data
    wp_data = {}
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            wp_id = row.get('ID', '')
            if wp_id:
                wp_data[wp_id] = {
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
        await page.wait_for_selector('text=Communities', timeout=10000)
        await page.close()
        print("✅ Logged in successfully")
        print()
        
        updates_needed = []
        matches_found = 0
        processed = 0
        
        for match in matches:
            processed += 1
            seniorly_wp_id = match.get('seniorly_wp_id', '')
            seniorly_title = match.get('seniorly_title', '')
            senior_place_url = match.get('senior_place_url', '')
            senior_place_title = match.get('senior_place_title', '')
            title_similarity = match.get('title_similarity', '')
            
            print(f"📋 {processed}/{len(matches)}: {seniorly_title}")
            print(f"    → {senior_place_title} (similarity: {title_similarity})")
            print(f"    Senior Place URL: {senior_place_url}")
            
            # Get current WordPress types
            current_wp_data = wp_data.get(seniorly_wp_id, {})
            current_wp_types = current_wp_data.get('current_types', [])
            
            print(f"    Current WP: {', '.join(current_wp_types) if current_wp_types else 'None'}")
            
            # Scrape live community types from Senior Place
            live_community_types = await scrape_community_types_from_seniorplace(context, senior_place_url)
            
            if live_community_types:
                print(f"    🔍 Live SP: {live_community_types}")
                
                # Map to canonical types
                canonical_types = []
                for community_type in live_community_types:
                    canonical = CANONICAL_MAPPING.get(community_type.lower())
                    if canonical and canonical not in canonical_types:
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
                            'ID': seniorly_wp_id,
                            'Title': seniorly_title,
                            'type': correct_type_field,
                            'normalized_types': correct_normalized_types,
                            'senior_place_url': senior_place_url,
                            'seniorly_url': match.get('seniorly_url', ''),
                            'live_senior_place_types': ', '.join(live_community_types),
                            'current_wp_types': ', '.join(current_wp_types) if current_wp_types else 'None',
                            'correct_wp_types': correct_normalized_types,
                            'title_similarity': title_similarity,
                            'correction_reason': f'Synced from Senior Place: {", ".join(live_community_types)}'
                        })
                        
                        print(f"    📝 Added to updates")
                    else:
                        matches_found += 1
                        print(f"    ✅ Already correct")
                else:
                    print(f"    ⚠️ No mappable types found")
            else:
                print(f"    ❌ Could not scrape community types")
            
            print()
            
            # Small delay to be respectful
            await asyncio.sleep(1)
        
        await browser.close()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if updates_needed:
        output_file = f'organized_csvs/SYNC_113_RELIABLE_MATCHES_{timestamp}.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['ID', 'Title', 'type', 'normalized_types', 'senior_place_url', 'seniorly_url', 
                         'live_senior_place_types', 'current_wp_types', 'correct_wp_types', 
                         'title_similarity', 'correction_reason']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updates_needed)
        
        print("📊 SYNC RESULTS:")
        print(f"  🔄 Updates needed: {len(updates_needed)}")
        print(f"  ✅ Already correct: {matches_found}")
        print(f"  📁 Updates saved to: {output_file}")
        print()
        
        # Show sample updates
        if updates_needed:
            print("🎯 SAMPLE UPDATES:")
            for i, update in enumerate(updates_needed[:5]):
                print(f"  {i+1}. {update['Title']}")
                print(f"     Current: {update['current_wp_types']}")
                print(f"     Should be: {update['correct_wp_types']}")
                print(f"     Senior Place: {update['live_senior_place_types']}")
                print()
    else:
        print("✅ All 113 reliable matches already have correct categories!")

if __name__ == "__main__":
    asyncio.run(sync_reliable_matches())
