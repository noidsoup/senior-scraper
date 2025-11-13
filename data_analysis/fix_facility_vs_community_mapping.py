#!/usr/bin/env python3
"""
Fix the care type mapping issue where "Assisted Living Facility" was incorrectly 
being mapped to "Assisted Living Community" instead of preserving the distinction.

The issue: Senior Place has:
- Assisted Living Home (small, ≤10 beds)  
- Assisted Living Facility (larger facilities)
- Independent Living (separate category)

Our mapping was converting both homes and facilities to "Community" which
loses the important distinction that Senior Place maintains.

This script will:
1. Check what WordPress categories we have available
2. Create "Assisted Living Facility" as a separate category if needed
3. Re-map listings that should be "Facility" instead of "Community"
4. Generate corrected CSV for import
"""

import csv
import requests
import json
from typing import Dict, List, Set
from collections import defaultdict

# Corrected mapping that preserves the home vs facility distinction
CORRECTED_TYPE_MAPPING = {
    "assisted living facility": "Assisted Living Facility",  # Keep as facility, not community
    "assisted living home": "Assisted Living Home",  # Small homes stay as homes
    "independent living": "Independent Living",
    "memory care": "Memory Care", 
    "skilled nursing": "Nursing Home",
    "continuing care retirement community": "Assisted Living Community",  # CCRC can be community
    "in-home care": "Home Care",
    "home health": "Home Care",
    "hospice": "Home Care", 
    "respite care": "Assisted Living Community",
}

# Current WordPress term IDs (we may need to add a new one for "Assisted Living Facility")
CURRENT_CANONICAL_TO_ID = {
    "Assisted Living Community": 5,
    "Assisted Living Home": 162,
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    "Home Care": 488,
    # "Assisted Living Facility": ???  # Need to check if this exists or create it
}

def check_wordpress_categories():
    """Check what categories exist in WordPress"""
    try:
        wp_api_url = "https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2/categories"
        response = requests.get(wp_api_url, params={"per_page": 100})
        
        if response.status_code == 200:
            categories = response.json()
            print(f"Found {len(categories)} WordPress categories:")
            
            care_type_categories = []
            for cat in categories:
                if any(keyword in cat['name'].lower() for keyword in ['assisted', 'living', 'memory', 'nursing', 'home', 'care']):
                    care_type_categories.append(cat)
                    print(f"  ID {cat['id']}: {cat['name']} (slug: {cat['slug']})")
            
            return care_type_categories
        else:
            print(f"Failed to fetch categories: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Error checking WordPress categories: {e}")
        return []

def analyze_current_mapping_issues(csv_file):
    """Analyze the current data to identify mapping issues"""
    facility_vs_community_issues = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '')
            type_field = row.get('type', '')
            senior_place_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
            
            # Look for listings that might be facilities being labeled as communities
            if senior_place_url and 'seniorplace' in senior_place_url:
                # Check for clues in the title that suggest it's a facility vs home
                title_lower = title.lower()
                
                # Signs it might be a facility (not a small home)
                facility_indicators = [
                    'facility', 'center', 'manor', 'village', 'community', 'residence',
                    'towers', 'plaza', 'gardens', 'estates', 'court', 'place'
                ]
                
                # Signs it might be a home
                home_indicators = ['home', 'house', 'care home', 'adult care']
                
                has_facility_indicator = any(indicator in title_lower for indicator in facility_indicators)
                has_home_indicator = any(indicator in title_lower for indicator in home_indicators)
                
                # Decode current WordPress type
                current_wp_type = decode_wordpress_type(type_field)
                
                if has_facility_indicator and not has_home_indicator:
                    if current_wp_type == "Assisted Living Community":
                        facility_vs_community_issues.append({
                            'ID': row.get('ID', ''),
                            'Title': title,
                            'Current_WP_Type': current_wp_type,
                            'Suggested_Type': 'Assisted Living Facility',
                            'Reason': 'Title suggests facility, currently Community',
                            'Senior_Place_URL': senior_place_url
                        })
    
    return facility_vs_community_issues

def decode_wordpress_type(type_field):
    """Decode WordPress serialized type field to readable name"""
    if not type_field or type_field == '0':
        return "Uncategorized"
    
    # Map IDs back to names
    id_to_name = {v: k for k, v in CURRENT_CANONICAL_TO_ID.items()}
    
    try:
        # Extract ID from serialized format like a:1:{i:0;i:162;}
        if 'i:0;i:' in type_field:
            import re
            match = re.search(r'i:0;i:(\d+);', type_field)
            if match:
                type_id = int(match.group(1))
                return id_to_name.get(type_id, f"Unknown ID {type_id}")
        
        return "Unknown format"
    except:
        return "Parse error"

def main():
    print("🔍 Analyzing Care Type Mapping Issues")
    print("=" * 50)
    
    # Check WordPress categories
    print("\n1. Checking WordPress categories...")
    categories = check_wordpress_categories()
    
    # Check if "Assisted Living Facility" exists
    facility_category = None
    for cat in categories:
        if cat['name'] == 'Assisted Living Facility':
            facility_category = cat
            break
    
    if facility_category:
        print(f"\n✅ 'Assisted Living Facility' category exists (ID: {facility_category['id']})")
        CURRENT_CANONICAL_TO_ID["Assisted Living Facility"] = facility_category['id']
    else:
        print(f"\n⚠️  'Assisted Living Facility' category does NOT exist")
        print("   This category needs to be created in WordPress before mapping")
    
    # Analyze current data
    print("\n2. Analyzing current mapping issues...")
    csv_file = "/Users/nicholas/Repos/senior-scrapr/organized_csvs/Listings-Export-2025-August-28-1956.csv"
    
    issues = analyze_current_mapping_issues(csv_file)
    
    if issues:
        print(f"\n📊 Found {len(issues)} potential facility vs community mapping issues:")
        for i, issue in enumerate(issues[:10], 1):  # Show first 10
            print(f"  {i}. {issue['Title']}")
            print(f"     Current: {issue['Current_WP_Type']} → Suggested: {issue['Suggested_Type']}")
            print(f"     Reason: {issue['Reason']}")
            print()
        
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
        
        # Save detailed report
        report_file = "/Users/nicholas/Repos/senior-scrapr/organized_csvs/FACILITY_VS_COMMUNITY_ANALYSIS.csv"
        with open(report_file, 'w', newline='', encoding='utf-8') as f:
            if issues:
                writer = csv.DictWriter(f, fieldnames=issues[0].keys())
                writer.writeheader()
                writer.writerows(issues)
        
        print(f"\n💾 Detailed analysis saved to: {report_file}")
        
    else:
        print("\n✅ No obvious facility vs community mapping issues found")
    
    print("\n3. Next Steps:")
    if not facility_category:
        print("   a. Create 'Assisted Living Facility' category in WordPress")
        print("   b. Get the new category ID") 
    print("   c. Re-scrape Senior Place to get actual care types")
    print("   d. Apply corrected mapping with facility vs community distinction")
    print("   e. Generate corrected CSV for WordPress import")

if __name__ == "__main__":
    main()
