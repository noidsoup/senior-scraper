#!/usr/bin/env python3
"""
Prepare California listings for WordPress import
Converts California Senior Place data into WordPress All Import compatible format
"""

import csv
import re
from typing import Dict, List

# Type mapping from memory.md
TYPE_TO_CANONICAL = {
    "Assisted Living Home": "Assisted Living Home",
    "Assisted Living Facility": "Assisted Living Community",
    "Assisted Living Community": "Assisted Living Community",
    "Independent Living": "Independent Living",
    "Memory Care": "Memory Care",
    "Skilled Nursing": "Nursing Home",
    "Nursing Home": "Nursing Home",
    "Continuing Care Retirement Community": "Assisted Living Community",
    "In-Home Care": "Home Care",
    "Home Health": "Home Care",
    "Hospice": "Home Care",
    "Home Care": "Home Care",
}

# CMS term IDs from memory.md
CANONICAL_TO_ID = {
    "Assisted Living Community": 5,
    "Assisted Living Home": 162,
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    "Home Care": 488,
}

def normalize_types(type_str: str) -> tuple:
    """
    Convert type string to normalized types and WordPress serialized format
    Returns (normalized_types_str, serialized_type_ids)
    """
    if not type_str:
        return ("", "")
    
    # Parse types (they come as comma-separated or single values)
    types = [t.strip() for t in type_str.split(',')]
    
    # Map to canonical
    canonical_types = []
    for t in types:
        canonical = TYPE_TO_CANONICAL.get(t, t)
        if canonical not in canonical_types:
            canonical_types.append(canonical)
    
    # Get term IDs
    term_ids = [CANONICAL_TO_ID.get(ct) for ct in canonical_types if ct in CANONICAL_TO_ID]
    
    # Create normalized types string
    normalized_types_str = ', '.join(canonical_types)
    
    # Create WordPress serialized array: a:N:{i:0;i:ID1;i:1;i:ID2;}
    if term_ids:
        items = ''.join(f"i:{i};i:{term_ids[i]};" for i in range(len(term_ids)))
        serialized = f"a:{len(term_ids)}:{{{items}}}"
    else:
        serialized = ""
    
    return (normalized_types_str, serialized)

