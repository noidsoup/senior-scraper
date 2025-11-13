#!/usr/bin/env python3
"""
Create a CSV with only the records that were actually modified during the merge process
"""

import pandas as pd

def create_update_only_csv():
    print("Creating update-only CSV...")
    
    # Read the clean dataset and true duplicates info
    clean_df = pd.read_csv('organized_csvs/Listings-Export-2025-August-28-1956_NO_TRUE_DUPLICATES.csv')
    true_dupes = pd.read_csv('organized_csvs/TRUE_DUPLICATES_SAME_TITLE_AND_ADDRESS.csv')
    
    # Get the IDs that were kept as primary (the ones that got updated with merged data)
    primary_ids = []
    
    # Group duplicates by facility to find which IDs were kept as primary
    dupe_groups = true_dupes.groupby('Title_Address_Key')
    
    for key, group in dupe_groups:
        # Find Senior Place entries first (they were prioritized)
        seniorplace_entries = group[group['Source'] == 'seniorplace']
        seniorly_entries = group[group['Source'] == 'seniorly']
        
        if len(seniorplace_entries) > 0:
            # Senior Place was kept as primary
            primary_id = seniorplace_entries.iloc[0]['ID']
        elif len(seniorly_entries) > 0:
            # Seniorly was kept as primary (if no Senior Place)
            primary_id = seniorly_entries.iloc[0]['ID']
        else:
            # Other was kept as primary
            primary_id = group.iloc[0]['ID']
        
        primary_ids.append(primary_id)
        print(f"Primary ID {primary_id}: {group.iloc[0]['Title']}")
    
    print(f"\\nFound {len(primary_ids)} records that were updated with merged data")
    
    # Filter the clean dataset to only include the updated records
    updated_records = clean_df[clean_df['ID'].isin(primary_ids)].copy()
    
    print(f"Extracted {len(updated_records)} updated records")
    
    # Save the update-only CSV
    output_file = 'organized_csvs/UPDATE_ONLY_MERGED_RECORDS.csv'
    updated_records.to_csv(output_file, index=False)
    
    print(f"\\nSaved to: {output_file}")
    
    # Show what will be updated
    print(f"\\nThese {len(updated_records)} records contain merged data and should be imported:")
    for _, row in updated_records.iterrows():
        has_photos = 'Yes' if pd.notna(row['photos']) and row['photos'].strip() else 'No'
        has_content = 'Yes' if pd.notna(row['Content']) and row['Content'].strip() else 'No'
        print(f"  ID {row['ID']}: {row['Title'][:50]}... | Photos: {has_photos} | Content: {has_content}")
    
    print(f"\\n✅ IMPORT INSTRUCTIONS:")
    print(f"1. Upload UPDATE_ONLY_MERGED_RECORDS.csv to WP All Import")
    print(f"2. Choose 'Update existing posts'")
    print(f"3. Match by ID field")
    print(f"4. Map photos, Content, and other fields you want to update")
    print(f"5. This will only update the {len(updated_records)} records that actually changed")
    
    return updated_records

if __name__ == "__main__":
    create_update_only_csv()
