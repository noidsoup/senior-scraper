import asyncio
import json
import csv
import random
import re
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_JSONL = "seniorly_data_resume.jsonl"
OUTPUT_CSV = "seniorly_data_resume.csv"
URL_LIST_FILE = "seniorly_city_urls.txt"
PROCESSED_FILE = "processed_cities.txt"

def load_processed_cities():
    return set(Path(PROCESSED_FILE).read_text().splitlines()) if Path(PROCESSED_FILE).exists() else set()

def mark_city_processed(url):
    with open(PROCESSED_FILE, "a") as f:
        f.write(url + "\n")

def get_scraped_urls():
    if not Path(OUTPUT_JSONL).exists():
        return set()
    with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
        return set(json.loads(line)["url"] for line in f if line.strip())

def normalize_amenities(amenities_list):
    """Lowercase, strip, and deduplicate amenity strings."""
    if not isinstance(amenities_list, list):
        return []
    normalized = set()
    for amenity in amenities_list:
        cleaned = amenity.strip().lower()
        if cleaned:
            normalized.add(cleaned)
    return sorted(normalized)

def save_listing(listing):
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(listing, ensure_ascii=False) + "\n")

    listing_copy = listing.copy()
    listing_copy["type"] = ', '.join(listing_copy["type"])
    listing_copy["photos"] = ', '.join(listing_copy["photos"])
    listing_copy["amenities"] = ', '.join(listing_copy["amenities"])
    fieldnames = ["title", "description", "address", "location-name", "price", "type", "featured_image", "photos", "amenities", "url"]
    is_new = not Path(OUTPUT_CSV).exists()
    with open(OUTPUT_CSV, "a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow(listing_copy)

async def extract_amenities(detail_page, url):
    try:
        await detail_page.goto(url)
        await detail_page.wait_for_selector('#amenities-section', timeout=8000)
        await detail_page.wait_for_function(
            "() => document.querySelectorAll('#amenities-section li div.font-b-m').length > 0", timeout=8000
        )
        amenity_els = await detail_page.query_selector_all('#amenities-section li div.font-b-m')
        raw_amenities = [await el.inner_text() for el in amenity_els if el]
        return normalize_amenities(raw_amenities)
    except Exception as e:
        print(f"⚠️ Failed to extract amenities from {url}: {e}")
        return []

async def scrape_url(city_url, page, detail_page, scraped_urls):
    page_num = 1
    seen_this_city = set()
    pagination_param = "?page-number="

    await page.goto(city_url)
    if not await page.query_selector('#searchTilesContainer'):
        pagination_param = "?page="

    while True:
        page_url = f"{city_url}{pagination_param}{page_num}"
        print(f"\n➡️ Visiting {page_url}")
        try:
            await page.goto(page_url)
            await page.wait_for_selector('#searchTilesContainer', timeout=10000)
        except:
            break

        cards = await page.query_selector_all('#searchTilesContainer article')
        if not cards:
            break

        page_new_urls = set()

        for card in cards:
            try:
                title_el = await card.query_selector('h3.title-small')
                if not title_el:
                    continue
                title = await title_el.inner_text()

                spans = await card.query_selector_all('span.font-b-s')
                address = await spans[0].inner_text() if len(spans) > 0 else ''
                match = re.search(r',\s*([^,]+),\s*[A-Z]{2}', address)
                location_name = match.group(1).strip() if match else ''
                type_text = await spans[1].inner_text() if len(spans) > 1 else ''
                types = [t.strip() for t in type_text.split(',') if t.strip()]

                price_el = await card.query_selector('div.inline.font-t-xs-azo.font-medium')
                price_text = await price_el.inner_text() if price_el else ''
                price_match = re.search(r'\$([\d,]+)', price_text)
                price = int(price_match.group(1).replace(',', '')) if price_match else None

                desc_el = await card.query_selector('div[data-testid="card-description"]')
                description = await desc_el.inner_text() if desc_el else ''

                img_elements = await card.query_selector_all('img[src*="cloudfront.net"]')
                images = list({await img.get_attribute('src') for img in img_elements if await img.get_attribute('src')})
                featured_image = images[0] if images else None
                photos = images[1:] if len(images) > 1 else []

                parent_link = await card.evaluate_handle('el => el.closest("a")')
                href = await parent_link.get_attribute('href') if parent_link else ''
                full_url = f"https://www.seniorly.com{href}" if href else ''
                if not full_url or full_url in scraped_urls or full_url in seen_this_city:
                    continue

                seen_this_city.add(full_url)
                page_new_urls.add(full_url)

                amenities = await extract_amenities(detail_page, full_url)

                save_listing({
                    "title": title,
                    "description": description,
                    "address": address,
                    "location-name": location_name,
                    "price": price,
                    "type": types,
                    "featured_image": featured_image,
                    "photos": photos,
                    "amenities": amenities,
                    "url": full_url
                })

                print(f"✅ {title} - {location_name} (${price if price else 'N/A'})")
                time.sleep(random.uniform(1.0, 2.0))

            except Exception as e:
                print(f"❌ Error scraping card: {e}")

        if not page_new_urls:
            print("🚑 No new listings on this page. Ending pagination.")
            break

        page_num += 1

async def run():
    all_urls = Path(URL_LIST_FILE).read_text().splitlines()
    processed = load_processed_cities()
    scraped_urls = get_scraped_urls()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        detail_page = await context.new_page()

        for url in all_urls:
            if url.strip() == '' or url in processed:
                continue
            print(f"\n--- Starting city: {url} ---")
            await scrape_url(url, page, detail_page, scraped_urls)
            scraped_urls = get_scraped_urls()
            mark_city_processed(url)

        await browser.close()
    print("✅ Scraping completed.")

if __name__ == "__main__":
    asyncio.run(run())
