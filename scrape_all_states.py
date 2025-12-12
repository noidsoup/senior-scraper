#!/usr/bin/env python3
"""
Multi-State Senior Place Scraper
Based on the WORKING California scraper approach
Scrapes all pages and filters by state
WITH CHECKPOINT/RESUME SUPPORT
"""

import asyncio
import json
import csv
import re
import argparse
import pickle
import random
from pathlib import Path
import os
from playwright.async_api import async_playwright
from datetime import datetime

# Senior Place credentials from environment
USERNAME = os.getenv("SP_USERNAME")
PASSWORD = os.getenv("SP_PASSWORD")

# Type mapping
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

def normalize_type(types):
    """Normalize care types"""
    normalized = []
    for t in types:
        t = t.strip()
        canonical = TYPE_TO_CANONICAL.get(t, t)
        if canonical not in normalized:
            normalized.append(canonical)
    return sorted(set(normalized))

def normalize_title(title):
    """
    Normalize title to match WordPress format:
    1. Strip business suffixes (LLC, INC, DBA, etc.)
    2. Convert to Title Case
    """
    if not title:
        return title
    
    # Strip common business suffixes
    suffixes = [
        r'\s+LLC\.?$',
        r'\s+L\.L\.C\.?$',
        r'\s+INC\.?$',
        r'\s+INCORPORATED\.?$',
        r'\s+CORP\.?$',
        r'\s+CORPORATION\.?$',
        r'\s+CO\.?$',
        r'\s+LTD\.?$',
        r'\s+LIMITED\.?$',
        r'\s+LP\.?$',
        r'\s+LLP\.?$',
    ]
    
    cleaned = title.strip()
    
    # Strip DBA (Doing Business As) patterns FIRST - removes everything after DBA
    # Handle "LLC Dba Centennial", "DBA Business Name", etc.
    dba_patterns = [
        r'\s+D\.?B\.?A\.?\s+.*$',  # DBA, D.B.A., DBA. followed by business name
        r'\s+D/B/A\s+.*$',         # D/B/A followed by business name
        r'\s+DBA\s+.*$',           # DBA followed by business name
        r'\s+Dba\s+.*$',           # Dba followed by business name (capitalized)
        r'\s+Doing Business As\s+.*$',  # "Doing Business As XYZ" - remove entire phrase
    ]
    
    for pattern in dba_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Then strip common business suffixes
    for suffix in suffixes:
        cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up trailing commas and extra whitespace
    cleaned = re.sub(r',?\s*$', '', cleaned).strip()
    
    # Clean up multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Convert to title case
    # Python's .title() handles most cases well
    cleaned = cleaned.title()
    
    # Fix common issues with title case
    # "Of", "At", "The", "By", etc. should be lowercase unless at start
    words = cleaned.split()
    for i in range(1, len(words)):
        if words[i].lower() in ['of', 'the', 'at', 'by', 'in', 'on', 'for', 'and', 'or']:
            words[i] = words[i].lower()
    
    return ' '.join(words)

async def login(context):
    """Login to Senior Place"""
    if not USERNAME or not PASSWORD:
        raise RuntimeError("Missing SP_USERNAME or SP_PASSWORD environment variables.")
    page = await context.new_page()
    print("🔐 Logging into Senior Place...")
    await page.goto("https://app.seniorplace.com/login")
    await page.wait_for_timeout(2000)
    
    await page.fill('#email', USERNAME)
    await page.fill('#password', PASSWORD)
    await page.click('#signin')
    
    await page.wait_for_selector('text=Communities', timeout=10000)
    print("✅ Successfully logged in\n")
    return page

