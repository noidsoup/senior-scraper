#!/usr/bin/env python3
"""
Simple duplicate merger - creates a clean dataset without duplicates
"""

import pandas as pd
import sys

def merge_duplicates_simple(csv_path):
    """Merge duplicate records by address"""
    
    # Read the full dataset and duplicates analysis
    print("Reading datasets...")
    df = pd.read_csv(csv_path)
    dupes_df = pd.read_csv('organized_csvs/Listings-Export-2025-August-28-1956_ADDRESS_DUPLICATES_ENHANCED.csv')
    
    print(f"Total listings: {len(df)}")
    print(f"Duplicate listings: {len(dupes_df)}")
    
    # Track which IDs to delete and which to keep
    ids_to_delete = set()
    ids_to_update = {}  # ID -> updated row data
    
    # Group duplicates by normalized address
    address_groups = dupes_df.groupby('Normalized_Address')
    
    print(f"Processing {len(address_groups)} duplicate address groups...")
    
    for addr, group in address_groups:
        # Find Senior Place and Seniorly entries
        seniorplace_entries = group[group['Source'] == 'seniorplace']
        seniorly_entries = group[group['Source'] == 'seniorly']
        
        if len(seniorplace_entries) > 0:
            # Use first Senior Place as primary
            primary_id = seniorplace_entries.iloc[0]['ID']
            primary_row = df[df['ID'] == primary_id].iloc[0].copy()
            
            # Check for Seniorly photos to merge
            for _, seniorly_entry in seniorly_entries.iterrows():
                seniorly_id = seniorly_entry['ID']
                seniorly_row = df[df['ID'] == seniorly_id].iloc[0]
                
                # Merge photos if Seniorly has them and primary doesn't
                if 'photos' in df.columns:
                    if pd.notna(seniorly_row['photos']) and pd.isna(primary_row['photos']):
                        primary_row['photos'] = seniorly_row['photos']
                        print(f"  Merged photos from Seniorly ID {seniorly_id} into Senior Place ID {primary_id}")
            
            # Store the updated primary record
            ids_to_update[primary_id] = primary_row
            
            # Mark all others for deletion
            for _, dup_entry in group.iterrows():
                if dup_entry['ID'] != primary_id:
                    ids_to_delete.add(dup_entry['ID'])
        
        else:
            # No Senior Place entry, keep first Seniorly entry
            primary_id = group.iloc[0]['ID']
            
            # Mark others for deletion
            for _, dup_entry in group.iterrows():
                if dup_entry['ID'] != primary_id:
                    ids_to_delete.add(dup_entry['ID'])
    
    print(f"IDs to delete: {len(ids_to_delete)}")
    print(f"IDs to update: {len(ids_to_update)}")
    
    # Create the final dataset
    print("Creating merged dataset...")
    
    # Remove duplicates
    final_df = df[~df['ID'].isin(ids_to_delete)].copy()
    
    # Update records with merged data
    for record_id, updated_row in ids_to_update.items():
        mask = final_df['ID'] == record_id
        if mask.any():
            # Update each column individually to avoid the length mismatch error
            for col in updated_row.index:
                if col in final_df.columns:
                    final_df.loc[mask, col] = updated_row[col]
    
    print(f"Final dataset: {len(final_df)} listings")
    print(f"Removed {len(df) - len(final_df)} duplicates")
    
    # Save results
    output_file = csv_path.replace('.csv', '_MERGED_NO_DUPLICATES.csv')
    final_df.to_csv(output_file, index=False)
    
    # Save list of deleted IDs
    delete_df = pd.DataFrame({'Deleted_ID': list(ids_to_delete)})
    delete_file = csv_path.replace('.csv', '_DELETED_IDS.csv')
    delete_df.to_csv(delete_file, index=False)
    
    print(f"\\nFiles created:")
    print(f"  Clean dataset: {output_file}")
    print(f"  Deleted IDs: {delete_file}")
    
    return final_df

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 merge_dupes_simple.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    merge_duplicates_simple(csv_file)
