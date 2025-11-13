import csv
import os
import argparse
from typing import List, Dict


def extract_dash2_listings(export_path: str, output_path: str) -> int:
    """Extract only listings with -2 in their slug from the export."""
    dash2_rows = []
    
    with open(export_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle BOM in ID column
            row_id = str(row.get("ID") or row.get("\ufeffID") or "").strip()
            slug = row.get("Slug", "")
            
            if slug and slug.endswith("-2"):
                # Remove -2 from slug for matching with originals
                original_slug = slug[:-2]
                
                # Keep columns requested by user
                dash2_rows.append({
                    "ID": row_id,
                    "Title": row.get("Title", ""),
                    "seniorplace_url": row.get("senior_place_url", "") or row.get("_senior_place_url", ""),
                    "seniorly_url": row.get("seniorly_url", "") or row.get("_seniorly_url", ""),
                    "seniorplace_types": row.get("seniorplace_types", ""),
                    "normalized_types": row.get("normalized_types", ""),
                    "Slug": original_slug,  # Use slug without -2
                    "Original_Dash2_Slug": slug,  # Keep original -2 slug for reference
                    "Content": row.get("Content", ""),
                    "Permalink": row.get("Permalink", ""),
                    "Status": "publish",
                })
    
    # Write the -2 listings
    fieldnames = ["ID", "Title", "seniorplace_url", "seniorly_url", "seniorplace_types", "normalized_types", "Slug", "Original_Dash2_Slug", "Content", "Permalink", "Status"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in dash2_rows:
            writer.writerow(row)
    
    return len(dash2_rows)


def main():
    parser = argparse.ArgumentParser(description="Extract listings with -2 slugs from export")
    parser.add_argument("--input", help="Path to listings export CSV")
    parser.add_argument("--output", help="Output CSV path")
    args = parser.parse_args()
    
    # Auto-detect latest export if not provided
    if not args.input:
        base_dir = os.path.join(os.path.dirname(__file__), "organized_csvs")
        candidates = []
        for name in os.listdir(base_dir):
            if name.startswith("Listings-Export-") and name.endswith(".csv"):
                full_path = os.path.join(base_dir, name)
                candidates.append((os.path.getmtime(full_path), full_path))
        if not candidates:
            print("Error: No Listings-Export CSV found")
            return
        candidates.sort(reverse=True)
        args.input = candidates[0][1]
    
    if not args.output:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        args.output = os.path.join(os.path.dirname(args.input), f"{base_name}_DASH2_ONLY.csv")
    
    count = extract_dash2_listings(args.input, args.output)
    print(f"Extracted {count} listings with -2 slugs -> {args.output}")


if __name__ == "__main__":
    main()
