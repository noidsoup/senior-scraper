import pandas as pd

# File paths
original_file = 'Listings-Export-2025-June-26-2013.csv'
cleaned_file = 'Listings-Export-2025-June-26-2013-cleaned.csv'
output_file = 'type_changes_to_uncategorized.csv'

# Read both CSVs
orig = pd.read_csv(original_file, dtype=str)
clean = pd.read_csv(cleaned_file, dtype=str)

# Merge on ID (assuming 'ID' is the unique identifier)
merged = pd.merge(orig, clean, on='ID', suffixes=('_old', '_new'))

# Find rows where type changed from something else to 'Uncategorized'
changed = merged[(merged['type_old'].str.strip().str.lower() != 'uncategorized') &
                 (merged['type_new'].str.strip().str.lower() == 'uncategorized')]

# Output relevant columns
out = changed[['ID', 'Title_old', 'type_old', 'type_new']]
out.columns = ['ID', 'Title', 'Old Type', 'New Type']
out.to_csv(output_file, index=False)

print(f"Done! Output saved to {output_file}") 