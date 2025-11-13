#!/usr/bin/env python3
"""
Fix misclassified assisted living homes that Senior Place incorrectly labels as "Assisted Living Facility"
when they are actually small homes (≤10 beds).

The canonical mapping is correct:
- "Assisted Living Facility" → "Assisted Living Community" ✅
- "Assisted Living Home" → "Assisted Living Home" ✅

The issue: Some Senior Place listings that are actually small homes are misclassified
as "Facility" in Senior Place's own data when they should be "Home".

This script will:
1. Identify listings that are likely misclassified (facilities that seem like homes)
2. Re-scrape those specific listings to verify their actual care types
3. Correct the misclassifications 
4. Apply the correct canonical mapping
"""

import csv
import asyncio
import re
from typing import Dict, List, Tuple, Optional
from playwright.async_api import async_playwright
import argparse

# CORRECT canonical mapping (client-approved from memory.md)
CANONICAL_MAPPING = {
    "assisted living facility": "Assisted Living Community",  # ✅ Correct
    "assisted living home": "Assisted Living Home",           # ✅ Correct
    "independent living": "Independent Living",               # ✅ Correct
    "memory care": "Memory Care",                            # ✅ Correct
    "skilled nursing": "Nursing Home",                       # ✅ Correct
    "continuing care retirement community": "Assisted Living Community",  # ✅ Correct
    "in-home care": "Home Care",                             # ✅ Correct
    "home health": "Home Care",                              # ✅ Correct
    "hospice": "Home Care",                                  # ✅ Correct
    "respite care": "Assisted Living Community",             # ✅ Correct
}

# WordPress term IDs (from memory.md)
CANONICAL_TO_ID = {
    "Assisted Living Community": 5,
    "Assisted Living Home": 162,
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    "Home Care": 488,
}

def identify_likely_misclassified_homes(csv_file: str) -> List[Dict]:
    """
    Identify listings that are likely misclassified as "Facility" when they're actually "Home"
    based on title patterns and other indicators
    """
    likely_misclassified = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '')
            current_type = decode_wordpress_type(row.get('type', ''))
            senior_place_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
            
            # Only check listings currently classified as "Assisted Living Community"
            # (which comes from Senior Place "Assisted Living Facility")
            if current_type == "Assisted Living Community" and senior_place_url:
                
                # Look for indicators this might actually be a home, not a facility
                title_lower = title.lower()
                
                # Strong indicators it's actually a home (≤10 beds)
                home_indicators = [
                    'home', 'house', 'care home', 'adult care', 'family care',
                    'residential', 'cottage', 'manor home', 'living home'
                ]
                
                # Address patterns that suggest homes vs facilities
                address = row.get('address', '') or row.get('_address', '')
                address_lower = address.lower()
                home_address_patterns = [
                    'way', 'drive', 'street', 'lane', 'court', 'circle', 'place'
                ]
                
                # Facility indicators (less likely to be misclassified)
                facility_indicators = [
                    'center', 'facility', 'community', 'village', 'manor', 'estates',
                    'towers', 'plaza', 'gardens', 'residence', 'assisted living of',
                    'senior living', 'retirement'
                ]
                
                has_home_indicator = any(indicator in title_lower for indicator in home_indicators)
                has_facility_indicator = any(indicator in title_lower for indicator in facility_indicators)
                has_home_address = any(pattern in address_lower for pattern in home_address_patterns)
                
                # Calculate a "home likelihood" score
                home_score = 0
                facility_score = 0
                
                if has_home_indicator:
                    home_score += 2
                if has_home_address and not has_facility_indicator:
                    home_score += 1
                if 'adult care' in title_lower or 'care home' in title_lower:
                    home_score += 3  # Strong indicators
                    
                if has_facility_indicator:
                    facility_score += 2
                if any(word in title_lower for word in ['community', 'center', 'village']):
                    facility_score += 1
                
                # If home score is higher, this might be misclassified
                if home_score > facility_score and home_score >= 2:
                    likely_misclassified.append({
                        'ID': row.get('ID', ''),
                        'Title': title,
                        'Address': address,
                        'Current_Type': current_type,
                        'Senior_Place_URL': senior_place_url,
                        'Home_Score': home_score,
                        'Facility_Score': facility_score,
                        'Home_Indicators': [ind for ind in home_indicators if ind in title_lower],
                        'Reason': f"Home score {home_score} > Facility score {facility_score}"
                    })
    
    return likely_misclassified

def decode_wordpress_type(type_field: str) -> str:
    """Decode WordPress serialized type field to readable name"""
    if not type_field or type_field == '0':
        return "Uncategorized"
    
    # Map IDs back to names
    id_to_name = {v: k for k, v in CANONICAL_TO_ID.items()}
    
    try:
        # Extract ID from serialized format like a:1:{i:0;i:162;}
        if 'i:0;i:' in type_field:
            match = re.search(r'i:0;i:(\d+);', type_field)
            if match:
                type_id = int(match.group(1))
                return id_to_name.get(type_id, f"Unknown ID {type_id}")
        
        return "Unknown format"
    except:
        return "Parse error"

