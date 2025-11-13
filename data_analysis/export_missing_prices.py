import csv
import argparse
from typing import List, Dict, Optional


def get_price_col(header: List[str]) -> Optional[str]:
    for c in header:
        if c.strip().lower() == "price":
            return c
    return None


def find_url(row: Dict[str, str], needle: str) -> str:
    for k, v in row.items():
        val = (v or "").strip()
        if needle in val:
            return val
    return ""


def export_missing(input_csv: str, output_csv: str) -> int:
    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames or []

    price_col = get_price_col(header)
    if not price_col:
        raise RuntimeError("No 'price' column found in input CSV")

    out_rows: List[Dict[str, str]] = []
    for r in rows:
        price = (r.get(price_col) or "").strip()
        if price == "":
            out_rows.append({
                "ID": r.get("ID", ""),
                "Title": r.get("Title", r.get("title", "")),
                "City": r.get("location-name", r.get("location", "")),
                "State": r.get("States", r.get("state", "")),
                "SeniorPlaceURL": find_url(r, "seniorplace.com/communities/show/"),
                "SeniorlyURL": find_url(r, "seniorly.com"),
                "NormalizedTypes": r.get("normalized_types", ""),
                "NormalizedTypeIDs": r.get("normalized_type_ids", ""),
            })

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ID", "Title", "City", "State", "SeniorPlaceURL", "SeniorlyURL",
            "NormalizedTypes", "NormalizedTypeIDs"
        ])
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)


def main():
    p = argparse.ArgumentParser(description="Export listings with missing price from a CSV")
    p.add_argument("--input", required=True, help="Path to input CSV")
    p.add_argument("--output", required=False, help="Path to output CSV")
    args = p.parse_args()
    out = args.output or (args.input.rsplit('.', 1)[0] + "_missing_prices.csv")
    count = export_missing(args.input, out)
    print(f"Wrote {count} rows → {out}")


if __name__ == "__main__":
    main()


