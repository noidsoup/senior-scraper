#!/usr/bin/env python3
"""
Fix normalized_types column to show existing CMS categories for non-Senior Place listings
"""

import csv

# WordPress term ID to CMS category mapping
ID_TO_CATEGORY = {
    "1": "Uncategorized",
    "3": "Memory Care", 
    "5": "Assisted Living Community",
    "6": "Independent Living",
    "7": "Nursing Home",
    "162": "Assisted Living Home",
    "488": "Home Care",
}

def decode_wordpress_type(type_field: str) -> str:
    """Decode WordPress serialized type field to readable categories"""
    
    if not type_field or type_field.strip() == '':
        return "Uncategorized"
    
    # Handle serialized format like a:1:{i:0;i:162;} or a:2:{i:0;i:162;i:1;i:3;}
    try:
        categories = []
        
        # Extract IDs from serialized format
        import re
        id_matches = re.findall(r'i:\d+;i:(\d+);', type_field)
        
        for term_id in id_matches:
            if term_id in ID_TO_CATEGORY:
                category = ID_TO_CATEGORY[term_id]
                if category not in categories:
                    categories.append(category)
        
        return ', '.join(categories) if categories else "Uncategorized"
        
    except:
        return "Uncategorized"

def fix_normalized_types_for_all():
    """Fix normalized_types to show existing CMS categories for all listings"""
    
    input_file = "/Users/nicholas/Repos/senior-scrapr/CORRECTED_Senior_Place_Care_Types_FINAL.csv"
    output_file = "/Users/nicholas/Repos/senior-scrapr/CORRECTED_Senior_Place_Care_Types_FINAL_FIXED.csv"
    
    print("🔧 FIXING NORMALIZED TYPES FOR ALL LISTINGS")
    print("=" * 50)
    
    updated_count = 0
    senior_place_count = 0
    seniorly_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        rows = []
        for row in reader:
            website = row.get('website', '').strip()
            current_normalized = row.get('normalized_types', '')
            
            if 'seniorplace.com' in website.lower():
                # Senior Place listing - keep existing normalized_types as-is
                senior_place_count += 1
                
            elif current_normalized == 'N/A (not Senior Place)':
                # Non-Senior Place listing - decode existing type field
                type_field = row.get('type', '')
                decoded_categories = decode_wordpress_type(type_field)
                row['normalized_types'] = decoded_categories
                updated_count += 1
                
                # Count Seniorly listings
                if 'seniorly.com' in row.get('seniorly_url', '').lower():
                    seniorly_count += 1
            
            rows.append(row)
    
    # Write the fixed file
    print("💾 Writing fixed file...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✅ COMPLETED!")
    print(f"📁 Output: {output_file}")
    print(f"📊 Senior Place listings: {senior_place_count:,} (kept as-is)")
    print(f"📊 Non-Senior Place updated: {updated_count:,}")
    print(f"📊 Seniorly listings: {seniorly_count:,}")
    
    # Show samples
    print(f"\n🔍 SAMPLE UPDATED LISTINGS:")
    sample_count = 0
    for row in rows:
        normalized = row.get('normalized_types', '')
        seniorly_url = row.get('seniorly_url', '')
        
        if seniorly_url and 'seniorly.com' in seniorly_url and normalized not in ['N/A (not Senior Place)', '']:
            sample_count += 1
            if sample_count <= 3:
                title = row.get('Title', '')[:40]
                print(f"  {sample_count}. {title}")
                print(f"     normalized_types: {normalized}")
                print(f"     seniorly_url: ✅")
            if sample_count >= 3:
                break

if __name__ == "__main__":
    fix_normalized_types_for_all()
