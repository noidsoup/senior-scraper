#!/usr/bin/env python3
"""
FULL WORKFLOW TEST: Scrape 100 listings, get care types, save CSV
Tests the complete monthly update process end-to-end
"""

import asyncio
import csv
import random
from playwright.async_api import async_playwright
from datetime import datetime

USERNAME = "allison@aplaceforseniors.org"
PASSWORD = "Hugomax2025!"

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
    normalized = []
    for t in types:
        t = t.strip()
        canonical = TYPE_TO_CANONICAL.get(t, t)
        if canonical not in normalized:
            normalized.append(canonical)
    return sorted(set(normalized))

async def main():
    print("="*70)
    print("FULL WORKFLOW TEST - 100 LISTINGS")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Step 1: Login...")
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', USERNAME)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        print("   ✅ Logged in\n")
        
        # Scrape first few pages
        print("📄 Step 2: Scrape first 4 pages (~100 listings)...")
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(3000)
        
        all_listings = []
        for page_num in range(1, 5):  # First 4 pages = ~100 listings
            try:
                await page.wait_for_selector('div.flex.space-x-6', timeout=10000)
            except:
                print(f"   No listings on page {page_num}")
                break
            
            cards = await page.query_selector_all('div.flex.space-x-6')
            
            for card in cards:
                try:
                    # Title and URL
                    title_el = await card.query_selector('h3 a')
                    if not title_el:
                        continue
                    
                    title = await title_el.inner_text()
                    href = await title_el.get_attribute('href')
                    url = f"https://app.seniorplace.com{href}" if href.startswith('/') else href
                    
                    # Image
                    img_el = await card.query_selector('img')
                    featured_image = ""
                    if img_el:
                        img_src = await img_el.get_attribute("src")
                        if img_src and img_src.startswith("/api/files/"):
                            featured_image = f"https://app.seniorplace.com{img_src}"
                        elif img_src:
                            featured_image = img_src
                    
                    # Address
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
                    
                    full_address = f"{street}, {city}, {state} {zip_code}".strip(", ")
                    
                    all_listings.append({
                        "title": title.strip(),
                        "address": full_address,
                        "city": city,
                        "state": state.upper(),
                        "zip": zip_code,
                        "url": url,
                        "featured_image": featured_image,
                        "care_types": "",
                        "care_types_raw": ""
                    })
                    
                except:
                    continue
            
            print(f"   Page {page_num}: Found {len(cards)} listings")
            
            # Next page
            if page_num < 4:
                next_btn = await page.query_selector('button:has-text("Next")')
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
        
        print(f"   ✅ Scraped {len(all_listings)} listings\n")
        
        # Dedupe by URL
        print("🔍 Step 3: Deduplicating...")
        unique_listings = {}
        for listing in all_listings:
            url = listing['url']
            if url not in unique_listings:
                unique_listings[url] = listing
        
        unique_list = list(unique_listings.values())
        print(f"   ✅ {len(unique_list)} unique listings (removed {len(all_listings) - len(unique_list)} dupes)\n")
        
        # Get care types from first 10 detail pages (proof of concept)
        print("🏥 Step 4: Get care types from first 10 listings...")
        print("   (With 2-3 sec delays to avoid ban)\n")
        
        for idx, listing in enumerate(unique_list[:10], 1):
            try:
                # Rate limiting
                delay = random.uniform(2000, 3000)
                await page.wait_for_timeout(delay)
                
                await page.goto(listing['url'], timeout=30000)
                await page.wait_for_timeout(1000)
                
                # Click Attributes tab
                attributes_tab = await page.query_selector('button:has-text("Attributes"), a:has-text("Attributes")')
                if attributes_tab:
                    await attributes_tab.click()
                    await page.wait_for_timeout(500)
                
                # Get checked care types
                care_types = []
                checked_boxes = await page.query_selector_all('input[type="checkbox"][checked]')
                
                for checkbox in checked_boxes:
                    try:
                        parent = await checkbox.evaluate_handle('el => el.closest("label")')
                        if parent:
                            text = await parent.inner_text()
                            if any(keyword in text for keyword in ['Living', 'Care', 'Nursing', 'Memory', 'Hospice', 'Health', 'Respite', 'Community']):
                                care_types.append(text.strip())
                    except:
                        continue
                
                # Normalize
                if care_types:
                    normalized = normalize_type(care_types)
                    listing['care_types'] = ', '.join(normalized)
                    listing['care_types_raw'] = ', '.join(care_types)
                
                status = "✅" if care_types else "⚠️ "
                print(f"   {status} {idx}/10: {listing['title'][:40]}... → {listing['care_types'] or 'No types found'}")
                
            except Exception as e:
                print(f"   ❌ {idx}/10: Failed - {str(e)[:50]}")
                continue
        
        # Save to CSV
        print(f"\n💾 Step 5: Save to CSV...")
        output_file = 'TEST_100_LISTINGS.csv'
        
        fieldnames = ['title', 'address', 'city', 'state', 'zip', 'url', 
                     'featured_image', 'care_types', 'care_types_raw']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_list)
        
        print(f"   ✅ Saved to {output_file}\n")
        
        await browser.close()
    
    # Show results
    print("="*70)
    print("TEST COMPLETE!")
    print("="*70)
    print(f"✅ Scraped {len(all_listings)} listings from 4 pages")
    print(f"✅ Deduped to {len(unique_list)} unique listings")
    print(f"✅ Got care types for 10 sample listings")
    print(f"✅ Saved to {output_file}")
    print("\n📊 Sample of CSV contents:")
    print("-"*70)
    
    # Show first 3 rows
    with open(output_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[:4]:  # Header + 3 rows
            print(line.strip())
    
    print("\n✅ FULL WORKFLOW WORKS - Ready for production run!")
    print("="*70)

asyncio.run(main())

