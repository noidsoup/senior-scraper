import json
import csv
import re
import pandas as pd

SENIORPLACE_FILE = "seniorplace_data.csv"
SENIORLY_FILE = "seniorly_data_resume.jsonl"
OUTPUT_JSONL = "master_listings_rewritten.jsonl"
OUTPUT_CSV = "master_listings_rewritten.csv"

COMMON_SUFFIX_FIXES = {
    r'\bdirve\b': 'drive',
    r'\bdrvie\b': 'drive',
    r'\bstreeet\b': 'street',
    r'\bstrret\b': 'street',
    r'\bctreet\b': 'street',
    r'\bplaec\b': 'place',
    r'\bavneue\b': 'avenue',
    r'\baveneue\b': 'avenue',
    r'\brod\b': 'road',
    r'\bstr\b': 'street',
    r'\bave\b': 'avenue',
}

LEGAL_SUFFIX_REGEX = r'\b(?:llc|l\.l\.c\.|inc|inc\.|corp|corporation|co|ltd|l\.t\.d\.)\b'

SKIP_KEYWORDS = [
    "do not refer", "don’t refer", "does not refer", "won’t work with us",
    "non-payment", "non payment", "closed by state", "closed by the state",
    "does not work with placement", "they don’t work", "they don't work"
]

def normalize_address(address):
    if pd.isna(address):
        return ""
    address = address.lower()
    for bad, good in COMMON_SUFFIX_FIXES.items():
        address = re.sub(bad, good, address)
    return re.sub(r'\W+', '', address)

def fix_featured_image_url(url):
    if pd.isna(url) or not url:
        return ""
    if url.startswith("/api/files/public/"):
        return f"https://app.seniorplace.com{url}"
    return url

def normalize_type_list(types):
    return [
        "Assisted Living Home" if t.strip() == "Assisted Living" else t.strip()
        for t in types
        if isinstance(t, str) and t.strip().lower() not in {"", "null", "none"}
    ]

def safe_type_list(raw):
    if isinstance(raw, list):
        return normalize_type_list(raw)
    if isinstance(raw, str):
        items = [x.strip() for x in raw.split(",") if x.strip()]
        return normalize_type_list(items)
    return []

def clean_title(title):
    if not isinstance(title, str):
        return ""
    cleaned = re.sub(LEGAL_SUFFIX_REGEX, '', title, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,.-]+', '', cleaned)
    return cleaned.strip()

def should_skip(title):
    if not title:
        return False
    title = title.lower()
    return any(keyword in title for keyword in SKIP_KEYWORDS)

def safe_split_list(raw):
    if pd.isna(raw):
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []

def write_outputs(listings):
    fieldnames = [
        "title", "description", "address", "location-name",
        "price", "type", "featured_image", "photos", "amenities", "url"
    ]
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as jf:
        for item in listings:
            jf.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for item in listings:
            row = item.copy()
            row["type"] = ", ".join(row.get("type", []))
            row["photos"] = ", ".join(row.get("photos", []))
            row["amenities"] = ", ".join(row.get("amenities", []))
            writer.writerow(row)

def main():
    crm_df = pd.read_csv(SENIORPLACE_FILE)
    seniorly_df = pd.read_json(SENIORLY_FILE, lines=True)

    crm_df["address_key"] = crm_df["address"].apply(normalize_address)
    seniorly_df["address_key"] = seniorly_df["address"].apply(normalize_address)

    seniorly_index = seniorly_df.drop_duplicates(subset="address_key") \
                                .set_index("address_key") \
                                .to_dict(orient="index")

    seen_keys = set()
    merged = []

    for _, row in crm_df.iterrows():
        key = row["address_key"]
        seniorly = seniorly_index.get(key)
        seen_keys.add(key)

        title = clean_title(seniorly.get("title") if seniorly else row.get("title", ""))
        if should_skip(title):
            continue

        description = seniorly.get("description", "") if seniorly and pd.notna(seniorly.get("description")) else ""
        price = seniorly.get("price") if seniorly and pd.notna(seniorly.get("price")) else row.get("price")

        crm_type = safe_type_list(row.get("type"))
        seniorly_type = safe_type_list(seniorly.get("type")) if seniorly else []

        listing = {
            "title": title,
            "description": description,
            "address": row.get("address", ""),
            "location-name": row.get("location-name", ""),
            "price": price,
            "type": list(set(crm_type + seniorly_type)),
            "featured_image": fix_featured_image_url(row.get("featured_image", "")),
            "photos": safe_split_list(row.get("photos")),
            "amenities": [],
            "url": row.get("url", ""),
        }

        if seniorly:
            listing["photos"] = list(set(listing["photos"] + safe_split_list(seniorly.get("photos"))))
            listing["amenities"] = safe_split_list(seniorly.get("amenities"))

        merged.append(listing)

    # Include unmatched seniorly listings
    for _, row in seniorly_df.iterrows():
        key = row["address_key"]
        if key in seen_keys:
            continue

        title = clean_title(row.get("title", ""))
        if should_skip(title):
            continue

        listing = {
            "title": title,
            "description": row.get("description", ""),
            "address": row.get("address", ""),
            "location-name": row.get("location-name", ""),
            "price": row.get("price", None),
            "type": safe_type_list(row.get("type")),
            "featured_image": fix_featured_image_url(row.get("featured_image", "")),
            "photos": safe_split_list(row.get("photos")),
            "amenities": safe_split_list(row.get("amenities")),
            "url": row.get("url", ""),
        }

        merged.append(listing)

    write_outputs(merged)
    print(f"✅ Wrote {len(merged)} listings to {OUTPUT_JSONL} and {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
