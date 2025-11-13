#!/usr/bin/env python3
import csv

with open("/Users/nicholas/Repos/senior-scrapr/CORRECTED_Senior_Place_Care_Types_FINAL.csv", 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    
    count = 0
    for row in reader:
        if "15298 W Ventura St" in row.get('Title', ''):
            print(f"Title: {row.get('Title', '')}")
            print(f"normalized_types: {row.get('normalized_types', '')}")
            break
        count += 1
        if count > 10:  # Check first few that have directed care
            title = row.get('Title', '')
            normalized = row.get('normalized_types', '')
            if 'directed care' in row.get('scraped_care_types', '') or 'Assisted Living Home' in normalized:
                print(f"Title: {title}")
                print(f"normalized_types: {normalized}")
                break