async def scrape_state(page, state_code, output_file):
    """Scrape all listings for a specific state with checkpoint/resume"""
    
    checkpoint_file = f"{output_file}.checkpoint"
    
    # Check for existing checkpoint
    start_page = 1
    all_listings = []
    
    if Path(checkpoint_file).exists():
        try:
            with open(checkpoint_file, 'rb') as f:
                checkpoint = pickle.load(f)
                start_page = checkpoint['page'] + 1
                all_listings = checkpoint['listings']
            print(f"📂 Resuming {state_code} from page {start_page} (found {len(all_listings)} listings so far)")
        except:
            print(f"⚠️ Checkpoint corrupted, starting fresh")
            start_page = 1
            all_listings = []
    
    # Populate seen_urls from checkpoint to prevent duplicates
    seen_urls_from_checkpoint = {listing['url'] for listing in all_listings}
    
    print(f"🏠 Scraping {state_code} from Senior Place...")
    print("=" * 60)
    
    # Navigate to communities page
    await page.goto("https://app.seniorplace.com/communities")
    await page.wait_for_timeout(3000)

    # Use Location filter with zipcode (simpler and more reliable)
    print(f"🔍 Applying Location filter for {state_code}...")

    # Zipcodes for each state (major city in each state)
    zipcode_map = {
        'AR': '72201',  # Little Rock, AR
        'CT': '06103',  # Hartford, CT
        'WY': '82001',  # Cheyenne, WY
        'AZ': '85001',  # Phoenix, AZ
        'CA': '90001',  # Los Angeles, CA
        'CO': '80201',  # Denver, CO
        'ID': '83701',  # Boise, ID
        'NM': '87101',  # Albuquerque, NM
        'UT': '84101'   # Salt Lake City, UT
    }

    zipcode = zipcode_map.get(state_code)
    if zipcode:
        print(f"📍 Using zipcode {zipcode} for {state_code}")

        try:
            # Wait for page to be ready
            await page.wait_for_selector('button', timeout=10000)
            await page.wait_for_timeout(2000)

            # Find Location button (first button in searchbar)
            searchbar = await page.query_selector('.searchbar-component, form.searchbar-component')
            if searchbar:
                location_btn = await searchbar.query_selector('button:first-of-type')
                if location_btn:
                    await location_btn.click()
                    await page.wait_for_timeout(2000)  # Wait for popover

                    # Select "Zip" from first dropdown
                    first_select = await page.query_selector('select.form-select')
                    if first_select:
                        await first_select.select_option('specificZip')
                        await page.wait_for_timeout(1000)

                    # Enter zipcode
                    zip_input = await page.query_selector('input[placeholder*="Zip"], input[placeholder*="zip"], input[type="text"]')
                    if zip_input:
                        await zip_input.fill(zipcode)
                        await page.wait_for_timeout(1000)

                        # Click Apply
                        apply_btn = await page.query_selector('button:has-text("Apply")')
                        if apply_btn:
                            await apply_btn.click()
                            await page.wait_for_timeout(4000)  # Wait for filter to apply
                            print(f"✅ Filtered to zipcode {zipcode} ({state_code})")
                        else:
                            print(f"⚠️ Could not find Apply button")
                    else:
                        print(f"⚠️ Could not find Zip input field")
                else:
                    print(f"⚠️ Could not find Location button, continuing without filter")
            else:
                print(f"⚠️ Could not find searchbar, continuing without filter")
        except Exception as e:
            print(f"⚠️ Error applying filter: {e}, continuing without filter")
    else:
        print(f"⚠️ No zipcode mapped for {state_code}, skipping filter")
    
    # Skip to resume page if needed
    page_num = 1
    if start_page > 1:
        print(f"⏭️ Skipping to page {start_page}...")
        for _ in range(start_page - 1):
            try:
                next_btn = await page.query_selector('button:has-text("Next")')
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                    page_num += 1
            except:
                break
        print(f"✅ Resumed at page {page_num}")
    
    # Track consecutive empty pages for smart exit
    consecutive_empty_pages = 0
    MAX_EMPTY_PAGES = 100
    
    # Track seen URLs to detect duplicates and pagination loops
    seen_urls = seen_urls_from_checkpoint  # Start with URLs from checkpoint
    consecutive_duplicate_pages = 0
    MAX_DUPLICATE_PAGES = 50  # Stop after 50 consecutive pages with only duplicates
    
    while True:
        print(f"📄 Processing page {page_num}...", end=" ")
        
        try:
            await page.wait_for_selector('div.flex.space-x-6', timeout=10000)
        except:
            print("⚠️ No listings found")
            break
        
        cards = await page.query_selector_all('div.flex.space-x-6')
        
        page_total = 0
        state_count = 0
        new_listings_this_page = 0
        
        for card in cards:
            try:
                # Extract title
                name_el = await card.query_selector("h3 a")
                if not name_el:
                    continue
                    
                title = normalize_title((await name_el.inner_text()).strip())
                
                # Extract URL
                href = await name_el.get_attribute("href")
                url = f"https://app.seniorplace.com{href}"
                
                # Skip if we've already seen this URL (duplicate detection)
                if url in seen_urls:
                    continue
                
                # Extract featured image
                img_el = await card.query_selector("img")
                featured_image = ""
                if img_el:
                    img_src = await img_el.get_attribute("src")
                    if img_src and img_src.startswith("/api/files/"):
                        featured_image = f"https://app.seniorplace.com{img_src}"
                    elif img_src:
                        featured_image = img_src
                
                # Extract care types from card (they're displayed as text elements)
                # Look for the flex container with badge elements
                care_type_badges = await card.query_selector_all('span.inline-block')
                card_types = []
                for badge in care_type_badges:
                    type_text = await badge.inner_text()
                    if type_text:
                        card_types.append(type_text.strip())
                
                types = normalize_type(card_types) if card_types else []
                
                # Extract address
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
                
                page_total += 1
                
                # FILTER for target state
                if state.upper() != state_code.upper():
                    continue
                
                state_count += 1
                
                full_address = f"{street}, {city}, {state} {zip_code}".strip(", ")
                
                listing = {
                    "title": title,
                    "address": full_address,
                    "city": city,
                    "state": state.upper(),
                    "zip": zip_code,
                    "url": url,
                    "featured_image": featured_image,
                    "care_types": ', '.join(types),
                    "care_types_raw": ', '.join(card_types)
                }
                
                all_listings.append(listing)
                seen_urls.add(url)  # Mark as seen
                new_listings_this_page += 1
                
            except Exception as e:
                continue
        
        print(f"Found {state_count} {state_code} listings (out of {page_total} total)")
        
        # Track consecutive duplicate-only pages - stop if pagination is looping
        if new_listings_this_page == 0 and state_count > 0:
            # We found listings for this state, but they were ALL duplicates
            consecutive_duplicate_pages += 1
            if consecutive_duplicate_pages >= MAX_DUPLICATE_PAGES:
                print(f"🛑 Stopping: {MAX_DUPLICATE_PAGES} consecutive pages with only duplicates")
                print(f"   Pagination is looping - all {state_code} listings collected")
                break
        else:
            consecutive_duplicate_pages = 0  # Reset when we find new listings
        
        # Track consecutive empty pages - smart exit if we hit too many
        if state_count == 0:
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= MAX_EMPTY_PAGES:
                print(f"🛑 Stopping: {MAX_EMPTY_PAGES} consecutive pages with 0 {state_code} listings")
                print(f"   Likely exhausted all {state_code} listings in database")
                break
        else:
            consecutive_empty_pages = 0  # Reset counter when we find listings
        
        # Try to go to next page
        try:
            # Look for Next button
            next_btn = await page.query_selector('button:has-text("Next")')
            
            if not next_btn:
                print("📄 No next button found - reached end")
                break
            
            # Just try to click - if it fails or does nothing, we'll hit smart exit anyway
            try:
                await next_btn.click()
                await page.wait_for_timeout(2000)
                page_num += 1
            except:
                print("📄 Failed to click Next - reached end")
                break
            
            # CHECKPOINT every 50 pages
            if page_num % 50 == 0:
                try:
                    checkpoint = {
                        'page': page_num,
                        'listings': all_listings,
                        'timestamp': datetime.now().isoformat()
                    }
                    with open(checkpoint_file, 'wb') as f:
                        pickle.dump(checkpoint, f)
                    print(f"💾 Checkpoint saved at page {page_num} ({len(all_listings)} listings)")
                except Exception as e:
                    print(f"⚠️ Checkpoint save failed: {e}")
            
            # NO SAFETY LIMIT - scrape until Next button is disabled
                
        except Exception as e:
            print(f"⚠️ Pagination done or error: {e}")
            break
    
    # Care types already extracted from cards during pagination
    print(f"\n✅ Collected {len(all_listings)} {state_code} listings with care types from listing cards\n")
    
    # Save to CSV
    if all_listings:
        fieldnames = ['title', 'address', 'city', 'state', 'zip', 'url', 
                     'featured_image', 'care_types', 'care_types_raw']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_listings)
        
        print(f"\n✅ Saved {len(all_listings)} {state_code} listings to: {output_file}")
        
        # Clean up checkpoint file after successful completion
        if Path(checkpoint_file).exists():
            Path(checkpoint_file).unlink()
            print(f"🗑️ Removed checkpoint file (scraping complete)")
    else:
        print(f"\n⚠️ No {state_code} listings found")
    
    return all_listings

async def main():
    parser = argparse.ArgumentParser(description="Scrape Senior Place by state")
    parser.add_argument('--states', nargs='+', default=['AZ', 'CA', 'CO', 'ID', 'NM', 'UT'],
                       help='State codes to scrape (space-separated)')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    print("🚀 MULTI-STATE SENIOR PLACE SCRAPER")
    print("=" * 60)
    print(f"States: {', '.join(args.states)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context()
        
        try:
            page = await login(context)
            
            all_results = {}
            for state in args.states:
                output_file = f"{state}_seniorplace_data_{datetime.now().strftime('%Y%m%d')}.csv"
                listings = await scrape_state(page, state, output_file)
                all_results[state] = len(listings)
                print()
            
            print("=" * 60)
            print("🎉 SCRAPING COMPLETE!")
            print("=" * 60)
            for state, count in all_results.items():
                print(f"  {state}: {count} listings")
            print()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

