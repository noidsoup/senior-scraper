import pandas as pd
from pathlib import Path


def load_base_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    
    # Filter to only Seniorly listings
    seniorly_mask = df['website'].str.contains('seniorly.com', na=False) | df['seniorly_url'].notna()
    df = df[seniorly_mask].copy()
    
    # Keep essential columns plus image columns
    essential_cols = ['ID', 'Title', 'seniorly_url', 'type', 'States', 'Locations']
    image_cols = ['Image Featured', 'Image URL', 'photos', '_photos', 'Attachment URL', 'Image Title', 'Image Caption']
    
    cols_to_keep = essential_cols + image_cols
    existing = [c for c in cols_to_keep if c in df.columns]
    df = df[existing].copy()
    
    # Create URL column from seniorly_url or website
    if 'seniorly_url' in df.columns:
        df['URL'] = df['seniorly_url'].fillna(df.get('website', ''))
    else:
        df['URL'] = df.get('website', '')
    
    return df


def load_progress(csv_path: str) -> pd.DataFrame:
    p = Path(csv_path)
    if p.exists():
        df = pd.read_csv(p)
        # Fix Notes column - convert NaN to empty string and ensure string type
        df['Notes'] = df['Notes'].fillna('').astype(str)
        return df
    return pd.DataFrame(columns=['ID', 'Decision', 'Notes']).astype({'ID': 'int64', 'Decision': 'str', 'Notes': 'str'})


def save_progress(csv_path: str, progress_df: pd.DataFrame) -> None:
    progress_df.to_csv(csv_path, index=False)


def upsert_decision(progress_df: pd.DataFrame, row_id, decision: str, notes: str) -> pd.DataFrame:
    # Ensure notes is a string to avoid dtype warnings
    notes = str(notes) if notes is not None else ''
    
    idx_list = progress_df.index[progress_df['ID'] == row_id].tolist()
    if idx_list:
        idx = idx_list[0]
        progress_df.loc[idx, 'Decision'] = decision
        progress_df.loc[idx, 'Notes'] = notes
    else:
        progress_df = pd.concat(
            [progress_df, pd.DataFrame([{'ID': row_id, 'Decision': decision, 'Notes': notes}])],
            ignore_index=True,
        )
    return progress_df


def export_wp_import(progress_df: pd.DataFrame, base_df: pd.DataFrame) -> pd.DataFrame:
    import re
    
    merged = base_df.merge(progress_df[['ID', 'Decision', 'Notes']], on='ID', how='left')
    corrections = merged[merged['Decision'].isin(['Community', 'Home'])].copy()
    
    def get_normalized_types(row):
        """Parse existing types and update Home/Community while preserving others"""
        original_type = str(row['type'])
        decision = row['Decision']
        
        # Extract all type IDs from serialized WordPress data
        matches = re.findall(r'i:\d+;i:(\d+);', original_type)
        existing_types = list(set(matches))  # Remove duplicates
        
        # Remove Home (162) and Community (5) from existing types
        filtered_types = [t for t in existing_types if t not in ['162', '5']]
        
        # Add the new Home or Community type
        if decision == 'Home':
            filtered_types.append('162')
        else:  # Community
            filtered_types.append('5')
        
        # Create type mappings
        type_map = {
            '162': 'Assisted Living Home',
            '5': 'Assisted Living Community',
            '3': 'Memory Care',
            '6': 'Independent Living',
            '4': 'Nursing Home',
            '7': 'Home Care'
        }
        
        # Build normalized_types string
        normalized_parts = [type_map.get(t, f'Type_{t}') for t in filtered_types]
        return ', '.join(normalized_parts)
    
    # Add the normalized_types column
    corrections['normalized_types'] = corrections.apply(get_normalized_types, axis=1)
    
    # Return all columns for safety
    return corrections


