#!/usr/bin/env python3
"""
Comprehensive fix for ALL facility vs home mismatches.

This will:
1. Check ALL Senior Place listings to find "Assisted Living Facility" types
2. Compare with WordPress data to find mismatches
3. Create a complete correction CSV with normalized types for OUR system
4. Generate import-ready file for WordPress All Import
"""

import csv
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import argparse

# Our canonical mapping (from memory.md)
CANONICAL_MAPPING = {
    "assisted living facility": "Assisted Living Community",
    "assisted living home": "Assisted Living Home",
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
    "Assisted Living Community": 5,
    "Assisted Living Home": 162,
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    "Home Care": 488,
}

def decode_wp_type(type_field):
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

def generate_wp_type_field(canonical_types):
    """Generate WordPress serialized type field"""
    if not canonical_types:
        return 'a:1:{i:0;i:1;}'  # Uncategorized
    
    type_ids = [CANONICAL_TO_ID[t] for t in canonical_types if t in CANONICAL_TO_ID]
    
    if len(type_ids) == 1:
        return f'a:1:{{i:0;i:{type_ids[0]};}}'
    else:
        items = ''.join(f'i:{i};i:{type_ids[i]};' for i in range(len(type_ids)))
        return f'a:{len(type_ids)}:{{{items}}}'

