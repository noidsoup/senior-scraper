#!/usr/bin/env python3
"""
Merge the 54 true duplicates (same title + same address):
- Keep Senior Place data as primary
- Preserve Seniorly photos (they're usually better)
- Merge any other valuable Seniorly content if Senior Place is missing it
"""

import pandas as pd

def merge_true_duplicates():
    print("Reading datasets...")
    
    # Read the full dataset and true duplicates
    df = pd.read_csv('organized_csvs/Listings-Export-2025-August-28-1956.csv')
    true_dupes = pd.read_csv('organized_csvs/TRUE_DUPLICATES_SAME_TITLE_AND_ADDRESS.csv')
    
    print(f"Total listings: {len(df)}")
    print(f"True duplicates to merge: {len(true_dupes)}")
    
    # Group duplicates by facility (same title + address)
    dupe_groups = true_dupes.groupby('Title_Address_Key')
    
    merged_records = {}  # ID -> updated row data
    ids_to_delete = set()
    
    print(f"\\nProcessing {len(dupe_groups)} duplicate facilities...")
    
    merge_stats = {
        'photos_merged': 0,
        'content_merged': 0,
        'facilities_processed': 0,
        'seniorplace_kept': 0,
        'seniorly_kept': 0
    }
    
    for key, group in dupe_groups:
        merge_stats['facilities_processed'] += 1
        title = group.iloc[0]['Title']
        address = group.iloc[0]['Address']
        
        print(f"\\nProcessing: '{title}' at {address}")
        print(f"  {len(group)} duplicates found")
        
        # Separate Senior Place and Seniorly entries
        seniorplace_entries = group[group['Source'] == 'seniorplace']
        seniorly_entries = group[group['Source'] == 'seniorly']
        other_entries = group[group['Source'] == 'other']
        
        primary_id = None
        primary_row = None
        
        # Priority: Senior Place > Seniorly > Other
        if len(seniorplace_entries) > 0:
            primary_id = seniorplace_entries.iloc[0]['ID']
            merge_stats['seniorplace_kept'] += 1
            print(f"  Primary: Senior Place ID {primary_id}")
        elif len(seniorly_entries) > 0:
            primary_id = seniorly_entries.iloc[0]['ID']
            merge_stats['seniorly_kept'] += 1
            print(f"  Primary: Seniorly ID {primary_id}")
        else:
            primary_id = other_entries.iloc[0]['ID']
            print(f"  Primary: Other ID {primary_id}")
        
        # Get the primary record from the full dataset
        primary_row = df[df['ID'] == primary_id].iloc[0].copy()
        
        # Merge data from other entries (prioritizing Seniorly photos/content)
        for _, entry in group.iterrows():
            if entry['ID'] == primary_id:
                continue  # Skip the primary record
                
            # Get the full record from the main dataset
            source_row = df[df['ID'] == entry['ID']].iloc[0]
            
            # Always prefer Seniorly photos if they exist
            if 'photos' in df.columns:
                if pd.notna(source_row['photos']) and source_row['photos'].strip():
                    if entry['Source'] == 'seniorly':
                        print(f"    Merging Seniorly photos from ID {entry['ID']}")
                        primary_row['photos'] = source_row['photos']
                        merge_stats['photos_merged'] += 1
                    elif pd.isna(primary_row['photos']) or not primary_row['photos'].strip():
                        print(f"    Merging photos from ID {entry['ID']} (primary had none)")
                        primary_row['photos'] = source_row['photos']
                        merge_stats['photos_merged'] += 1
            
            # Merge content if primary is missing it
            if 'Content' in df.columns:
                if pd.notna(source_row['Content']) and source_row['Content'].strip():
                    if pd.isna(primary_row['Content']) or not primary_row['Content'].strip():
                        print(f"    Merging content from ID {entry['ID']}")
                        primary_row['Content'] = source_row['Content']
                        merge_stats['content_merged'] += 1
            
            # Merge price if primary doesn't have it
            if 'price' in df.columns:
                if pd.notna(source_row['price']) and source_row['price']:
                    if pd.isna(primary_row['price']) or not primary_row['price']:
                        print(f"    Merging price from ID {entry['ID']}")
                        primary_row['price'] = source_row['price']
            
            # Mark for deletion
            ids_to_delete.add(entry['ID'])
            print(f"    Marking ID {entry['ID']} for deletion")
        
        # Store the merged record
        merged_records[primary_id] = primary_row
    
    print(f"\\n=== MERGE SUMMARY ===")
    print(f"Facilities processed: {merge_stats['facilities_processed']}")
    print(f"Senior Place kept as primary: {merge_stats['seniorplace_kept']}")
    print(f"Seniorly kept as primary: {merge_stats['seniorly_kept']}")
    print(f"Photos merged: {merge_stats['photos_merged']}")
    print(f"Content merged: {merge_stats['content_merged']}")
    print(f"Records to delete: {len(ids_to_delete)}")
    
    # Create the final dataset
    print(f"\\nCreating merged dataset...")
    
    # Remove duplicates
    final_df = df[~df['ID'].isin(ids_to_delete)].copy()
    
    # Update records with merged data
    for record_id, updated_row in merged_records.items():
        mask = final_df['ID'] == record_id
        if mask.any():
            # Update each column individually
            for col in updated_row.index:
                if col in final_df.columns:
                    final_df.loc[mask, col] = updated_row[col]
    
    print(f"Original dataset: {len(df)} listings")
    print(f"Final dataset: {len(final_df)} listings")
    print(f"Removed {len(df) - len(final_df)} true duplicates")
    
    # Save results
    output_file = 'organized_csvs/Listings-Export-2025-August-28-1956_NO_TRUE_DUPLICATES.csv'
    final_df.to_csv(output_file, index=False)
    
    # Save list of deleted IDs for reference
    delete_df = pd.DataFrame({'Deleted_ID': list(ids_to_delete), 'Reason': 'True duplicate (same title + address)'})
    delete_file = 'organized_csvs/TRUE_DUPLICATES_DELETED_IDS.csv'
    delete_df.to_csv(delete_file, index=False)
    
    print(f"\\nFiles created:")
    print(f"  Clean dataset: {output_file}")
    print(f"  Deleted IDs: {delete_file}")
    
    return final_df

if __name__ == "__main__":
    merge_true_duplicates()
