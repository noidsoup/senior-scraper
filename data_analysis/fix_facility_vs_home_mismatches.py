#!/usr/bin/env python3
"""
Fix the exact issue identified by the user:

PROBLEM: Large facilities showing as "Assisted Living Home" instead of "Assisted Living Community"

EXAMPLE: Avista Senior Living North Mountain
- Senior Place: "Assisted Living Facility" ✅ 
- Our site: "Assisted Living Home" ❌ (should be "Community")

SOLUTION:
1. Find all Senior Place listings marked as "Assisted Living Facility"
2. Verify they map to "Assisted Living Community" (ID 5), not "Home" (ID 162)
3. Find mismatches and generate corrections
4. Ensure canonical mapping is properly applied
"""

import csv
import asyncio
import re
from typing import Dict, List, Tuple
from playwright.async_api import async_playwright
import argparse
from datetime import datetime

# Correct canonical mapping (from memory.md)
CANONICAL_MAPPING = {
    "assisted living facility": "Assisted Living Community",  # ✅ Large facilities → Community
    "assisted living home": "Assisted Living Home",           # ✅ Small homes → Home
    "independent living": "Independent Living",
    "memory care": "Memory Care",
    "skilled nursing": "Nursing Home",
    "continuing care retirement community": "Assisted Living Community",
    "in-home care": "Home Care",
    "home health": "Home Care",
    "hospice": "Home Care",
    "respite care": "Assisted Living Community",
}

# WordPress term IDs
CANONICAL_TO_ID = {
    "Assisted Living Community": 5,  # Should be large facilities
    "Assisted Living Home": 162,     # Should be small homes
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    "Home Care": 488,
}

