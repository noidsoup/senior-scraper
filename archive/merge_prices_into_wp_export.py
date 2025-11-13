import csv
import argparse
from typing import Dict, List, Tuple


def normalize_key(value: str) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def row_key(row: Dict[str, str]) -> Tuple[str, str]:
    """Return a canonical join key tuple for a WP row.
    Priority: Slug → Permalink → ID → website (Senior Place URL) → URL.
    We return a (key_type, key_value) tuple to reduce collisions.
    """
    # Try Slug
    slug = row.get("Slug") or row.get("slug")
    if slug:
        return ("slug", normalize_key(slug))

    # Permalink
    permalink = row.get("Permalink") or row.get("permalink")
    if permalink:
        return ("permalink", normalize_key(permalink))

    # ID
    _id = row.get("ID") or row.get("id")
    if _id:
        return ("id", normalize_key(str(_id)))

    # website (often holds Senior Place URL in our exports)
    website = row.get("website") or row.get("_website") or row.get("URL") or row.get("Url")
    if website:
        return ("url", normalize_key(website))

    # Fallback: title
    title = row.get("Title") or row.get("title")
    if title:
        return ("title", normalize_key(title))

    return ("", "")


def build_index(rows: List[Dict[str, str]]) -> Dict[Tuple[str, str], Dict[str, str]]:
    index: Dict[Tuple[str, str], Dict[str, str]] = {}
    for r in rows:
        k = row_key(r)
        if k[1]:
            # Last one wins; acceptable for our use case
            index[k] = r
    return index


def collect_finance_columns(rows: List[Dict[str, str]]) -> List[str]:
    """Collect finance-related columns present in enriched rows.
    Always include 'price' if present to ensure updates propagate.
    """
    wanted_prefixes = {
        "monthly_base_price",
        "price_high_end",
        "second_person_fee",
        "pet_deposit",
        "al_care_levels_low",
        "al_care_levels_high",
        "assisted_living_price_low",
        "assisted_living_price_high",
        "assisted_living_1br_price_low",
        "assisted_living_1br_price_high",
        "assisted_living_2br_price_low",
        "assisted_living_2br_price_high",
        "assisted_living_home_price_low",
        "assisted_living_home_price_high",
        "independent_living_price_low",
        "independent_living_price_high",
        "independent_living_1br_price_low",
        "independent_living_1br_price_high",
        "independent_living_2br_price_low",
        "independent_living_2br_price_high",
        "memory_care_price_low",
        "memory_care_price_high",
        "accepts_altcs",
        "has_medicaid_contract",
        "offers_affordable_low_income",
        "community_fee_notes",
        "other_pricing_notes",
        "accepted_spend_down_periods",
        "price",
    }
    cols: List[str] = []
    for r in rows:
        for c in r.keys():
            if c in wanted_prefixes:
                if c not in cols:
                    cols.append(c)
    return cols


def merge(wp_export_csv: str, enriched_csv: str, output_csv: str) -> None:
    # Load enriched data
    with open(enriched_csv, newline="", encoding="utf-8") as f:
        enr_reader = csv.DictReader(f)
        enr_rows = list(enr_reader)

    finance_cols = collect_finance_columns(enr_rows)
    enr_index = build_index(enr_rows)

    # Load WP export
    with open(wp_export_csv, newline="", encoding="utf-8") as f:
        wp_reader = csv.DictReader(f)
        wp_rows = list(wp_reader)
        wp_header = wp_reader.fieldnames or []

    # Ensure finance columns exist in output header
    out_header = list(wp_header)
    for col in finance_cols:
        if col not in out_header:
            out_header.append(col)

    # Merge
    updated_count = 0
    for r in wp_rows:
        k = row_key(r)
        if not k[1]:
            continue
        src = enr_index.get(k)
        if not src:
            continue
        # Copy finance fields
        for col in finance_cols:
            val = src.get(col, "")
            if val is None:
                val = ""
            # Only update when non-empty to avoid clobbering existing data
            if str(val).strip() != "":
                r[col] = val
        # Backfill generic price if present in enriched
        if (not r.get("price") or str(r.get("price")).strip() == "") and src.get("monthly_base_price"):
            r["price"] = src["monthly_base_price"]
        updated_count += 1

    # Write
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_header)
        writer.writeheader()
        for r in wp_rows:
            writer.writerow(r)

    print(f"Merged finance fields into {updated_count} rows → {output_csv}")


def main():
    parser = argparse.ArgumentParser(description="Merge enriched prices/finance fields into a WP All Export CSV.")
    parser.add_argument("--wp-export", required=True, help="Path to WP All Export CSV to update.")
    parser.add_argument("--enriched", required=False, default="Listings_Export_2025_June_26_2013_cleaned_with_prices.csv", help="Path to enriched CSV containing finance columns.")
    parser.add_argument("--output", required=False, default="wp_export_with_finances.csv", help="Output CSV path.")
    args = parser.parse_args()

    merge(args.wp_export, args.enriched, args.output)


if __name__ == "__main__":
    main()


