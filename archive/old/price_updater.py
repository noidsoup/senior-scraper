import asyncio
import json
import csv
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright

INPUT_FILE = "seniorplace_data.jsonl"
OUTPUT_FILE = "seniorplace_data.jsonl"
EXPORT_CSV = "seniorplace_data_export.csv"

PRICE_SELECTOR = 'div[data-testid="communityPricing"] > div'

async def extract_price(page, url: str) -> Optional[int]:
    try:
        await page.goto(url, timeout=15000)
        price_el = await page.query_selector(PRICE_SELECTOR)
        if price_el:
            text = await price_el.inner_text()
            if "$" in text:
                return int(''.join(filter(str.isdigit, text.split('/')[0])))
    except Exception as e:
        print(f"❌ Failed on {url}: {e}")
    return None

async def update_prices():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        listings = [json.loads(line) for line in f if line.strip()]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for listing in listings:
            url = listing.get("url", "")
            if "seniorly.com" in url:
                print(f"🔍 Scraping price for: {listing['title']}")
                price = await extract_price(page, url)
                if price:
                    listing["price"] = price
                    print(f"✅ Updated price: ${price}")
                else:
                    print("⚠️ Price not found.")
                await page.wait_for_timeout(1000)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for listing in listings:
            f.write(json.dumps(listing, ensure_ascii=False) + "\n")

    with open(EXPORT_CSV, "w", newline="", encoding="utf-8") as f:
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
    asyncio.run(update_prices())