async def scrape_senior_place_care_types(context, url: str) -> List[str]:
    """Scrape actual care types from Senior Place"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="networkidle", timeout=30000)
        
        # Wait for community type section
        await page.wait_for_selector('text=Community Type', timeout=10000)
        
        # Extract checked care types
        care_types = await page.evaluate("""
            () => {
                const careTypes = [];
                const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                
                for (const label of labels) {
                    const textEl = label.querySelector("div.ml-2");
                    const input = label.querySelector('input[type="checkbox"]');
                    
                    if (!textEl || !input) continue;
                    if (!input.checked) continue;
                    
                    const name = (textEl.textContent || "").trim();
                    if (name) careTypes.push(name);
                }
                
                return careTypes;
            }
        """)
        
        await page.close()
        return care_types
        
    except Exception as e:
        print(f"    ❌ Error scraping: {str(e)}")
        if 'page' in locals():
            await page.close()
        return []

def decode_wordpress_type(type_field: str) -> str:
    """Decode WordPress type field to readable name"""
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

def generate_correct_type_field(care_types: List[str]) -> str:
    """Generate correct WordPress type field based on Senior Place care types"""
    mapped_types = []
    
    for sp_type in care_types:
        sp_lower = sp_type.lower()
        if sp_lower in CANONICAL_MAPPING:
            canonical = CANONICAL_MAPPING[sp_lower]
            if canonical not in mapped_types:
                mapped_types.append(canonical)
    
    if not mapped_types:
        return f'a:1:{{i:0;i:1;}}' # Uncategorized
    
    # Get type IDs
    type_ids = [CANONICAL_TO_ID[t] for t in mapped_types if t in CANONICAL_TO_ID]
    
    if len(type_ids) == 1:
        return f'a:1:{{i:0;i:{type_ids[0]};}}' 
    else:
        # Multiple types
        items = ''.join(f'i:{i};i:{type_ids[i]};' for i in range(len(type_ids)))
        return f'a:{len(type_ids)}:{{{items}}}'

async def find_and_fix_mismatches(csv_file: str, username: str, password: str, limit: int = None):
    """Find facilities incorrectly classified as homes and fix them"""
    
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
        print("✅ Successfully logged in")
        await page.close()
        
        # Process CSV
        mismatches = []
        corrections = []
        stats = {
            'total_processed': 0,
            'senior_place_listings': 0,
            'facilities_found': 0,
            'mismatched_facilities': 0,
            'correctly_mapped': 0,
        }
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                    
                stats['total_processed'] += 1
                title = row.get('Title', '').strip('"')
                senior_place_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
                current_type_field = row.get('type', '')
                current_wp_type = decode_wordpress_type(current_type_field)
                
                if not senior_place_url or 'seniorplace.com' not in senior_place_url:
                    continue
                
                stats['senior_place_listings'] += 1
                print(f"\n📋 Processing {stats['senior_place_listings']}: {title}")
                print(f"    Current WordPress type: {current_wp_type}")
                
                # Scrape actual Senior Place care types
                actual_sp_types = await scrape_senior_place_care_types(context, senior_place_url)
                
                if actual_sp_types:
                    print(f"    Senior Place shows: {actual_sp_types}")
                    
                    # Check if this is a facility
                    is_facility = "Assisted Living Facility" in actual_sp_types
                    is_home = "Assisted Living Home" in actual_sp_types
                    
                    if is_facility:
                        stats['facilities_found'] += 1
                        
                        # Should be mapped to "Assisted Living Community"
                        if current_wp_type == "Assisted Living Home":
                            # MISMATCH! Facility showing as Home
                            stats['mismatched_facilities'] += 1
                            print(f"    ⚠️  MISMATCH: Facility showing as Home!")
                            
                            # Generate correct type field
                            correct_type_field = generate_correct_type_field(actual_sp_types)
                            
                            mismatch = {
                                'ID': row.get('ID', ''),
                                'Title': title,
                                'Current_WP_Type': current_wp_type,
                                'Should_Be_Type': 'Assisted Living Community',
                                'Senior_Place_Types': ', '.join(actual_sp_types),
                                'Senior_Place_URL': senior_place_url,
                                'Issue': 'Facility incorrectly showing as Home'
                            }
                            mismatches.append(mismatch)
                            
                            correction = {
                                'ID': row.get('ID', ''),
                                'Title': title,
                                'type': correct_type_field,
                                'corrected_care_types': ', '.join(actual_sp_types),
                                'correction_reason': 'Fixed facility misclassified as home'
                            }
                            corrections.append(correction)
                            
                        elif current_wp_type == "Assisted Living Community":
                            stats['correctly_mapped'] += 1
                            print(f"    ✅ CORRECT: Facility properly showing as Community")
                        else:
                            print(f"    ℹ️  Has other types: {current_wp_type}")
                    
                    elif is_home:
                        if current_wp_type == "Assisted Living Home":
                            print(f"    ✅ CORRECT: Home properly showing as Home")
                        elif current_wp_type == "Assisted Living Community":
                            print(f"    ℹ️  Home showing as Community (might be intentional)")
                    else:
                        print(f"    ℹ️  Other care types: {actual_sp_types}")
                else:
                    print(f"    ❌ Failed to scrape Senior Place care types")
                
                # Progress update
                if stats['total_processed'] % 25 == 0:
                    print(f"\n📊 Progress: {stats['total_processed']} processed, {stats['mismatched_facilities']} mismatches found")
        
        await browser.close()
        
        # Generate output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save mismatch analysis
        if mismatches:
            analysis_file = f"organized_csvs/FACILITY_HOME_MISMATCHES_{timestamp}.csv"
            with open(analysis_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=mismatches[0].keys())
                writer.writeheader()
                writer.writerows(mismatches)
            print(f"\n💾 Mismatch analysis saved to: {analysis_file}")
        
        # Save corrections for WordPress import
        if corrections:
            corrections_file = f"organized_csvs/FACILITY_HOME_CORRECTIONS_{timestamp}.csv"
            
            # Add all original fields for WP import
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                original_fieldnames = reader.fieldnames
                
                corrected_rows = []
                for row in reader:
                    row_id = row.get('ID', '')
                    
                    # Check if this row needs correction
                    correction = next((c for c in corrections if c['ID'] == row_id), None)
                    if correction:
                        # Apply correction
                        row['type'] = correction['type']
                        row['corrected_care_types'] = correction['corrected_care_types']
                        row['correction_reason'] = correction['correction_reason']
                    
                    corrected_rows.append(row)
            
            # Add new columns to fieldnames
            extended_fieldnames = list(original_fieldnames) + ['corrected_care_types', 'correction_reason']
            
            with open(corrections_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=extended_fieldnames)
                writer.writeheader()
                writer.writerows(corrected_rows)
            
            print(f"💾 Corrections CSV saved to: {corrections_file}")
        
        # Print final stats
        print(f"\n📈 FINAL RESULTS:")
        print(f"   Total processed: {stats['total_processed']}")
        print(f"   Senior Place listings: {stats['senior_place_listings']}")
        print(f"   Facilities found: {stats['facilities_found']}")
        print(f"   Mismatched facilities: {stats['mismatched_facilities']}")
        print(f"   Correctly mapped: {stats['correctly_mapped']}")
        
        if stats['mismatched_facilities'] > 0:
            print(f"\n🚀 NEXT STEPS:")
            print(f"   1. Review the mismatch analysis file")
            print(f"   2. Import the corrections CSV to WordPress using WP All Import")
            print(f"   3. Use ID matching to update the type field for mismatched listings")
        else:
            print(f"\n✅ No mismatches found - all facilities are correctly mapped!")

def main():
    parser = argparse.ArgumentParser(description="Fix facility vs home mismatches")
    parser.add_argument('--input', required=True, help='Input CSV file (WordPress export)')
    parser.add_argument('--username', default='allison@aplaceforseniors.org', help='Senior Place username')
    parser.add_argument('--password', default='Hugomax2023!', help='Senior Place password')
    parser.add_argument('--limit', type=int, help='Limit processing for testing')
    
    args = parser.parse_args()
    
    print("🔍 FIXING FACILITY VS HOME MISMATCHES")
    print("=" * 50)
    print("Looking for Senior Place 'Assisted Living Facility' listings")
    print("that are incorrectly showing as 'Assisted Living Home' on our site")
    print()
    
    asyncio.run(find_and_fix_mismatches(
        args.input, 
        args.username, 
        args.password,
        args.limit
    ))

if __name__ == "__main__":
    main()
