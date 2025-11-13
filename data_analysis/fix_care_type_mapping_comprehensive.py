#!/usr/bin/env python3
"""
Comprehensive fix for the care type mapping issue.

This script addresses the critical problem where "Assisted Living Facility" 
was being incorrectly mapped to "Assisted Living Community", losing the 
important distinction between homes and facilities.

The fix:
1. Updates all mapping dictionaries with the corrected logic
2. Re-scrapes Senior Place to get actual care types (not our incorrect mappings)
3. Applies the corrected mapping that preserves home vs facility distinction
4. Generates corrected CSV for WordPress import

Prerequisites:
- "Assisted Living Facility" category must exist in WordPress
- Senior Place login credentials available
"""

import csv
import asyncio
import argparse
import re
from typing import Dict, List, Tuple, Optional
from playwright.async_api import async_playwright
from collections import defaultdict
import json
import os
from datetime import datetime

# CORRECTED TYPE MAPPING - preserves home vs facility distinction
CORRECTED_TYPE_MAPPING = {
    "assisted living facility": "Assisted Living Facility",  # FIX: Don't convert to Community
    "assisted living home": "Assisted Living Home",          # UNCHANGED: Small homes stay homes
    "independent living": "Independent Living",               # UNCHANGED
    "memory care": "Memory Care",                            # UNCHANGED  
    "skilled nursing": "Nursing Home",                       # UNCHANGED
    "continuing care retirement community": "Assisted Living Community",  # UNCHANGED: CCRC as community
    "in-home care": "Home Care",                             # UNCHANGED
    "home health": "Home Care",                              # UNCHANGED
    "hospice": "Home Care",                                  # UNCHANGED
    "respite care": "Assisted Living Community",             # UNCHANGED
}

# WordPress term IDs (update this after creating Assisted Living Facility category)
CANONICAL_TO_ID = {
    "Assisted Living Community": 5,
    "Assisted Living Home": 162, 
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    "Home Care": 488,
    "Assisted Living Facility": 999,  # UPDATE THIS with actual ID after creating category
    "Uncategorized": 1,
}

async def scrape_seniorplace_care_types(context, url: str, max_retries: int = 3) -> Tuple[str, List[str]]:
    """Scrape actual care types from Senior Place (requires login)"""
    
    for attempt in range(max_retries):
        try:
            page = await context.new_page()
            
            # Navigate to attributes page (where care types are shown)
            attributes_url = f"{url.rstrip('/')}/attributes"
            print(f"  🔍 Scraping: {attributes_url}")
            
            await page.goto(attributes_url, wait_until="networkidle", timeout=30000)
            
            # Wait for the community type section to load
            try:
                await page.wait_for_selector('text=Community Type', timeout=10000)
            except:
                print(f"    ⚠️  Community Type section not found, trying main page...")
                return url, []
            
            # Extract checked care types using the correct selector
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
                print(f"    ✅ Found care types: {care_types}")
                return url, care_types
            else:
                print(f"    ⚠️  No care types found (attempt {attempt + 1})")
                
        except Exception as e:
            print(f"    ❌ Error scraping {url} (attempt {attempt + 1}): {str(e)}")
            if 'page' in locals():
                await page.close()
        
        if attempt < max_retries - 1:
            await asyncio.sleep(2)  # Wait before retry
    
    return url, []

def apply_corrected_mapping(senior_place_types: List[str]) -> Tuple[List[str], List[str]]:
    """Apply the corrected mapping that preserves facility vs home distinction"""
    mapped_types = []
    unmapped_types = []
    
    for sp_type in senior_place_types:
        sp_type_lower = sp_type.lower()
        
        if sp_type_lower in CORRECTED_TYPE_MAPPING:
            cms_type = CORRECTED_TYPE_MAPPING[sp_type_lower]
            if cms_type not in mapped_types:  # Avoid duplicates
                mapped_types.append(cms_type)
        else:
            unmapped_types.append(sp_type)
            print(f"    ⚠️  Unmapped type: {sp_type}")
    
    return mapped_types, unmapped_types

def generate_wordpress_type_field(mapped_types: List[str]) -> str:
    """Generate WordPress serialized type field"""
    if not mapped_types:
        return f'a:1:{{i:0;i:{CANONICAL_TO_ID["Uncategorized"]};}}'
    
    # Get type IDs, skip any that don't have IDs yet
    type_ids = []
    for cms_type in mapped_types:
        if cms_type in CANONICAL_TO_ID:
            type_id = CANONICAL_TO_ID[cms_type]
            if type_id != 999:  # Skip placeholder ID
                type_ids.append(type_id)
        else:
            print(f"    ⚠️  No ID found for type: {cms_type}")
    
    if not type_ids:
        return f'a:1:{{i:0;i:{CANONICAL_TO_ID["Uncategorized"]};}}'
    
    if len(type_ids) == 1:
        return f'a:1:{{i:0;i:{type_ids[0]};}}'
    else:
        # Multiple types
        items = ''.join(f'i:{i};i:{type_ids[i]};' for i in range(len(type_ids)))
        return f'a:{len(type_ids)}:{{{items}}}'

