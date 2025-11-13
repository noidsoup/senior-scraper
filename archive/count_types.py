import pandas as pd

# Read the cleaned CSV
file = 'Listings-Export-2025-June-26-2013-cleaned.csv'
df = pd.read_csv(file, dtype=str)

# Count the number of listings per type
counts = df['type'].value_counts(dropna=False)

print('Type counts in cleaned CSV:')
print(counts) 