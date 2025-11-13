import csv
import os


def test_and_extract_dash2():
    """Test-first approach: verify fields exist, then extract properly."""
    export_path = '/Users/nicholas/Repos/senior-scrapr/organized_csvs/Listings-Export-2025-August-28-1956.csv'
    
    print("Testing export structure...")
    with open(export_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames)
        
        # Test for expected fields
        required_fields = ['Slug', 'Title', 'Content']
        optional_fields = ['senior_place_url', '_senior_place_url', 'seniorly_url', '_seniorly_url']
        
        print("Required fields check:")
        for field in required_fields:
            exists = field in headers or f'\ufeff{field}' in headers
            print(f"  {field}: {'✓' if exists else '✗'}")
        
        print("Optional fields available:")
        for field in optional_fields:
            if field in headers:
                print(f"  {field}: ✓")
        
        # Test first dash-2 row
        dash2_rows = []
        for row in reader:
            # Handle BOM
            row_id = str(row.get('ID') or row.get('\ufeffID') or '').strip()
            slug = row.get('Slug', '')
            
            if slug and slug.endswith('-2'):
                original_slug = slug[:-2]
                
                # Extract available fields only
                extracted = {
                    'ID': row_id,
                    'Title': row.get('Title', ''),
                    'seniorplace_url': row.get('senior_place_url', '') or row.get('_senior_place_url', ''),
                    'seniorly_url': row.get('seniorly_url', '') or row.get('_seniorly_url', ''),
                    'Slug': original_slug,
                    'Original_Dash2_Slug': slug,
                    'Content': row.get('Content', ''),
                    'Permalink': row.get('Permalink', ''),
                }
                
                dash2_rows.append(extracted)
                
                if len(dash2_rows) == 1:
                    print(f"\nFirst -2 row test:")
                    print(f"  Original slug: {slug} → {original_slug}")
                    print(f"  Has content: {bool(extracted['Content'].strip())}")
                    print(f"  Senior place URL: {extracted['seniorplace_url'][:50]}...")
                    print(f"  Seniorly URL: {extracted['seniorly_url'][:50]}...")
    
    print(f"\nFound {len(dash2_rows)} -2 listings")
    
    # Write output
    output_path = '/Users/nicholas/Repos/senior-scrapr/organized_csvs/DASH2_FOR_CONTENT_IMPORT_FIXED.csv'
    fieldnames = ['ID', 'Title', 'seniorplace_url', 'seniorly_url', 'Slug', 'Original_Dash2_Slug', 'Content', 'Permalink']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in dash2_rows:
            writer.writerow({k: row.get(k, '') for k in fieldnames})
    
    print(f"Wrote {len(dash2_rows)} rows to {output_path}")
    return output_path


if __name__ == '__main__':
    test_and_extract_dash2()
