#!/usr/bin/env python3
"""
Create the corrections CSV using the Senior Place export vs WordPress comparison
"""

import csv
from datetime import datetime

def create_corrections():
    print('🔍 CREATING CORRECTIONS CSV FROM SENIOR PLACE EXPORT')
    print('=' * 60)

    # Load Senior Place data
    sp_data = {}
    with open('organized_csvs/seniorplace_data_export.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get('title', '').strip().lower()
            sp_type = row.get('type', '')
            url = row.get('url', '')
            
            if sp_type and url:
                sp_data[title] = {
                    'type': sp_type,
                    'url': url
                }

    print(f'📊 Loaded {len(sp_data)} Senior Place listings')

    # Canonical mapping
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

    def map_sp_types_to_canonical(sp_types_str):
        if not sp_types_str:
            return []
        
        # Handle comma-separated types
        sp_types = [t.strip() for t in sp_types_str.split(',')]
        mapped = []
        
        for sp_type in sp_types:
            sp_lower = sp_type.lower()
            if sp_lower in CANONICAL_MAPPING:
                canonical = CANONICAL_MAPPING[sp_lower]
                if canonical not in mapped:
                    mapped.append(canonical)
        
        return mapped

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

    # Compare with WordPress data and collect mismatches
    mismatches = []
    all_rows = []

    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        original_fieldnames = reader.fieldnames
        
        for row in reader:
            wp_title = row.get('Title', '').strip('"').lower()
            wp_type = decode_wp_type(row.get('type', ''))
            wp_id = row.get('ID', '')
            
            # Try to find matching Senior Place listing
            sp_match = None
            for sp_title, sp_data_item in sp_data.items():
                # Fuzzy match - check if titles are similar
                if wp_title in sp_title or sp_title in wp_title:
                    sp_match = sp_data_item
                    break
            
            correction_applied = False
            
            if sp_match:
                # Found match - compare types
                sp_canonical_types = map_sp_types_to_canonical(sp_match['type'])
                
                if sp_canonical_types:
                    # Take primary type (first one) 
                    should_be_type = sp_canonical_types[0]
                    
                    if wp_type != should_be_type:
                        # MISMATCH - apply correction
                        correct_type_field = generate_wp_type_field(sp_canonical_types)
                        row['type'] = correct_type_field
                        
                        mismatches.append({
                            'ID': wp_id,
                            'Title': row.get('Title', '').strip('"'),
                            'WordPress_Type': wp_type,
                            'Senior_Place_Types': sp_match['type'],
                            'Should_Be_Type': should_be_type,
                            'Corrected_Normalized_Types': ', '.join(sp_canonical_types)
                        })
                        
                        correction_applied = True
            
            # Add tracking columns
            if correction_applied:
                row['correction_applied'] = 'Yes'
                row['corrected_care_types'] = ', '.join(sp_canonical_types)
                row['correction_reason'] = f"Updated from '{wp_type}' to '{should_be_type}' based on Senior Place data"
            else:
                row['correction_applied'] = 'No'
                row['corrected_care_types'] = ''
                row['correction_reason'] = ''
            
            all_rows.append(row)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save mismatch analysis
    if mismatches:
        analysis_file = f"organized_csvs/CARE_TYPE_MISMATCHES_ANALYSIS_{timestamp}.csv"
        with open(analysis_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=mismatches[0].keys())
            writer.writeheader()
            writer.writerows(mismatches)
        
        print(f"💾 Mismatch analysis saved: {analysis_file}")
    
    # Save corrected WordPress import file
    correction_file = f"organized_csvs/WORDPRESS_CORRECTED_CARE_TYPES_{timestamp}.csv"
    
    # Add new columns to fieldnames
    extended_fieldnames = list(original_fieldnames) + ['correction_applied', 'corrected_care_types', 'correction_reason']
    
    with open(correction_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=extended_fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    
    print(f"💾 WordPress correction file saved: {correction_file}")
    
    # Print summary
    print(f"\n🎯 CORRECTION SUMMARY:")
    print(f"  Total mismatches corrected: {len(mismatches)}")
    print(f"  Correction file ready for WordPress import")
    
    if len(mismatches) > 0:
        print(f"\n🚀 NEXT STEPS:")
        print(f"1. Review: {analysis_file}")
        print(f"2. Import: {correction_file}")
        print(f"3. Use WP All Import with ID matching to update care types")
        
        print(f"\n📊 Sample corrections:")
        for i, mismatch in enumerate(mismatches[:5], 1):
            print(f"  {i}. {mismatch['Title']}")
            print(f"     {mismatch['WordPress_Type']} → {mismatch['Should_Be_Type']}")

if __name__ == "__main__":
    create_corrections()
