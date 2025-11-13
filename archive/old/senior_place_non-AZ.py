import asyncio
import json
import csv
import re
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Error

OUTPUT_JSONL = "seniorplace_data_non_az.jsonl"
OUTPUT_CSV = "seniorplace_data_non_az.csv"

BAD_PHRASES = [
    "do not refer", "don't refer", "they did not pay", "they don't pay",
    "avoid", "blacklist", "unlicensed", "flagged", "non compliant",
    "closed", "no agency fee"
]

SUFFIX_RE = re.compile(
    r"(,)?\s*(l[\s\.]*l[\s\.]*c[\s\.]*|inc[\s\.]*|corporation|corp[\s\.]*|ltd[\s\.]*)\s*$",
    re.IGNORECASE
)

ADDRESS_FIXES = {
    r"\bdirve\b": "Drive",
    r"\bdr\b\.?": "Drive",
    r"\bst\b\.?": "Street",
    r"\brd\b\.?": "Road",
    r"\bave\b\.?": "Avenue",
    r"\bln\b\.?": "Lane",
    r"\bpkwy\b\.?": "Parkway",
    r"\bblvd\b\.?": "Boulevard",
    r"\bhwy\b\.?": "Highway",
}

def normalize_address(address: str) -> str:
    address_clean = address.lower()
    for pattern, replacement in ADDRESS_FIXES.items():
        address_clean = re.sub(pattern, replacement.lower(), address_clean)
    address_clean = re.sub(r"[^\w\s,]", "", address_clean)
    address_clean = re.sub(r"\s+", " ", address_clean)
    return address_clean.title().strip()

def normalize_title(title: str) -> Optional[str]:
    title_clean = title.lower()
    if any(bad in title_clean for bad in BAD_PHRASES):
        return None
    title_clean = SUFFIX_RE.sub("", title_clean)
    title_clean = re.sub(r"\b([a-z]+)\s+s\b", r"\1's", title_clean)
    title_clean = re.sub(r"[^\w\s]", "", title_clean)
    title_clean = re.sub(r"\s+", " ", title_clean).strip()
    return title_clean.title()

def normalize_type(types: list[str]) -> list[str]:
    normalized = []
    for t in types:
        t = t.lower().strip()
        if "assisted care facility" in t:
            normalized.append("Assisted Care Home")
        elif "assisted living facility" in t:
            normalized.append("Assisted Living Home")
        else:
            normalized.append(t.title())
    return sorted(set(normalized))

def write_listing_jsonl(listing):
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(listing, ensure_ascii=False) + "\n")

def write_csv(listings):
    fieldnames = [
        "title", "description", "address", "location-name",
        "price", "type", "featured_image", "photos", "amenities", "url"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in listings:
            row = item.copy()
            row["type"] = ", ".join(item.get("type", []))
            row["photos"] = ", ".join(item.get("photos", []))
            row["amenities"] = ", ".join(item.get("amenities", []))
            row["price"] = "" if row["price"] is None else row["price"]
            writer.writerow(row)

async def login(context):
    page = await context.new_page()
    await page.goto("https://app.seniorplace.com/login")
    await page.fill('#email', "allison@aplaceforseniors.org")
    await page.fill('#password', "Hugomax2023!")
    await page.click('#signin')
    await page.wait_for_selector('text=Communities')
    return page

async def scrape_communities(page):
    all_listings = []
    await page.goto("https://app.seniorplace.com/communities")
    page_num = 1

    while True:
        await page.wait_for_selector('div.flex.space-x-6')
        cards = await page.query_selector_all('div.flex.space-x-6')

        for card in cards:
            try:
                name_el = await card.query_selector("h3 a")
                if not name_el:
                    continue
                title_raw = await name_el.inner_text()
                title = title_raw.strip().title()
                normalized = normalize_title(title)
                if not normalized:
                    print(f"❌ Skipping flagged title: {title}")
                    continue

                href = await name_el.get_attribute("href")
                url = f"https://app.seniorplace.com{href}"

                img_el = await card.query_selector("img")
                featured_image = await img_el.get_attribute("src") if img_el else ""
                if featured_image.startswith("/api/files/"):
                    featured_image = "https://app.seniorplace.com" + featured_image

                tag_elements = await card.query_selector_all("span.text-sm.font-medium")
                types = [await tag.inner_text() for tag in tag_elements if tag]
                types = normalize_type(types)

                address_lines = await card.query_selector_all("div.flex-1 > div > div > div")
                if len(address_lines) < 2:
                    continue
                street = await address_lines[0].inner_text()
                citystatezip = await address_lines[1].inner_text()
                if "," not in citystatezip:
                    continue
                city_part, state_zip_part = citystatezip.rsplit(",", 1)
                city = city_part.strip()
                parts = state_zip_part.strip().split()
                if len(parts) < 1:
                    continue
                state = parts[0]
                zip_code = parts[1] if len(parts) > 1 else ""
                if state.upper() == "AZ":
                    continue

                full_address = f"{street}, {city}, {state} {zip_code}".strip(", ")
                full_address = normalize_address(full_address)

                listing = {
                    "title": normalized,
                    "description": "",
                    "address": full_address,
                    "location-name": city,
                    "price": None,
                    "type": types,
                    "featured_image": featured_image or "",
                    "photos": [],
                    "amenities": [],
                    "url": url
                }
                all_listings.append(listing)
                write_listing_jsonl(listing)
                print(f"✅ Scraped: {normalized}")

            except Exception as e:
                print(f"❌ Error scraping card: {e}")

        try:
            next_btn = await page.query_selector('nav[aria-label="Pagination"] button[aria-label="Next"], nav[aria-label="Pagination"] >> text=Next')
            if not next_btn:
                break
            class_attr = await next_btn.get_attribute("class") or ""
            if "text-gray-300" in class_attr or "bg-gray-100" in class_attr:
                break
            await next_btn.click()
            await page.wait_for_timeout(1500)
            page_num += 1
        except Exception as e:
            print(f"⚠️ Pagination error or done: {e}")
            break

    return all_listings

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        try:
            page = await login(context)
            listings = await scrape_communities(page)
        finally:
            await browser.close()
            print("📁 Writing final CSV...")
            write_csv(listings)
            print(f"✅ Wrote {len(listings)} listings to {OUTPUT_CSV}")

if __name__ == "__main__":
    asyncio.run(run())
