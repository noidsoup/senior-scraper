#!/usr/bin/env python3
"""
Convert California city descriptions to WordPress taxonomy import format.

This script takes the city descriptions CSV and converts it to a format
that can be imported into WordPress via WP All Import to create location
taxonomy terms with descriptions.
"""

import csv
import os
from typing import Dict, List
import re

def clean_city_name(city: str) -> str:
    """Clean city name for use as taxonomy term"""
    # Remove extra spaces and normalize
    cleaned = city.strip()
    # Handle special cases like "Los Angeles" -> "los-angeles"
    # Remove special characters but keep spaces and hyphens
    cleaned = re.sub(r'[^a-zA-Z0-9\s-]', '', cleaned)
    # Replace spaces with hyphens and remove multiple spaces
    cleaned = re.sub(r'\s+', '-', cleaned)
    # Remove multiple hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip('-')
    return cleaned.lower()

def create_taxonomy_csv(input_file: str, output_file: str, include_state: bool = False):
    """Convert city descriptions CSV to WordPress taxonomy import format"""

    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return False

    print(f"📍 Converting California city descriptions to WordPress taxonomy format")
    print(f"📁 Input: {input_file}")
    print(f"📁 Output: {output_file}")
    if include_state:
        print("🌎 Including state in taxonomy structure")
    print("-" * 60)

    cities_data = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            city_name = row['City'].strip()
            state = row['State'].strip()
            description = row['Description'].strip()

            # Clean the data
            if include_state:
                # Create hierarchical structure: State > City
                taxonomy_name = f"location-{state.lower()}"  # Correct WordPress taxonomy name
                parent_slug = state.lower()
                city_slug = clean_city_name(city_name)
                full_name = f"{city_name}, {state}"
            else:
                taxonomy_name = 'location'  # Correct WordPress taxonomy name
                parent_slug = ''
                city_slug = clean_city_name(city_name)
                full_name = city_name

            cities_data.append({
                'name': full_name,
                'slug': city_slug,
                'description': description,
                'taxonomy': taxonomy_name,
                'parent': parent_slug if include_state else ''
            })

    print(f"📊 Processing {len(cities_data)} cities...")

    # Write taxonomy import CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        # WP All Import taxonomy format
        fieldnames = ['taxonomy', 'parent', 'name', 'slug', 'description']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for city in cities_data:
            writer.writerow({
                'taxonomy': city['taxonomy'],
                'parent': city['parent'],
                'name': city['name'],
                'slug': city['slug'],
                'description': city['description']
            })

    print(f"✅ Successfully created taxonomy import CSV")
    print(f"📊 {len(cities_data)} location terms ready for import")
    print(f"🎯 Next step: Import {output_file} via WP All Import")
    print("   - Set 'Post Type' to 'Taxonomies'")
    print("   - Map 'taxonomy' to 'Taxonomy'")
    print("   - Map 'parent' to 'Parent'")
    print("   - Map 'name' to 'Term Name'")
    print("   - Map 'slug' to 'Term Slug'")
    print("   - Map 'description' to 'Term Description'")

    return True

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Convert California city descriptions to WordPress taxonomy import format")
    parser.add_argument('--input', default='california_city_descriptions_final.csv',
                       help='Input city descriptions CSV file')
    parser.add_argument('--output', default='CALIFORNIA_LOCATIONS_TAXONOMY_IMPORT.csv',
                       help='Output WordPress taxonomy import CSV')
    parser.add_argument('--hierarchical', action='store_true',
                       help='Create hierarchical taxonomy with state as parent')

    args = parser.parse_args()

    # Create flat version (default)
    flat_output = args.output.replace('.csv', '_FLAT.csv') if args.hierarchical else args.output
    success1 = create_taxonomy_csv(args.input, flat_output, include_state=False)

    # Create hierarchical version if requested
    if args.hierarchical:
        hierarchical_output = args.output
        success2 = create_taxonomy_csv(args.input, hierarchical_output, include_state=True)
        success = success1 and success2
    else:
        success = success1

    if success:
        print(f"\n🎉 Ready for WordPress import!")
        if args.hierarchical:
            print(f"📁 Flat taxonomy: {flat_output}")
            print(f"📁 Hierarchical taxonomy: {hierarchical_output}")
        else:
            print(f"📁 Flat taxonomy: {flat_output}")

        print(f"\n📋 WordPress Import Instructions:")
        print(f"1. Go to WP All Import → New Import")
        print(f"2. Upload the generated CSV file")
        print(f"3. Set 'Post Type' to 'Taxonomies'")
        print(f"4. Map the columns as shown above")
        print(f"5. Run the import")
    else:
        print(f"\n❌ Failed to create taxonomy import file")

if __name__ == "__main__":
    main()
