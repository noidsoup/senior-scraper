#!/usr/bin/env python3
"""
Create WordPress import CSV with corrected classifications for Seniorly listings.

This will create an import file that can be used with WP All Import to update
the care type classifications for listings that were historically mislabeled.

Focus on HIGH CONFIDENCE classifications to avoid introducing errors.
"""

import pandas as pd
import sys
from pathlib import Path

def create_wp_import_file():
    """
    Create WordPress import file with corrected care type classifications
    """
    print("🔄 CREATING WORDPRESS IMPORT WITH CORRECTED CLASSIFICATIONS")
    print("=" * 60)
    
    # Load classification results
    homes_file = 'seniorly_classified_as_HOMES.csv'
    communities_file = 'seniorly_classified_as_COMMUNITIES.csv'
    
    if not Path(homes_file).exists() or not Path(communities_file).exists():
        print("❌ Classification files not found. Run improve_seniorly_classification.py first.")
        return
    
    homes_df = pd.read_csv(homes_file)
    communities_df = pd.read_csv(communities_file)
    
    print(f"📊 Loaded classifications:")
    print(f"  Homes: {len(homes_df)}")
    print(f"  Communities: {len(communities_df)}")
    
    # Filter for HIGH CONFIDENCE only to avoid errors
    high_conf_homes = homes_df[homes_df['confidence'] == 'High'].copy()
    high_conf_communities = communities_df[communities_df['confidence'] == 'High'].copy()
    
    print(f"\n🎯 High confidence classifications:")
    print(f"  High confidence homes: {len(high_conf_homes)}")
    print(f"  High confidence communities: {len(high_conf_communities)}")
    
    # Prepare WordPress import data
    import_records = []
    
    # Process homes (change from current "Assisted Living Home" ID 162 to... wait, they're already 162)
    # The issue is they should be "Assisted Living Home" but many are probably mislabeled as communities
    # Let me check what the current type IDs mean
    
    print(f"\n🔍 ANALYZING CURRENT TYPE IDs:")
    
    # Check current types in homes
    current_home_types = high_conf_homes['Current_Type'].value_counts()
    print(f"Current types for HIGH CONFIDENCE HOMES:")
    for type_val, count in current_home_types.items():
        print(f"  {type_val}: {count}")
    
    # Check current types in communities  
    current_community_types = high_conf_communities['Current_Type'].value_counts()
    print(f"\\nCurrent types for HIGH CONFIDENCE COMMUNITIES:")
    for type_val, count in current_community_types.items():
        print(f"  {type_val}: {count}")
    
    # From memory.md, the type IDs are:
    # - Assisted Living Community = 5
    # - Assisted Living Home = 162
    
    # Create import records for communities that need to be changed from Home (162) to Community (5)
    communities_to_fix = high_conf_communities[
        high_conf_communities['Current_Type'].str.contains('162', na=False)
    ].copy()
    
    print(f"\\n🔄 COMMUNITIES TO FIX (currently labeled as homes):")
    print(f"  Count: {len(communities_to_fix)}")
    
    for _, row in communities_to_fix.iterrows():
        import_records.append({
            'ID': row['ID'],
            'Title': row['Title'],
            'Current_Classification': 'Assisted Living Home (162)',
            'New_Classification': 'Assisted Living Community (5)', 
            'Confidence': row['confidence'],
            'Score': row['score'],
            'Reasons': row['reasons'],
            'new_type_id': '5',  # Assisted Living Community
            'new_normalized_types': 'Assisted Living Community'
        })
    
    # Create import records for homes that might be mislabeled as communities
    homes_to_fix = high_conf_homes[
        ~high_conf_homes['Current_Type'].str.contains('162', na=False)
    ].copy()
    
    print(f"\\n🔄 HOMES TO FIX (currently labeled as communities):")
    print(f"  Count: {len(homes_to_fix)}")
    
    for _, row in homes_to_fix.iterrows():
        import_records.append({
            'ID': row['ID'],
            'Title': row['Title'],
            'Current_Classification': 'Other (not 162)',
            'New_Classification': 'Assisted Living Home (162)',
            'Confidence': row['confidence'], 
            'Score': row['score'],
            'Reasons': row['reasons'],
            'new_type_id': '162',  # Assisted Living Home
            'new_normalized_types': 'Assisted Living Home'
        })
    
    if not import_records:
        print("✅ No high-confidence corrections needed - classifications appear to already be correct!")
        return
    
    # Create import DataFrame
    import_df = pd.DataFrame(import_records)
    
    # Create WordPress-compatible import file
    wp_import_df = pd.DataFrame({
        'ID': import_df['ID'],
        'type': import_df['new_type_id'],  # This will update the type taxonomy 
        'normalized_types': import_df['new_normalized_types'],
        '_type': import_df['new_type_id'],  # Update the meta field too
        'classification_confidence': import_df['Confidence'],
        'classification_score': import_df['Score'],
        'correction_reason': import_df['Reasons']
    })
    
    # Export files
    corrections_file = 'SENIORLY_CARE_TYPE_CORRECTIONS.csv'
    wp_import_file = 'WP_IMPORT_seniorly_care_type_corrections.csv'
    
    import_df.to_csv(corrections_file, index=False)
    wp_import_df.to_csv(wp_import_file, index=False)
    
    print(f"\\n💾 EXPORT COMPLETE:")
    print(f"  Analysis file: {corrections_file} ({len(import_df)} corrections)")
    print(f"  WordPress import file: {wp_import_file}")
    
    # Show summary of changes
    print(f"\\n📊 SUMMARY OF CORRECTIONS:")
    changes_summary = import_df.groupby(['Current_Classification', 'New_Classification']).size()
    for (current, new), count in changes_summary.items():
        print(f"  {current} → {new}: {count} listings")
    
    # Show examples
    print(f"\\n🔍 EXAMPLES OF CORRECTIONS:")
    for i, row in import_df.head(10).iterrows():
        print(f"  {row['Title'][:50]:<50} | {row['Current_Classification']} → {row['New_Classification']}")
    
    print(f"\\n🎯 NEXT STEPS:")
    print(f"1. Review {corrections_file} to verify corrections look accurate")
    print(f"2. Import {wp_import_file} using WP All Import")
    print(f"3. Map 'type' field to Type taxonomy, 'normalized_types' to display field")
    print(f"4. Verify changes on frontend - communities should now show as 'Assisted Living Community'")
    
    return len(import_records)

if __name__ == "__main__":
    corrections_count = create_wp_import_file()
    if corrections_count:
        print(f"\\n✅ Created import file with {corrections_count} high-confidence corrections")
    else:
        print("\\n✅ No corrections needed - classifications already look good!")
