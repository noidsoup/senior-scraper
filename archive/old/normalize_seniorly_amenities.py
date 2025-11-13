import asyncio
import json
import csv
from pathlib import Path
from playwright.async_api import async_playwright

INPUT_JSONL = "seniorly_data_resume.jsonl"
OUTPUT_JSONL = "seniorly_data_updated_amenities.jsonl"
OUTPUT_CSV = "seniorly_data_updated_amenities.csv"

def normalize_amenities(amenities_list):
    if not isinstance(amenities_list, list):
        return []
    normalized = set()
    for amenity in amenities_list:
        cleaned = amenity.strip().lower()
        if cleaned:
            normalized.add(cleaned)
    return sorted(normalized)

async def extract_amenities(page, url):
    try:
        await page.goto(url)
        await page.wait_for_selector('#amenities-section', timeout=8000)
        await page.wait_for_function(
            "() => document.querySelectorAll('#amenities-section li div.font-b-m').length > 0",
            timeout=8000
        )
        amenity_els = await page.query_selector_all('#amenities-section li div.font-b-m')
        raw_amenities = [await el.inner_text() for el in amenity_els if el]
        return normalize_amenities(raw_amenities)
    except Exception as e:
        print(f"⚠️ Could not extract amenities for {url}: {e}")
        return []

async def update_amenities():
    listings = []
    if not Path(INPUT_JSONL).exists():
        print(f"❌ File not found: {INPUT_JSONL}")
        return

    with open(INPUT_JSONL, "r", encoding="utf-8") as infile:
        for line in infile:
            if line.strip():
                try:
                    listings.append(json.loads(line))
                except json.JSONDecodeError:
                    print("⚠️ Skipping invalid JSON line.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for i, listing in enumerate(listings):
            url = listing.get("url")
            if not url:
                continue
            print(f"🔄 ({i + 1}/{len(listings)}) Updating: {listing.get('title', 'Unknown')}")

            new_amenities = await extract_amenities(page, url)
            listing["amenities"] = new_amenities

        await browser.close()

    # Save updated JSONL
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out:
        for listing in listings:
            out.write(json.dumps(listing, ensure_ascii=False) + "\n")

    # Optional CSV export
    fieldnames = ["title", "description", "address", "location-name", "price", "type", "featured_image", "photos", "amenities", "url"]
    with open(OUTPUT_CSV, "w", newline='', encoding="utf-8") as csv_out:
        writer = csv.DictWriter(csv_out, fieldnames=fieldnames)
        writer.writeheader()
        for listing in listings:
            row = listing.copy()
            row["type"] = ", ".join(row["type"]) if isinstance(row["type"], list) else row["type"]
            row["photos"] = ", ".join(row["photos"]) if isinstance(row["photos"], list) else row["photos"]
            row["amenities"] = ", ".join(row["amenities"]) if isinstance(row["amenities"], list) else row["amenities"]
            writer.writerow(row)

    print("✅ Amenities updated and saved.")

if __name__ == "__main__":
    asyncio.run(update_amenities())
