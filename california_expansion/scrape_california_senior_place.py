#!/usr/bin/env python3
"""
California Senior Place Scraper
Based on the existing Senior Place scraping infrastructure, modified to target California listings specifically.
"""

import asyncio
import json
import csv
import re
from pathlib import Path
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Error
from datetime import datetime

# Output files
OUTPUT_JSONL = "california_seniorplace_data.jsonl"
OUTPUT_CSV = "california_seniorplace_data.csv"

# Senior Place credentials - updated
USERNAME = "allison@aplaceforseniors.org"
PASSWORD = "Hugomax2025!"

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
    """Clean and normalize address format"""
    address_clean = address.lower()
    for pattern, replacement in ADDRESS_FIXES.items():
        address_clean = re.sub(pattern, replacement.lower(), address_clean)
    address_clean = re.sub(r"[^\w\s,]", "", address_clean)
    address_clean = re.sub(r"\s+", " ", address_clean)
    return address_clean.title().strip()

def normalize_title(title: str) -> Optional[str]:
    """Clean and normalize facility title, filter out flagged facilities"""
    title_clean = title.lower()
    if any(bad in title_clean for bad in BAD_PHRASES):
        return None
    title_clean = SUFFIX_RE.sub("", title_clean)
    title_clean = re.sub(r"\b([a-z]+)\s+s\b", r"\1's", title_clean)
    title_clean = re.sub(r"[^\w\s]", "", title_clean)
    title_clean = re.sub(r"\s+", " ", title_clean).strip()
    return title_clean.title()

# Type mapping from memory.md - same as WordPress preparation
TYPE_TO_CANONICAL = {
    "Assisted Living Home": "Assisted Living Home",
    "Assisted Living Facility": "Assisted Living Community",
    "Assisted Living Community": "Assisted Living Community",
    "Independent Living": "Independent Living",
    "Memory Care": "Memory Care",
    "Skilled Nursing": "Nursing Home",
    "Nursing Home": "Nursing Home",
    "Continuing Care Retirement Community": "Assisted Living Community",
    "In-Home Care": "Home Care",
    "Home Health": "Home Care",
    "Hospice": "Home Care",
    "Home Care": "Home Care",
}

def normalize_type(types: List[str]) -> List[str]:
    """Normalize care types to match CMS taxonomy using canonical mapping"""
    normalized = []
    for t in types:
        t = t.strip()
        # Map to canonical type
        canonical = TYPE_TO_CANONICAL.get(t, t)
        if canonical not in normalized:
            normalized.append(canonical)
    
    return sorted(set(normalized))

def write_listing_jsonl(listing: Dict):
    """Append listing to JSONL file for incremental processing"""
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(listing, ensure_ascii=False) + "\n")

