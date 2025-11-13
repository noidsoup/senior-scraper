#!/usr/bin/env python3
"""
Comprehensive check of ALL Senior Place listings in WordPress export.
Go through every row, check every Senior Place URL, compare live data to current WordPress data,
and create a CSV of all listings that need updates.
"""

import csv
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import re
import argparse

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

async def scrape_community_types_from_attributes(context, url, title, row_num, total_rows):
    """Scrape community types from Senior Place attributes page"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        print(f"    🔍 Checking: {attributes_url}")
        
        await page.goto(attributes_url, wait_until="networkidle", timeout=20000)
        
        # Wait for the specific Community Type section
        await page.wait_for_selector('div:has-text("Community Type(s)")', timeout=10000)
        
        # Extract community types using the exact HTML structure
        community_types = await page.evaluate("""
            () => {
                const communityTypes = [];
                
                // Find the Community Type(s) section specifically  
                const communityTypeDiv = Array.from(document.querySelectorAll('div')).find(div => 
                    div.textContent && div.textContent.trim() === 'Community Type(s)' && 
                    div.classList.contains('font-bold')
                );
                
                if (!communityTypeDiv) {
                    return [];
                }
                
                // Get the options container that follows the Community Type(s) header
                let optionsContainer = communityTypeDiv.parentElement.querySelector('.options');
                
                if (!optionsContainer) {
                    return [];
                }
                
                // Get all checked checkboxes in this specific section
                const checkedInputs = optionsContainer.querySelectorAll('input[type="checkbox"]:checked');
                
                for (const input of checkedInputs) {
                    // Find the label text next to this checkbox
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
        
        if community_types and len(community_types) > 0:
            print(f"    ✅ Found: {community_types}")
            return community_types
        else:
            print(f"    ⚠️  No community types found")
            return []
            
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
        if 'page' in locals():
            await page.close()
        return []

async def process_all_wordpress_listings(username, password, start_row=1, limit=None):
    """Process ALL WordPress listings and check every Senior Place URL"""
    
    print("🔍 COMPREHENSIVE SENIOR PLACE UPDATE CHECK")
    print("=" * 60)
    print("Checking EVERY Senior Place URL in WordPress export")
    print("Creating CSV of ALL listings that need updates")
    print()
    
    # Read entire WordPress export
    all_listings = []
    seniorplace_count = 0
    
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            if row_num < start_row:
                continue
                
            title = row.get('Title', '').strip('"')
            sp_url = extract_senior_place_url(row)
            
            all_listings.append({
                'row_num': row_num,
                'wp_id': row.get('ID', ''),
                'title': title,
                'url': sp_url,
                'current_wp_type': decode_current_wp_type(row.get('type', '')),
                'current_type_field': row.get('type', ''),
                'website': row.get('website', ''),
                'senior_place_url_field': row.get('senior_place_url', ''),
                'original_row': row  # Keep full row for final CSV
            })
            
            if sp_url:
                seniorplace_count += 1
            
            if limit and row_num >= start_row + limit - 1:
                break
    
    print(f"📊 Processing {len(all_listings)} total listings")
    print(f"🔗 Found {seniorplace_count} Senior Place URLs to check")
    print()
    
    if seniorplace_count == 0:
        print("❌ No Senior Place URLs found!")
        return
    
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
        
        # Process all listings
        updates_needed = []
        all_results = []
        processed_count = 0
        success_count = 0
        failed_count = 0
        
        for listing in all_listings:
            if not listing['url']:
                continue  # Skip non-Senior Place listings
                
            processed_count += 1
            print(f"📋 {processed_count}/{seniorplace_count}: Row {listing['row_num']} - {listing['title']}")
            print(f"    Current WP: {listing['current_wp_type']}")
            
            # Scrape current community types from Senior Place
            community_types = await scrape_community_types_from_attributes(
                context, 
                listing['url'], 
                listing['title'],
                listing['row_num'],
                len(all_listings)
            )
            
            if community_types:
                success_count += 1
                
                # Map to canonical types (ALL types, following memory rules)
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
                        print(f"    🚨 UPDATE NEEDED!")
                        print(f"      Current WP: {listing['current_wp_type']}")
                        print(f"      Should be: {should_be_types}")
                        
                        # Create update record with ALL necessary fields for WordPress import
                        update_record = dict(listing['original_row'])  # Start with original row
                        update_record.update({
                            'type': correct_type_field,
                            'normalized_types': should_be_types,
                            '_senior_place_scraped_types': ', '.join(community_types),
                            '_update_reason': f'SP shows: {", ".join(community_types)} → Maps to: {should_be_types}',
                            '_original_wp_types': listing['current_wp_type'],
                            '_scrape_url': listing['url'],
                            '_row_number': listing['row_num']
                        })
                        
                        updates_needed.append(update_record)
                    else:
                        print(f"    ✅ Already correct: {should_be_types}")
                
                all_results.append({
                    'row_num': listing['row_num'],
                    'wp_id': listing['wp_id'],
                    'title': listing['title'],
                    'url': listing['url'],
                    'community_types': community_types,
                    'canonical_types': canonical_types,
                    'current_wp_type': listing['current_wp_type'],
                    'status': 'update_needed' if listing['current_type_field'] != correct_type_field else 'correct'
                })
            else:
                failed_count += 1
                print(f"    ❌ Failed to get community types")
                
                all_results.append({
                    'row_num': listing['row_num'],
                    'wp_id': listing['wp_id'],
                    'title': listing['title'],
                    'url': listing['url'],
                    'community_types': [],
                    'canonical_types': [],
                    'current_wp_type': listing['current_wp_type'],
                    'status': 'failed'
                })
            
            print()
            
            # Small delay to be respectful
            await asyncio.sleep(0.3)
            
            # Progress update every 50 items
            if processed_count % 50 == 0:
                print(f"📈 Progress: {processed_count}/{seniorplace_count} processed, {len(updates_needed)} updates found so far")
                print()
        
        await browser.close()
        
        # Final results summary
        print(f"\n🎯 COMPREHENSIVE CHECK COMPLETE!")
        print(f"  Total listings processed: {len(all_listings)}")
        print(f"  Senior Place URLs checked: {processed_count}")
        print(f"  Successful scrapes: {success_count}")
        print(f"  Failed scrapes: {failed_count}")
        print(f"  Updates needed: {len(updates_needed)}")
        print()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save updates needed (the important file for WordPress import!)
        if updates_needed:
            updates_file = f"organized_csvs/ALL_SENIORPLACE_UPDATES_{timestamp}.csv"
            with open(updates_file, 'w', newline='', encoding='utf-8') as f:
                if updates_needed:
                    writer = csv.DictWriter(f, fieldnames=updates_needed[0].keys())
                    writer.writeheader()
                    writer.writerows(updates_needed)
            
            print(f"💾 🚀 UPDATES FILE: {updates_file}")
            print(f"   → Import this to WordPress using ID matching!")
            print(f"   → Contains {len(updates_needed)} listings with corrected care types")
            print()
            
            print(f"📋 SAMPLE UPDATES:")
            for i, update in enumerate(updates_needed[:5]):
                print(f"  {i+1}. Row {update['_row_number']}: {update['Title']}")
                print(f"     Senior Place: {update['_senior_place_scraped_types']}")
                print(f"     Should be: {update['normalized_types']}")
                print(f"     Currently: {update['_original_wp_types']}")
                print()
            
            if len(updates_needed) > 5:
                print(f"   ... and {len(updates_needed) - 5} more updates")
                print()
                
            print(f"🔥 READY TO IMPORT: Use WordPress All Import with:")
            print(f"   • File: {updates_file}")
            print(f"   • Match by: ID")
            print(f"   • Map 'normalized_types' to Type taxonomy (comma-separated)")
            print(f"   • Map 'type' to custom field '_type'")
        else:
            print(f"✅ NO UPDATES NEEDED! All {success_count} Senior Place listings are correctly mapped.")
        
        # Save full analysis for reference
        if all_results:
            analysis_file = f"organized_csvs/FULL_SENIORPLACE_ANALYSIS_{timestamp}.csv"
            with open(analysis_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['row_num', 'wp_id', 'title', 'url', 'community_types', 'canonical_types', 'current_wp_type', 'status']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for result in all_results:
                    output_row = {
                        'row_num': result['row_num'],
                        'wp_id': result['wp_id'],
                        'title': result['title'],
                        'url': result['url'],
                        'community_types': ', '.join(result['community_types']) if result['community_types'] else '',
                        'canonical_types': ', '.join(result['canonical_types']) if result['canonical_types'] else '',
                        'current_wp_type': result['current_wp_type'],
                        'status': result['status']
                    }
                    writer.writerow(output_row)
            
            print(f"💾 Full analysis: {analysis_file}")

def main():
    parser = argparse.ArgumentParser(description="Comprehensive check of all Senior Place listings")
    parser.add_argument('--username', default='allison@aplaceforseniors.org', help='Senior Place username')
    parser.add_argument('--password', default='Hugomax2023!', help='Senior Place password')
    parser.add_argument('--start-row', type=int, default=1, help='Start from this row number (for resuming)')
    parser.add_argument('--limit', type=int, help='Limit processing to N rows (for testing)')
    
    args = parser.parse_args()
    
    print("🚀 Starting comprehensive Senior Place update check...")
    print("This will check EVERY Senior Place URL and create update CSV")
    print()
    
    asyncio.run(process_all_wordpress_listings(args.username, args.password, args.start_row, args.limit))

if __name__ == "__main__":
    main()
