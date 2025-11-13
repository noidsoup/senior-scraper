#!/usr/bin/env python3
"""
Create the missing "Assisted Living Facility" category in WordPress
to properly distinguish between facilities and homes.

This addresses the core issue where Senior Place shows:
- Assisted Living Home (small, ≤10 beds)  
- Assisted Living Facility (larger facilities)

But our WordPress only had "Community" and "Home", causing incorrect mapping.
"""

import requests
import json

def create_wordpress_category():
    """Create the Assisted Living Facility category in WordPress"""
    
    # WordPress REST API endpoint for creating categories
    wp_api_url = "https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2/categories"
    
    # Category data
    category_data = {
        "name": "Assisted Living Facility",
        "slug": "assisted-living-facility", 
        "description": "Assisted living facilities - larger care facilities that provide assistance with daily activities"
    }
    
    print("🏗️  Creating 'Assisted Living Facility' category in WordPress...")
    print(f"Category data: {json.dumps(category_data, indent=2)}")
    
    # Note: This requires authentication. For now, just show what needs to be done.
    print("\n⚠️  This requires WordPress admin authentication.")
    print("Manual steps to create the category:")
    print("1. Log into WordPress admin at https://aplaceforseniorscms.kinsta.cloud/wp-admin")
    print("2. Go to Listings → Categories (or Posts → Categories)")
    print("3. Add new category:")
    print(f"   - Name: {category_data['name']}")
    print(f"   - Slug: {category_data['slug']}")
    print(f"   - Description: {category_data['description']}")
    print("4. Note the new category ID for the mapping")
    
    print("\nAlternatively, you can create it via WP-CLI:")
    print(f"wp term create category '{category_data['name']}' --slug='{category_data['slug']}' --description='{category_data['description']}'")
    
    return None  # Would return the new category ID if we had auth

def show_corrected_mapping():
    """Show what the corrected mapping should look like"""
    
    print("\n📋 Corrected Type Mapping (after creating Assisted Living Facility):")
    print("=" * 60)
    
    corrected_mapping = {
        "assisted living facility": "Assisted Living Facility",  # NEW - preserve facility distinction
        "assisted living home": "Assisted Living Home",         # UNCHANGED - small homes
        "independent living": "Independent Living",              # UNCHANGED
        "memory care": "Memory Care",                           # UNCHANGED
        "skilled nursing": "Nursing Home",                      # UNCHANGED
        "continuing care retirement community": "Assisted Living Community",  # UNCHANGED - CCRC as community
        "in-home care": "Home Care",                            # UNCHANGED
        "home health": "Home Care",                             # UNCHANGED
        "hospice": "Home Care",                                 # UNCHANGED
        "respite care": "Assisted Living Community",            # UNCHANGED
    }
    
    for sp_type, cms_type in corrected_mapping.items():
        status = "NEW" if cms_type == "Assisted Living Facility" else "OK"
        print(f"  {sp_type:<40} → {cms_type:<25} [{status}]")
    
    print("\n🎯 This corrected mapping preserves the important distinction between:")
    print("   • Assisted Living Home (small, ≤10 beds)")
    print("   • Assisted Living Facility (larger facilities)")
    print("   • Assisted Living Community (CCRCs and general communities)")

def main():
    print("🔧 Creating Missing WordPress Category")
    print("=" * 50)
    
    # Attempt to create the category
    new_category_id = create_wordpress_category()
    
    # Show the corrected mapping
    show_corrected_mapping()
    
    print("\n📝 After creating the category, update the mapping in these files:")
    files_to_update = [
        "fix_seniorplace_care_types.py",
        "update_prices_from_seniorplace_export.py", 
        "sync_seniorly_from_sp_export.py",
        "search_seniorly_on_seniorplace.py",
        "sync_seniorly_care_types.py"
    ]
    
    for file in files_to_update:
        print(f"   • {file}")
    
    print("\n🚀 Next steps:")
    print("1. Create the 'Assisted Living Facility' category in WordPress")
    print("2. Get the new category ID") 
    print("3. Update TYPE_LABEL_MAP in all scripts with corrected mapping")
    print("4. Re-scrape Senior Place listings to apply correct types")
    print("5. Generate corrected CSV for WordPress import")

if __name__ == "__main__":
    main()
