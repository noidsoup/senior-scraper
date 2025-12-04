#!/usr/bin/env python3
"""
Deduplicate the AZ checkpoint data and scrape care types for unique listings only
"""

import asyncio
import pickle
import csv
import random
from playwright.async_api import async_playwright

import os
USERNAME = os.getenv("SP_USERNAME", "")
PASSWORD = os.getenv("SP_PASSWORD", "")

if not USERNAME or not PASSWORD:
    print("❌ Error: Set SP_USERNAME and SP_PASSWORD environment variables")
    exit(1)

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
    # Load checkpoint
    print("📂 Loading checkpoint...")
    with open('AZ_seniorplace_data_20251028.csv.checkpoint', 'rb') as f:
        cp = pickle.load(f)
    
    print(f"   Total listings: {len(cp['listings'])}")
    
    # Deduplicate by URL
    print("🔍 Deduplicating by URL...")
    unique_listings = {}
    for listing in cp['listings']:
        url = listing['url']
        if url not in unique_listings:
            unique_listings[url] = listing
    
    unique_list = list(unique_listings.values())
    print(f"   Unique listings: {len(unique_list)}")
    print(f"   Removed {len(cp['listings']) - len(unique_list)} duplicates\n")
    
    # Track failures for retry later
    failed_listings = []
    
    # Check for progress checkpoint
    progress_checkpoint = 'AZ_care_types_progress.pkl'
    start_idx = 0
    
    if Path(progress_checkpoint).exists():
        print("📂 Found progress checkpoint, resuming...")
        with open(progress_checkpoint, 'rb') as f:
            progress = pickle.load(f)
            start_idx = progress['last_index']
            failed_listings = progress.get('failed_listings', [])
            # Restore care types already scraped
            for i in range(start_idx):
                if 'care_types' in progress['listings'][i]:
                    unique_list[i]['care_types'] = progress['listings'][i]['care_types']
                    unique_list[i]['care_types_raw'] = progress['listings'][i].get('care_types_raw', '')
        print(f"   Resuming from listing {start_idx + 1}/{len(unique_list)}\n")
    
    # Now scrape care types for unique listings
    print(f"🔍 Scraping care types for {len(unique_list)} unique AZ listings...")
    print("   (With 2-4 sec delays between requests)\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', USERNAME)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        print("✅ Logged in\n")
        
        # Process each unique listing
        for idx, listing in enumerate(unique_list[start_idx:], start_idx + 1):
            try:
                # Rate limiting
                delay = random.uniform(2000, 4000)
                await page.wait_for_timeout(delay)
                
                await page.goto(listing['url'], timeout=30000)
                await page.wait_for_timeout(random.uniform(1000, 2000))
                
                # Click Attributes tab
                attributes_tab = await page.query_selector('button:has-text("Attributes"), a:has-text("Attributes")')
                if attributes_tab:
                    await attributes_tab.click()
                    await page.wait_for_timeout(random.uniform(500, 1000))
                
                # Find checked care type checkboxes
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
                
                # Normalize and update
                if care_types:
                    normalized = normalize_type(care_types)
                    listing['care_types'] = ', '.join(normalized)
                    listing['care_types_raw'] = ', '.join(care_types)
                
                # Save checkpoint every 10 listings
                if idx % 10 == 0:
                    with open(progress_checkpoint, 'wb') as f:
                        pickle.dump({
                            'last_index': idx,
                            'listings': unique_list,
                            'failed_listings': failed_listings
                        }, f)
                    print(f"  Processed {idx}/{len(unique_list)} listings... (checkpoint saved)")
                
                if idx % 50 == 0:
                    print(f"  ⏸️  Pausing 10 seconds...")
                    await page.wait_for_timeout(10000)
                    
            except Exception as e:
                print(f"  ⚠️ Failed for {listing['title']}: {e}")
                failed_listings.append({
                    'title': listing['title'],
                    'url': listing['url'],
                    'error': str(e)[:100]
                })
                await page.wait_for_timeout(random.uniform(1000, 2000))
                continue
        
        await browser.close()
    
    # Save to CSV
    print(f"\n💾 Saving to CSV...")
    output_file = 'AZ_seniorplace_data_FINAL.csv'
    
    fieldnames = ['title', 'address', 'city', 'state', 'zip', 'url', 
                 'featured_image', 'care_types', 'care_types_raw']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_list)
    
    print(f"✅ Saved {len(unique_list)} unique AZ listings to: {output_file}\n")
    
    # Clean up progress checkpoint
    if Path(progress_checkpoint).exists():
        Path(progress_checkpoint).unlink()
        print("🗑️  Removed progress checkpoint (complete)\n")
    
    # Save failed listings for retry
    if failed_listings:
        failed_file = 'AZ_FAILED_LISTINGS.csv'
        with open(failed_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'url', 'error'])
            writer.writeheader()
            writer.writerows(failed_listings)
        print(f"⚠️  Saved {len(failed_listings)} failed listings to: {failed_file}")
        print(f"   You can retry these later with a separate script\n")
    
    print("=" * 70)
    print("🎯 ARIZONA COMPLETE!")
    print(f"   Successful: {len(unique_list) - len(failed_listings)}")
    print(f"   Failed: {len(failed_listings)}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