async def verify_and_correct_care_types(misclassified_listings: List[Dict], username: str, password: str) -> List[Dict]:
    """
    Re-scrape the misclassified listings to verify their actual care types
    and correct them if needed
    """
    corrected_listings = []
    
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
        
        # Check each misclassified listing
        for i, listing in enumerate(misclassified_listings):
            print(f"\n🔍 Verifying {i+1}/{len(misclassified_listings)}: {listing['Title']}")
            
            # Scrape actual care types
            url = listing['Senior_Place_URL']
            actual_types = await scrape_actual_care_types(context, url)
            
            if actual_types:
                print(f"    📋 Senior Place shows: {actual_types}")
                
                # Apply canonical mapping to the actual types
                mapped_types = []
                for sp_type in actual_types:
                    sp_type_lower = sp_type.lower()
                    if sp_type_lower in CANONICAL_MAPPING:
                        canonical_type = CANONICAL_MAPPING[sp_type_lower]
                        if canonical_type not in mapped_types:
                            mapped_types.append(canonical_type)
                
                # Check if this fixes the misclassification
                if "Assisted Living Home" in mapped_types:
                    print(f"    ✅ CORRECTED: Should be 'Assisted Living Home', not 'Community'")
                    
                    # Generate corrected WordPress type field
                    home_id = CANONICAL_TO_ID["Assisted Living Home"]
                    corrected_type_field = f'a:1:{{i:0;i:{home_id};}}'
                    
                    corrected_listings.append({
                        'ID': listing['ID'],
                        'Title': listing['Title'],
                        'Original_Type': listing['Current_Type'],
                        'Corrected_Type': 'Assisted Living Home',
                        'Corrected_Type_Field': corrected_type_field,
                        'Senior_Place_Types': ', '.join(actual_types),
                        'Canonical_Types': ', '.join(mapped_types),
                        'Verification': 'Confirmed misclassification'
                    })
                elif "Assisted Living Community" in mapped_types:
                    print(f"    ℹ️  Confirmed: Actually is a facility (Community classification correct)")
                else:
                    print(f"    ⚠️  Unexpected types: {mapped_types}")
            else:
                print(f"    ❌ Failed to scrape care types")
        
        await browser.close()
    
    return corrected_listings

async def scrape_actual_care_types(context, url: str) -> List[str]:
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
                    if (!input.checked) continue; // Only checked boxes
                    
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

def main():
    parser = argparse.ArgumentParser(description="Fix misclassified assisted living homes")
    parser.add_argument('--input', required=True, help='Input CSV file (WordPress export)')
    parser.add_argument('--output-analysis', required=True, help='Output CSV for analysis results')
    parser.add_argument('--output-corrections', required=True, help='Output CSV for corrections to import')
    parser.add_argument('--username', default='allison@aplaceforseniors.org', help='Senior Place username')
    parser.add_argument('--password', default='Hugomax2023!', help='Senior Place password')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze, do not re-scrape')
    
    args = parser.parse_args()
    
    print("🔍 Identifying likely misclassified assisted living homes...")
    print("(Small homes incorrectly labeled as facilities)")
    
    # Step 1: Identify likely misclassified listings
    misclassified = identify_likely_misclassified_homes(args.input)
    
    print(f"\n📊 Found {len(misclassified)} likely misclassified listings:")
    for listing in misclassified[:10]:  # Show first 10
        print(f"  • {listing['Title']} (Score: H{listing['Home_Score']} vs F{listing['Facility_Score']})")
        print(f"    Indicators: {listing['Home_Indicators']}")
    
    if len(misclassified) > 10:
        print(f"  ... and {len(misclassified) - 10} more")
    
    # Save analysis
    if misclassified:
        with open(args.output_analysis, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=misclassified[0].keys())
            writer.writeheader()
            writer.writerows(misclassified)
        print(f"\n💾 Analysis saved to: {args.output_analysis}")
    
    # Step 2: Verify and correct (if not analyze-only)
    if not args.analyze_only and misclassified:
        print(f"\n🔄 Re-scraping {len(misclassified)} listings to verify...")
        
        corrected = asyncio.run(verify_and_correct_care_types(
            misclassified, args.username, args.password
        ))
        
        if corrected:
            with open(args.output_corrections, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=corrected[0].keys())
                writer.writeheader()
                writer.writerows(corrected)
            
            print(f"\n📈 Results:")
            print(f"   Analyzed: {len(misclassified)} listings")
            print(f"   Corrected: {len(corrected)} misclassifications")
            print(f"   Corrections saved to: {args.output_corrections}")
            
            print(f"\n🚀 Next step: Import {args.output_corrections} to WordPress")
            print("   Use WP All Import with ID matching to update the corrected types")
        else:
            print("\n✅ No corrections needed - all classifications were accurate")

if __name__ == "__main__":
    main()
