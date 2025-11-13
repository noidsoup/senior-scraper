#!/usr/bin/env python3
"""
Merge address duplicate records:
- Senior Place data takes priority
- Keep Seniorly photos if available
- Delete the duplicate entries
"""

import pandas as pd
import sys

def merge_duplicates(csv_path):
    """Merge duplicate records by address"""
    
    # Read the full dataset
    print("Reading full dataset...")
    df = pd.read_csv(csv_path)
    print(f"Total listings: {len(df)}")
    
    # Read the duplicates analysis
    dupes_df = pd.read_csv('organized_csvs/Listings-Export-2025-August-28-1956_ADDRESS_DUPLICATES_ENHANCED.csv')
    
    # Group duplicates by normalized address
    address_groups = dupes_df.groupby('Normalized_Address')
    
    merged_records = []
    ids_to_delete = []
    
    print(f"\nProcessing {len(address_groups)} duplicate address groups...")
    
    for addr, group in address_groups:
        print(f"\nProcessing address: {group.iloc[0]['Address']}")
        print(f"  {len(group)} duplicates found")
        
        # Find Senior Place and Seniorly entries
        seniorplace_entries = group[group['Source'] == 'seniorplace']
        seniorly_entries = group[group['Source'] == 'seniorly']
        
        if len(seniorplace_entries) > 0:
            # Use Senior Place as primary
            primary_id = seniorplace_entries.iloc[0]['ID']
            primary_row = df[df['ID'] == primary_id].iloc[0].copy()
            
            print(f"  Primary (Senior Place): ID {primary_id} - {primary_row['Title']}")
            
            # Check if there's a Seniorly entry with photos
            seniorly_photos = ""
            for _, seniorly_entry in seniorly_entries.iterrows():
                seniorly_id = seniorly_entry['ID']
                seniorly_row = df[df['ID'] == seniorly_id].iloc[0]
                
                # Check for photos field
                if 'photos' in df.columns and pd.notna(seniorly_row['photos']):
                    seniorly_photos = seniorly_row['photos']
                    print(f"  Found Seniorly photos from ID {seniorly_id}")
                    break
            
            # Update primary record with Seniorly photos if found
            if seniorly_photos and ('photos' in df.columns):
                primary_row['photos'] = seniorly_photos
                print(f"  Updated primary record with Seniorly photos")
            
            merged_records.append(primary_row)
            
            # Mark other entries for deletion
            for _, dup_entry in group.iterrows():
                if dup_entry['ID'] != primary_id:
                    ids_to_delete.append(dup_entry['ID'])
                    print(f"  Marking for deletion: ID {dup_entry['ID']} - {dup_entry['Title']}")
        
        else:
            # No Senior Place entry, keep the first Seniorly entry
            primary_id = group.iloc[0]['ID']
            primary_row = df[df['ID'] == primary_id].iloc[0].copy()
            print(f"  Primary (Seniorly only): ID {primary_id} - {primary_row['Title']}")
            
            merged_records.append(primary_row)
            
            # Mark other entries for deletion
            for _, dup_entry in group.iterrows():
                if dup_entry['ID'] != primary_id:
                    ids_to_delete.append(dup_entry['ID'])
                    print(f"  Marking for deletion: ID {dup_entry['ID']} - {dup_entry['Title']}")
    
    print(f"\nSummary:")
    print(f"  Merged groups: {len(address_groups)}")
    print(f"  Records to keep/update: {len(merged_records)}")
    print(f"  Records to delete: {len(ids_to_delete)}")
    
    # Create the final dataset
    print(f"\nCreating merged dataset...")
    
    # Start with all records except the ones to delete
    final_df = df[~df['ID'].isin(ids_to_delete)].copy()
    
    # Update the merged records
    for merged_record in merged_records:
        record_id = merged_record['ID']
        final_df.loc[final_df['ID'] == record_id] = merged_record
    
    print(f"Final dataset: {len(final_df)} listings (removed {len(df) - len(final_df)} duplicates)")
    
    # Save results
    output_file = csv_path.replace('.csv', '_MERGED_DUPLICATES.csv')
    final_df.to_csv(output_file, index=False)
    
    # Save deletion list for reference
    delete_df = pd.DataFrame({'ID': ids_to_delete})
    delete_file = csv_path.replace('.csv', '_DELETED_DUPLICATES.csv')
    delete_df.to_csv(delete_file, index=False)
    
    print(f"\nFiles created:")
    print(f"  Merged dataset: {output_file}")
    print(f"  Deleted IDs: {delete_file}")
    
    return final_df, ids_to_delete

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 merge_address_duplicates.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    merge_duplicates(csv_file)
