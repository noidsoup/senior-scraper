import pandas as pd
import re

# Mapping from code to readable type name
code_to_type = {
    162: "Assisted Living Home",
    5: "Board and Care Home",
    6: "Independent Living",
    3: "Memory Care",
    7: "Nursing Home",
    1: "Uncategorized"
}
allowed_types = set(code_to_type.values())

# Function to convert serialized/coded type to readable name(s)
def type_to_names(val):
    # If already a readable name, just return it (and check if allowed)
    if str(val).strip() in allowed_types:
        return str(val).strip()
    # If it's a serialized array, extract codes and map to names
    codes = [int(x) for x in re.findall(r'i:(\d+)', str(val))]
    names = [code_to_type.get(code, None) for code in codes if code in code_to_type and code != 1]
    # Only keep allowed types, ignore 'Uncategorized' unless nothing else
    names = [n for n in names if n in allowed_types and n != "Uncategorized"]
    if names:
        return ', '.join(sorted(set(names)))
    return "Uncategorized"

input_file = 'Listings-Export-2025-June-26-2013.csv'
output_file = 'Listings-Export-2025-June-26-2013-cleaned.csv'
chunksize = 10000

reader = pd.read_csv(input_file, chunksize=chunksize)
with open(output_file, 'w', encoding='utf-8', newline='') as f_out:
    for i, chunk in enumerate(reader):
        chunk['type'] = chunk['type'].apply(type_to_names)
        # Map 'Assisted Living' to 'Assisted Living Home' after initial cleaning
        chunk['type'] = chunk['type'].replace('Assisted Living', 'Assisted Living Home')
        # Clean amenities: remove 'about the chef' and any serialized array like 'a:18:{...}'
        if 'amenities' in chunk.columns:
            def clean_amenities(val):
                if pd.isna(val):
                    return val
                # Remove serialized array
                if isinstance(val, str) and val.strip().startswith('a:'):
                    return ''
                # Remove 'about the chef' from comma- or semicolon-separated lists
                items = [x.strip() for x in re.split(r'[;,]', str(val)) if x.strip().lower() != 'about the chef']
                return ', '.join(items) if items else ''
            chunk['amenities'] = chunk['amenities'].apply(clean_amenities)
        if i == 0:
            chunk.to_csv(f_out, index=False)
        else:
            chunk.to_csv(f_out, index=False, header=False)

print(f"Done! Cleaned file saved as {output_file}")