async def scrape_all_senior_place_types(username, password, max_listings=None):
    """Scrape care types for ALL Senior Place listings"""
    
    print("🔍 COMPREHENSIVE SENIOR PLACE CARE TYPE SCRAPING")
    print("=" * 60)
    
    # Get all Senior Place URLs from WordPress export
    all_sp_listings = []
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '').strip('"')
            senior_place_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
            
            if senior_place_url and 'seniorplace.com' in senior_place_url:
                all_sp_listings.append({
                    'wp_id': row.get('ID', ''),
                    'title': title,
                    'url': senior_place_url,
                    'current_wp_type': decode_wp_type(row.get('type', '')),
                    'current_type_field': row.get('type', ''),
                    'website': row.get('website', '') or row.get('_website', ''),
                })
    
    if max_listings:
        all_sp_listings = all_sp_listings[:max_listings]
    
    print(f"📊 Found {len(all_sp_listings)} Senior Place listings to check")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Login
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
        
        # Process all listings
        results = []
        stats = {
            'total_processed': 0,
            'scraped_successfully': 0,
            'facilities_found': 0,
            'mismatches_found': 0,
            'scraping_errors': 0
        }
        
        for i, listing in enumerate(all_sp_listings):
            stats['total_processed'] += 1
            
            print(f"📋 {i+1}/{len(all_sp_listings)}: {listing['title']}")
            
            # Scrape Senior Place care types
            sp_care_types = await scrape_care_types(context, listing['url'])
            
            if sp_care_types:
                stats['scraped_successfully'] += 1
                print(f"    Senior Place shows: {sp_care_types}")
                
                # Apply canonical mapping
                mapped_types = []
                for sp_type in sp_care_types:
                    sp_lower = sp_type.lower()
                    if sp_lower in CANONICAL_MAPPING:
                        canonical = CANONICAL_MAPPING[sp_lower]
                        if canonical not in mapped_types:
                            mapped_types.append(canonical)
                
                if mapped_types:
                    should_be_type = mapped_types[0] if len(mapped_types) == 1 else "Multiple Types"
                    
                    # Check for mismatch
                    if listing['current_wp_type'] != should_be_type and should_be_type != "Multiple Types":
                        stats['mismatches_found'] += 1
                        print(f"    WordPress shows: {listing['current_wp_type']}")
                        print(f"    Should be: {should_be_type}")
                        print(f"    🚨 MISMATCH!")
                        
                        # Generate correct type field
                        correct_type_field = generate_wp_type_field(mapped_types)
                        
                        results.append({
                            'ID': listing['wp_id'],
                            'Title': listing['title'],
                            'Website': listing['website'],
                            'Senior_Place_URL': listing['url'],
                            'Current_WP_Type': listing['current_wp_type'],
                            'Senior_Place_Types': ', '.join(sp_care_types),
                            'Correct_Normalized_Type': ', '.join(mapped_types),
                            'Should_Be_Type': should_be_type,
                            'Current_Type_Field': listing['current_type_field'],
                            'Correct_Type_Field': correct_type_field,
                            'Issue': 'Care type mismatch with Senior Place'
                        })
                    else:
                        print(f"    ✅ Correct: {listing['current_wp_type']}")
                
                # Track facilities specifically
                if 'Assisted Living Facility' in sp_care_types:
                    stats['facilities_found'] += 1
                
            else:
                stats['scraping_errors'] += 1
                print(f"    ❌ Failed to scrape care types")
            
            # Progress updates
            if stats['total_processed'] % 50 == 0:
                print(f"\n📊 Progress: {stats['total_processed']}/{len(all_sp_listings)} processed")
                print(f"   Mismatches found: {stats['mismatches_found']}")
                print(f"   Facilities found: {stats['facilities_found']}")
                print()
            
            # Small delay to be nice to Senior Place
            await asyncio.sleep(0.5)
        
        await browser.close()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if results:
            # Save mismatch analysis
            analysis_file = f"organized_csvs/FACILITY_MISMATCHES_ANALYSIS_{timestamp}.csv"
            with open(analysis_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            
            print(f"💾 Mismatch analysis saved: {analysis_file}")
            
            # Create WordPress import correction file
            correction_file = f"organized_csvs/WORDPRESS_CARE_TYPE_CORRECTIONS_{timestamp}.csv"
            
            # Read original WordPress export and apply corrections
            corrected_rows = []
            correction_ids = {r['ID'] for r in results}
            
            with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames)
                
                # Add correction tracking columns
                if 'corrected_care_types' not in fieldnames:
                    fieldnames.extend(['corrected_care_types', 'correction_applied', 'correction_reason'])
                
                for row in reader:
                    row_id = row.get('ID', '')
                    
                    # Check if this row needs correction
                    correction = next((c for c in results if c['ID'] == row_id), None)
                    if correction:
                        # Apply correction
                        row['type'] = correction['Correct_Type_Field']
                        row['corrected_care_types'] = correction['Correct_Normalized_Type']
                        row['correction_applied'] = 'Yes'
                        row['correction_reason'] = f"Updated from '{correction['Current_WP_Type']}' to '{correction['Should_Be_Type']}' based on Senior Place data"
                    else:
                        row['corrected_care_types'] = ''
                        row['correction_applied'] = 'No'
                        row['correction_reason'] = ''
                    
                    corrected_rows.append(row)
            
            # Save corrected WordPress export
            with open(correction_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(corrected_rows)
            
            print(f"💾 WordPress correction file saved: {correction_file}")
        
        # Final statistics
        print(f"\n🎯 FINAL RESULTS")
        print("=" * 40)
        print(f"Total listings processed: {stats['total_processed']}")
        print(f"Successfully scraped: {stats['scraped_successfully']}")
        print(f"Facilities found: {stats['facilities_found']}")
        print(f"Mismatches requiring correction: {stats['mismatches_found']}")
        print(f"Scraping errors: {stats['scraping_errors']}")
        
        if stats['mismatches_found'] > 0:
            print(f"\n🚀 NEXT STEPS:")
            print(f"1. Review {analysis_file}")
            print(f"2. Import {correction_file} to WordPress using WP All Import")
            print(f"3. Use ID matching to update care types")
        else:
            print(f"\n✅ All care types are correctly mapped!")
        
        return results

async def scrape_care_types(context, url):
    """Scrape care types from a Senior Place listing"""
    try:
        page = await context.new_page()
        
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="networkidle", timeout=20000)
        await page.wait_for_selector('text=Community Type', timeout=8000)
        
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
        if 'page' in locals():
            await page.close()
        return []

def main():
    parser = argparse.ArgumentParser(description="Comprehensive facility correction")
    parser.add_argument('--username', default='allison@aplaceforseniors.org', help='Senior Place username')
    parser.add_argument('--password', default='Hugomax2023!', help='Senior Place password')
    parser.add_argument('--limit', type=int, help='Limit for testing (default: all listings)')
    
    args = parser.parse_args()
    
    print("🚀 Starting comprehensive facility correction...")
    print("This will check ALL Senior Place listings and create correction CSV")
    print()
    
    asyncio.run(scrape_all_senior_place_types(
        args.username,
        args.password, 
        args.limit
    ))

if __name__ == "__main__":
    main()