def write_csv(listings: List[Dict]):
    """Write final CSV output compatible with WordPress import"""
    fieldnames = [
        "title", "description", "address", "location-name", "state",
        "price", "type", "featured_image", "photos", "amenities", "url", "website"
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
    """Login to Senior Place with credentials from memory.md"""
    page = await context.new_page()
    print("🔐 Logging into Senior Place...")
    await page.goto("https://app.seniorplace.com/login")
    
    # Wait for page to load
    await page.wait_for_timeout(2000)
    
    # Check if login form is present
    email_field = await page.query_selector('#email')
    if not email_field:
        print("❌ Email field not found - checking page content...")
        content = await page.content()
        print(f"Page title: {await page.title()}")
        # Take screenshot for debugging
        await page.screenshot(path="login_debug.png")
        raise Exception("Login form not found")
    
    await page.fill('#email', USERNAME)
    await page.fill('#password', PASSWORD)
    await page.click('#signin')
    
    # Wait longer and check for various possible success indicators
    try:
        await page.wait_for_selector('text=Communities', timeout=10000)
        print("✅ Successfully logged in")
    except:
        print("⚠️ 'Communities' text not found, checking for other success indicators...")
        # Check if we're redirected to dashboard or communities page
        current_url = page.url
        print(f"Current URL: {current_url}")
        if 'communities' in current_url or 'dashboard' in current_url:
            print("✅ Login appears successful based on URL")
        else:
            await page.screenshot(path="login_failed.png")
            raise Exception("Login failed - check login_failed.png")
    
    return page


async def scrape_california_communities(page):
    """Scrape all California communities from Senior Place"""
    all_listings = []
    
    # Navigate to communities page
    print("🏠 Navigating to communities page...")
    await page.goto("https://app.seniorplace.com/communities")
    await page.wait_for_timeout(3000)
    
    page_num = 1
    print("🏠 Starting California community scraping...")
    print("=" * 60)

    while True:
        print(f"📄 Processing page {page_num}...")
        await page.wait_for_selector('div.flex.space-x-6')
        cards = await page.query_selector_all('div.flex.space-x-6')
        
        page_listings = 0
        california_listings = 0

        for card in cards:
            try:
                # Extract title
                name_el = await card.query_selector("h3 a")
                if not name_el:
                    continue
                title_raw = await name_el.inner_text()
                title = title_raw.strip().title()
                normalized = normalize_title(title)
                if not normalized:
                    print(f"❌ Skipping flagged title: {title}")
                    continue

                # Extract URL
                href = await name_el.get_attribute("href")
                url = f"https://app.seniorplace.com{href}"

                # Extract featured image
                img_el = await card.query_selector("img")
                featured_image = await img_el.get_attribute("src") if img_el else ""
                if featured_image.startswith("/api/files/"):
                    featured_image = "https://app.seniorplace.com" + featured_image

                # Extract care types from card view - correct selector
                card_types = []
                
                # Look for care type badges - they have rounded-full and colored backgrounds
                type_elements = await card.query_selector_all("span.rounded-full[class*='bg-'], span[class*='rounded-full'][class*='px-3'][class*='py-0.5']")
                
                for el in type_elements:
                    text = await el.inner_text()
                    if text and len(text) < 50:  # Reasonable length for care type
                        card_types.append(text.strip())
                
                print(f"   📋 Raw card types: {card_types}")
                
                types = normalize_type(card_types)
                print(f"   📋 Normalized types: {types}")

                # Extract address and filter for California
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
                
                page_listings += 1
                
                # CALIFORNIA FILTER - only process CA listings
                if state.upper() != "CA":
                    continue
                
                california_listings += 1

                full_address = f"{street}, {city}, {state} {zip_code}".strip(", ")
                full_address = normalize_address(full_address)

                listing = {
                    "title": normalized,
                    "description": "",
                    "address": full_address,
                    "location-name": city,
                    "state": state.upper(),
                    "price": None,
                    "type": types,
                    "featured_image": featured_image or "",
                    "photos": [],
                    "amenities": [],
                    "url": url,
                    "website": url  # Senior Place URL as website
                }
                all_listings.append(listing)
                write_listing_jsonl(listing)
                print(f"✅ CA: {normalized} ({city}, {state})")

            except Exception as e:
                print(f"❌ Error scraping card: {e}")

        print(f"   📊 Page {page_num}: {california_listings} CA listings out of {page_listings} total")
        
        # Try to go to next page
        try:
            next_btn = await page.query_selector('nav[aria-label="Pagination"] button[aria-label="Next"], nav[aria-label="Pagination"] >> text=Next')
            if not next_btn:
                print("📄 No next button found - reached end")
                break
            class_attr = await next_btn.get_attribute("class") or ""
            if "text-gray-300" in class_attr or "bg-gray-100" in class_attr:
                print("📄 Next button disabled - reached end")
                break
            await next_btn.click()
            await page.wait_for_timeout(1500)  # Rate limiting
            page_num += 1
        except Exception as e:
            print(f"⚠️ Pagination error or done: {e}")
            break

    return all_listings

async def run():
    """Main execution function"""
    print("🌟 CALIFORNIA SENIOR PLACE SCRAPER")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Clear previous JSONL file
    if Path(OUTPUT_JSONL).exists():
        Path(OUTPUT_JSONL).unlink()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        context = await browser.new_context()
        try:
            page = await login(context)
            listings = await scrape_california_communities(page)
        finally:
            await browser.close()
            
    print()
    print("📁 Writing final CSV...")
    write_csv(listings)
    
    print()
    print("🎉 SCRAPING COMPLETE!")
    print("=" * 60)
    print(f"✅ Scraped {len(listings)} California listings")
    print(f"📄 JSONL: {OUTPUT_JSONL}")
    print(f"📊 CSV: {OUTPUT_CSV}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(run())
