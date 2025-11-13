#!/usr/bin/env python3

import csv

print("🔍 Testing CSV reading...")

# Read the CSV
with open('california_seniorplace_data_DEDUPED.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"📊 Found {len(rows)} rows")

# Check first few rows
for i in range(3):
    row = rows[i]
    print(f"\n📋 Row {i+1}:")
    print(f"  Title: {row['title']}")
    print(f"  Type: {row['type']}")
    print(f"  State: {row['state']}")
    print(f"  URL: {row['url']}")

print("\n✅ CSV reading test complete")