async def fix_care_types_for_csv(input_csv: str, output_csv: str, username: str, password: str, limit: Optional[int] = None):
    """Main function to fix care types in CSV"""
    
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
        
        # Wait for successful login
        await page.wait_for_selector('text=Communities', timeout=15000)
        print("✅ Successfully logged in")
        await page.close()
        
        # Process CSV
        corrected_rows = []
        stats = {
            'total_processed': 0,
            'senior_place_found': 0,
            'types_corrected': 0,
            'no_types_found': 0,
            'errors': 0
        }
        
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            # Add new columns for tracking the correction
            if 'scraped_care_types_corrected' not in fieldnames:
                fieldnames = list(fieldnames) + ['scraped_care_types_corrected', 'corrected_mapping_applied']
            
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                    
                stats['total_processed'] += 1
                title = row.get('Title', '')
                
                # Find Senior Place URL
                senior_place_url = (
                    row.get('senior_place_url', '') or 
                    row.get('_senior_place_url', '') or
                    row.get('website', '') if 'seniorplace.com' in row.get('website', '') else ''
                )
                
                if senior_place_url and 'seniorplace.com' in senior_place_url:
                    stats['senior_place_found'] += 1
                    print(f"\n📋 Processing {stats['senior_place_found']}: {title}")
                    
                    # Scrape actual care types from Senior Place
                    scraped_url, scraped_types = await scrape_seniorplace_care_types(context, senior_place_url)
                    
                    if scraped_types:
                        # Apply corrected mapping
                        mapped_types, unmapped_types = apply_corrected_mapping(scraped_types)
                        
                        if mapped_types:
                            stats['types_corrected'] += 1
                            
                            # Generate corrected WordPress type field
                            corrected_type_field = generate_wordpress_type_field(mapped_types)
                            
                            # Update row with corrected data
                            row['type'] = corrected_type_field
                            row['scraped_care_types_corrected'] = ', '.join(scraped_types)
                            row['corrected_mapping_applied'] = ', '.join(mapped_types)
                            
                            print(f"    ✅ Corrected: {scraped_types} → {mapped_types}")
                            
                            if unmapped_types:
                                print(f"    ⚠️  Unmapped: {unmapped_types}")
                        else:
                            stats['no_types_found'] += 1
                            row['scraped_care_types_corrected'] = ', '.join(scraped_types)
                            row['corrected_mapping_applied'] = 'No mappable types'
                    else:
                        stats['errors'] += 1
                        row['scraped_care_types_corrected'] = 'Scraping failed'
                        row['corrected_mapping_applied'] = 'Error'
                        
                else:
                    # Non-Senior Place listing
                    row['scraped_care_types_corrected'] = 'N/A (not Senior Place)'
                    row['corrected_mapping_applied'] = 'N/A'
                
                corrected_rows.append(row)
                
                # Progress update
                if stats['total_processed'] % 25 == 0:
                    print(f"\n📊 Progress: {stats['total_processed']} processed, {stats['types_corrected']} corrected")
        
        await browser.close()
        
        # Save corrected CSV
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            if corrected_rows:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(corrected_rows)
        
        # Print final stats
        print(f"\n📈 Final Statistics:")
        print(f"   Total processed: {stats['total_processed']}")
        print(f"   Senior Place listings: {stats['senior_place_found']}")
        print(f"   Care types corrected: {stats['types_corrected']}")
        print(f"   No types found: {stats['no_types_found']}")
        print(f"   Errors: {stats['errors']}")
        print(f"\n💾 Corrected data saved to: {output_csv}")

def main():
    parser = argparse.ArgumentParser(description="Fix care type mapping with corrected logic")
    parser.add_argument('--input', required=True, help='Input CSV file')
    parser.add_argument('--output', required=True, help='Output CSV file') 
    parser.add_argument('--username', default='allison@aplaceforseniors.org', help='Senior Place username')
    parser.add_argument('--password', default='Hugomax2023!', help='Senior Place password')
    parser.add_argument('--limit', type=int, help='Limit number of listings to process (for testing)')
    parser.add_argument('--facility-category-id', type=int, help='WordPress ID for Assisted Living Facility category')
    
    args = parser.parse_args()
    
    # Update the category ID if provided
    if args.facility_category_id:
        CANONICAL_TO_ID["Assisted Living Facility"] = args.facility_category_id
        print(f"📝 Updated Assisted Living Facility category ID to: {args.facility_category_id}")
    else:
        print("⚠️  WARNING: Using placeholder ID (999) for Assisted Living Facility")
        print("   Use --facility-category-id to specify the actual WordPress category ID")
    
    print("🚀 Starting care type mapping correction...")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print("Corrected mapping logic will preserve facility vs home distinction")
    
    asyncio.run(fix_care_types_for_csv(
        args.input, 
        args.output, 
        args.username, 
        args.password,
        args.limit
    ))

if __name__ == "__main__":
    main()
