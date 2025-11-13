import json
import csv
from urllib.parse import quote

INPUT_FILE = "seniorplace_data.jsonl"
OUTPUT_FILE = "seniorplace_data.jsonl"
CSV_EXPORT_FILE = "seniorplace_data_export.csv"

def encode_google_maps_image(url: str) -> str:
    if "maps.googleapis.com" not in url or "location=" not in url:
        return url
    try:
        base, query = url.split("location=", 1)
        location, rest = query.split("&", 1)
        location_encoded = quote(location)
        return f"{base}location={location_encoded}&{rest}"
    except Exception:
        return url

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        listings = [json.loads(line) for line in f if line.strip()]

    for listing in listings:
        featured = listing.get("featured_image", "")
        listing["featured_image"] = encode_google_maps_image(featured)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for listing in listings:
            f.write(json.dumps(listing, ensure_ascii=False) + "\n")

    with open(CSV_EXPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "title", "description", "address", "location-name",
            "price", "type", "featured_image", "url"
        ])
        for l in listings:
            writer.writerow([
                l.get("title", ""),
                l.get("description", ""),
                l.get("address", ""),
                l.get("location-name", ""),
                l.get("price", ""),
                ", ".join(l.get("type", [])),
                l.get("featured_image", ""),
                l.get("url", "")
            ])

if __name__ == "__main__":
    main()
