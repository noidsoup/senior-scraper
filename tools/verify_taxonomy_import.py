#!/usr/bin/env python3
"""
Verify the California locations taxonomy import files are correctly formatted.
"""

import csv
import os

def verify_taxonomy_file(file_path, expected_taxonomy=None):
    """Verify a taxonomy import CSV file"""
    print(f"🔍 Verifying: {file_path}")

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Check header
        expected_headers = ['taxonomy', 'parent', 'name', 'slug', 'description']
        actual_headers = reader.fieldnames

        if actual_headers != expected_headers:
            print(f"❌ Header mismatch. Expected: {expected_headers}, Got: {actual_headers}")
            return False

        print(f"✅ Correct CSV headers: {actual_headers}")

        # Check content
        rows = list(reader)
        print(f"📊 Contains {len(rows)} taxonomy terms")

        # Check taxonomy names
        taxonomies = set(row['taxonomy'] for row in rows)
        print(f"🏷️  Taxonomies: {sorted(taxonomies)}")

        if expected_taxonomy and taxonomies != {expected_taxonomy}:
            print(f"⚠️  Expected taxonomy: {expected_taxonomy}, Found: {taxonomies}")

        # Check for empty fields
        empty_count = 0
        for row in rows:
            if not row['name'] or not row['slug'] or not row['description']:
                empty_count += 1

        if empty_count > 0:
            print(f"⚠️  Found {empty_count} rows with empty required fields")
        else:
            print("✅ All rows have required fields populated")

        # Show sample
        if rows:
            print("📝 Sample entry:")
            sample = rows[0]
            print(f"   Name: {sample['name']}")
            print(f"   Slug: {sample['slug']}")
            print(f"   Description: {sample['description'][:100]}...")

        print()
        return True

def main():
    """Verify both taxonomy files"""
    print("🔍 CALIFORNIA LOCATIONS TAXONOMY VERIFICATION")
    print("=" * 50)

    # Check flat version
    flat_file = "CALIFORNIA_LOCATIONS_TAXONOMY_IMPORT_FLAT.csv"
    hierarchical_file = "CALIFORNIA_LOCATIONS_TAXONOMY_IMPORT.csv"

    success1 = verify_taxonomy_file(flat_file, "location")
    success2 = verify_taxonomy_file(hierarchical_file, "location-ca")

    if success1 and success2:
        print("🎉 All taxonomy files verified successfully!")
        print("\n📋 Ready for WordPress import:")
        print(f"   - Flat: {flat_file}")
        print(f"   - Hierarchical: {hierarchical_file}")
    else:
        print("❌ Some verification checks failed")

if __name__ == "__main__":
    main()
