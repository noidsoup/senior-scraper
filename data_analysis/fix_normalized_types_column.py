#!/usr/bin/env python3
"""
Fix the scraped_care_types column to be normalized_types with proper Capital Case formatting
"""

import csv

# Our mapping from Senior Place to CMS categories
TYPE_LABEL_MAP = {
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

def normalize_types_string(scraped_types_str: str) -> str:
    """Convert scraped types to normalized Capital Case CMS categories"""
    
    if not scraped_types_str or scraped_types_str in ['None found', 'N/A (not Senior Place)']:
        return scraped_types_str
    
    # Split the scraped types
    scraped_types = [t.strip().lower() for t in scraped_types_str.split(',')]
    
    # Map to CMS categories
    normalized = []
    for sp_type in scraped_types:
        if sp_type in TYPE_LABEL_MAP:
            cms_type = TYPE_LABEL_MAP[sp_type]
            if cms_type not in normalized:
                normalized.append(cms_type)
    
    return ', '.join(normalized) if normalized else 'Uncategorized'

def fix_normalized_types():
    """Fix the column name and format"""
    
    input_file = "/Users/nicholas/Repos/senior-scrapr/CORRECTED_Senior_Place_Care_Types.csv"
    output_file = "/Users/nicholas/Repos/senior-scrapr/CORRECTED_Senior_Place_Care_Types_FINAL.csv"
    
    print("🔧 FIXING NORMALIZED TYPES COLUMN")
    print("=" * 50)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        # Replace scraped_care_types with normalized_types in headers
        new_headers = []
        for header in headers:
            if header == 'scraped_care_types':
                new_headers.append('normalized_types')
            else:
                new_headers.append(header)
        
        rows = []
        senior_place_count = 0
        normalized_count = 0
        
        for row in reader:
            # Rename the column and normalize the content
            if 'scraped_care_types' in row:
                scraped_types = row['scraped_care_types']
                
                # Check if this is a Senior Place listing
                if 'seniorplace.com' in row.get('website', '').lower():
                    senior_place_count += 1
                    normalized_types = normalize_types_string(scraped_types)
                    if normalized_types and normalized_types not in ['None found', 'Uncategorized']:
                        normalized_count += 1
                else:
                    # For non-Senior Place, keep as is
                    normalized_types = scraped_types
                
                # Update the row
                row['normalized_types'] = normalized_types
                del row['scraped_care_types']
            
            rows.append(row)
    
    # Write the corrected file
    print("💾 Writing corrected file...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=new_headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ COMPLETED!")
    print(f"📁 Output: {output_file}")
    print(f"📊 Senior Place listings: {senior_place_count:,}")
    print(f"📊 Successfully normalized: {normalized_count:,}")
    print(f"📊 Success rate: {normalized_count/senior_place_count*100:.1f}%")
    
    # Show sample of the normalized types
    print(f"\n🔍 SAMPLE NORMALIZED TYPES:")
    sample_count = 0
    for row in rows:
        if row.get('normalized_types') and row['normalized_types'] not in ['None found', 'N/A (not Senior Place)', 'Uncategorized']:
            sample_count += 1
            if sample_count <= 5:
                title = row.get('Title', '')[:30]
                normalized = row.get('normalized_types', '')
                print(f"  {sample_count}. {title}: {normalized}")
            if sample_count >= 5:
                break

if __name__ == "__main__":
    fix_normalized_types()