def prepare_california_listing(ca_row: Dict) -> Dict:
    """Convert California row to WordPress import format"""
    
    # Extract care types
    care_type_str = ca_row.get('type', '')
    normalized_types, serialized_types = normalize_types(care_type_str)
    
    # Build WordPress row
    wp_row = {
        # Basic fields
        'Title': ca_row.get('title', ''),
        'Content': ca_row.get('description', ''),  # Will be enriched later
        'Excerpt': '',
        'Post Type': 'listing',
        'Status': 'publish',
        
        # Location fields
        'Locations': ca_row.get('location-name', ''),  # City
        'States': 'California',
        'state': 'California',
        '_state': 'field_682f4d903ba5f',  # ACF field key
        
        # Address
        'address': ca_row.get('address', ''),
        '_address': 'field_6813f255a7266',  # ACF field key
        'location-name': ca_row.get('location-name', ''),
        '_location-name': 'field_682f4d903ba5f',  # ACF field key
        
        # Contact
        'phone': ca_row.get('phone', ''),
        '_phone': 'field_68152ed96a2d0',  # ACF field key
        
        # Website/URLs - Senior Place URL as primary source
        'website': ca_row.get('url', ''),  # Senior Place URL
        '_website': 'field_68152f2303743',  # ACF field key
        'senior_place_url': ca_row.get('url', ''),
        '_senior_place_url': 'field_68af89a6f8692',  # ACF field key
        
        # Seniorly URL (if matched)
        'seniorly_url': ca_row.get('seniorly_url', ''),
        '_seniorly_url': 'field_68af89b8e4cd0',  # ACF field key
        
        # Pricing
        'price': ca_row.get('price', '') or ca_row.get('monthly_base_price', ''),
        '_price': 'field_682e9adea745b',  # ACF field key
        
        # Images
        'Image URL': ca_row.get('featured_image', ''),
        'Image Featured': '1' if ca_row.get('featured_image') else '',
        'photos': ca_row.get('photos', ''),
        '_photos': 'field_68361c6ff3620',  # ACF field key
        
        # Care types
        'type': serialized_types,
        '_type': 'field_682fc481aaf60',  # ACF field key
        'normalized_types': normalized_types,
        
        # Amenities
        'amenities': ca_row.get('amenities', ''),
        '_amenities': 'field_68324d980487e',  # ACF field key
        
        # Template fields
        '_wp_page_template': 'default',
        'Template': 'default',
        'Format': '',
        'Comment Status': 'open',
        'Ping Status': 'open',
    }
    
    # Add all pricing fields if they exist
    pricing_fields = [
        'monthly_base_price', 'price_high_end', 'second_person_fee', 'pet_deposit',
        'al_care_levels_low', 'al_care_levels_high',
        'assisted_living_price_low', 'assisted_living_price_high',
        'assisted_living_1br_price_low', 'assisted_living_1br_price_high',
        'assisted_living_2br_price_low', 'assisted_living_2br_price_high',
        'assisted_living_home_price_low', 'assisted_living_home_price_high',
        'independent_living_price_low', 'independent_living_price_high',
        'independent_living_1br_price_low', 'independent_living_1br_price_high',
        'independent_living_2br_price_low', 'independent_living_2br_price_high',
        'memory_care_price_low', 'memory_care_price_high',
        'accepts_altcs', 'has_medicaid_contract', 'offers_affordable_low_income'
    ]
    
    for field in pricing_fields:
        if field in ca_row:
            wp_row[field] = ca_row.get(field, '')
    
    return wp_row

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare California listings for WordPress")
    parser.add_argument('--input', default='california_seniorplace_data.csv', 
                       help='Input California CSV')
    parser.add_argument('--pricing', default='california_seniorplace_data_with_pricing.csv',
                       help='Optional pricing-enriched CSV (if available)')
    parser.add_argument('--output', default='CALIFORNIA_WP_IMPORT.csv',
                       help='Output WordPress import CSV')
    parser.add_argument('--use-pricing', action='store_true',
                       help='Use pricing-enriched file if it exists')
    
    args = parser.parse_args()
    
    # Determine which input file to use
    import os
    if args.use_pricing and os.path.exists(args.pricing):
        input_file = args.pricing
        print(f"📊 Using pricing-enriched file: {input_file}")
    else:
        input_file = args.input
        print(f"📊 Using base file: {input_file}")
    
    print("🔧 CALIFORNIA WORDPRESS PREPARATION")
    print("=" * 60)
    
    # Read California data
    ca_listings = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ca_listings.append(row)
    
    print(f"📊 Loaded {len(ca_listings)} California listings")
    
    # Convert to WordPress format
    wp_listings = []
    for listing in ca_listings:
        wp_row = prepare_california_listing(listing)
        wp_listings.append(wp_row)
    
    # Get all unique fieldnames
    all_fields = set()
    for listing in wp_listings:
        all_fields.update(listing.keys())
    
    # Define field order (WordPress import prefers certain order)
    priority_fields = [
        'Title', 'Content', 'Excerpt', 'Post Type', 'Status',
        'Locations', 'States', 'state', '_state',
        'address', '_address', 'location-name', '_location-name',
        'phone', '_phone', 'website', '_website',
        'senior_place_url', '_senior_place_url', 'seniorly_url', '_seniorly_url',
        'price', '_price', 'type', '_type', 'normalized_types',
        'Image URL', 'Image Featured', 'photos', '_photos',
        'amenities', '_amenities'
    ]
    
    # Add remaining fields
    remaining_fields = sorted(all_fields - set(priority_fields))
    fieldnames = priority_fields + remaining_fields
    
    # Write WordPress import CSV
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(wp_listings)
    
    print(f"✅ Converted {len(wp_listings)} listings")
    print(f"📄 Output: {args.output}")
    print()
    print("🎉 Ready for WordPress All Import!")

if __name__ == "__main__":
    main()
