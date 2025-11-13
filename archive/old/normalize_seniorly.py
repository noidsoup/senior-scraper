import json
import csv
from pathlib import Path

JSONL_PATH = Path("seniorplace_data.jsonl")
CSV_PATH = Path("seniorplace_data_export.csv")

TYPE_COLLAPSE_MAP = {
    "assisted living": "Assisted Living Home",
    "assisted living facility": "Assisted Living Home",
    "assisted living home": "Assisted Living Home",
    "board and care home": "Board And Care Home",
    "memory care": "Memory Care",
    "independent living": "Independent Living",
    "nursing home": "Nursing Home",
    "continuing care retirement community": "Continuing Care Retirement Community",
}

def normalize_types(raw_types):
    collapsed = set()
    for t in raw_types:
        key = t.strip().lower()
        if key in TYPE_COLLAPSE_MAP:
            collapsed.add(TYPE_COLLAPSE_MAP[key])
    return sorted(collapsed)

def clean_entry(entry):
    # Normalize type
    entry["type"] = normalize_types(entry.get("type", []))

    # Clean price
    price = entry.get("price")
    entry["price"] = "" if price is None else price

    # Clean featured image
    if not str(entry.get("featured_image", "")).startswith("http"):
        entry["featured_image"] = ""

    # Clean photos
    entry["photos"] = [p for p in entry.get("photos", []) if p.startswith("http")]

    # Clean amenities
    entry["amenities"] = entry.get("amenities", [])

    return entry

def jsonl_to_csv_and_update():
    entries = []

    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                entry = clean_entry(entry)
                entries.append(entry)
            except json.JSONDecodeError:
                continue

    if not entries:
        print("❌ No valid entries found.")
        return

    # Export to CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title", "description", "address", "location-name",
                "price", "type", "featured_image", "photos", "amenities", "url"
            ],
            quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        for entry in entries:
            # Flatten lists for CSV
            row = entry.copy()
            row["type"] = ", ".join(row.get("type", []))
            row["photos"] = ", ".join(row.get("photos", []))
            row["amenities"] = ", ".join(row.get("amenities", []))
            writer.writerow(row)

    # Overwrite JSONL with cleaned data
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"✅ Cleaned and exported {len(entries)} entries to {CSV_PATH}")
    print(f"✅ Overwrote {JSONL_PATH} with cleaned data")

if __name__ == "__main__":
    jsonl_to_csv_and_update()
