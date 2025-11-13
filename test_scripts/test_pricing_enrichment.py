#!/usr/bin/env python3
"""
California Pricing Enrichment Script
Enriches the California Senior Place listings with detailed pricing data from Senior Place attributes.
Based on the existing update_prices_from_seniorplace_export.py infrastructure.
"""

import os
import re
import csv
import argparse
import asyncio
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright
from datetime import datetime

# Senior Place credentials - updated
USERNAME = "allison@aplaceforseniors.org"
PASSWORD = "Hugomax2025!"

LOGIN_URL = "https://app.seniorplace.com/login"

def currency_to_number_str(value: str) -> str:
    """Convert currency string to clean number string"""
    if not value:
        return ""
    digits = re.sub(r"[^0-9.]+", "", str(value))
    return digits if digits and digits != "." else ""

async def login_to_seniorplace(context):
    """Login to Senior Place with enhanced error handling"""
    page = await context.new_page()
    print("🔐 Logging into Senior Place for pricing data...")
    
    await page.goto(LOGIN_URL)
    await page.wait_for_timeout(2000)
    
    # Fill login form
    await page.fill('#email', USERNAME)
    await page.fill('#password', PASSWORD)
    await page.click('#signin')
    
    # Wait for successful login
    try:
        await page.wait_for_selector('text=Communities', timeout=15000)
        print("✅ Successfully logged in")
    except:
        current_url = page.url
        if 'communities' in current_url or 'dashboard' in current_url:
            print("✅ Login successful (URL-based detection)")
        else:
            raise Exception("Login failed")
    
    return page

async def get_input_value_by_label(page, label_text: str) -> str:
    """Extract input value by label text from Senior Place forms"""
    label = page.locator("div.form-group div.label-group div", has_text=label_text).first
    if not await label.count():
        return ""
    group = label.locator("xpath=ancestor::div[contains(@class,'form-group')][1]")
    input_el = group.locator('input').first
    if not await input_el.count():
        return ""
    try:
        value = await input_el.input_value()
    except Exception:
        value = await input_el.get_attribute('value')
    return currency_to_number_str(value or "")

async def scrape_finances_block(page) -> Dict[str, str]:
    """Scrape ALL pricing data from the Finances block"""
    await page.wait_for_selector('text=Finances', timeout=20000)
    
    # Key pricing fields to extract
    pricing_fields = {
        "Monthly Base Price": "monthly_base_price",
        "Price (High End)": "price_high_end", 
        "Second Person Fee": "second_person_fee",
        "Pet Deposit": "pet_deposit",
        "AL Care Levels (Low)": "al_care_levels_low",
        "AL Care Levels (High)": "al_care_levels_high",
        "Assisted Living Price (Low)": "assisted_living_price_low",
        "Assisted Living Price (High)": "assisted_living_price_high",
        "Assisted Living 1BR Price (Low)": "assisted_living_1br_price_low",
        "Assisted Living 1BR Price (High)": "assisted_living_1br_price_high",
        "Assisted Living 2BR Price (Low)": "assisted_living_2br_price_low",
        "Assisted Living 2BR Price (High)": "assisted_living_2br_price_high",
        "Assisted Living Home Price (Low)": "assisted_living_home_price_low",
        "Assisted Living Home Price (High)": "assisted_living_home_price_high",
        "Independent Living Price (Low)": "independent_living_price_low",
        "Independent Living Price (High)": "independent_living_price_high",
        "Independent Living 1BR Price (Low)": "independent_living_1br_price_low",
        "Independent Living 1BR Price (High)": "independent_living_1br_price_high",
        "Independent Living 2BR Price (Low)": "independent_living_2br_price_low",
        "Independent Living 2BR Price (High)": "independent_living_2br_price_high",
        "Memory Care Price (Low)": "memory_care_price_low",
        "Memory Care Price (High)": "memory_care_price_high",
    }
    
    results = {}
    for label, field_name in pricing_fields.items():
        value = await get_input_value_by_label(page, label)
        if value:
            results[field_name] = value
    
    # Check for boolean flags
    boolean_fields = {
        "Accepts ALTCS": "accepts_altcs",
        "Has Medicaid Contract": "has_medicaid_contract", 
        "Offers Affordable/Low Income": "offers_affordable_low_income"
    }
    
    for label, field_name in boolean_fields.items():
        checkbox = page.locator(f"input[type='checkbox']", has_text=label).first
        if await checkbox.count():
            is_checked = await checkbox.is_checked()
            results[field_name] = "Yes" if is_checked else "No"
    
    return results

async def scrape_single_listing_pricing(page, url: str) -> Dict[str, str]:
    """Scrape pricing data for a single listing"""
    try:
        # Navigate to the listing's attributes page
        if not url.endswith('/attributes'):
            attributes_url = url.rstrip('/') + '/attributes'
        else:
            attributes_url = url
            
        await page.goto(attributes_url, timeout=30000)
        
        # Scrape the finances data
        pricing_data = await scrape_finances_block(page)
        
        return pricing_data
        
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return {}

async def enrich_california_listings():
    """Main function to enrich California listings with pricing data"""
    
    input_file = "california_expansion/test_sample_10.csv"
    output_file = "california_seniorplace_data_with_pricing.csv"
    
    print("💰 CALIFORNIA PRICING ENRICHMENT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Read California listings
    listings = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        original_fieldnames = reader.fieldnames
        for row in reader:
            listings.append(row)
    
    print(f"📊 Loaded {len(listings)} California listings")
    
    # Add new pricing columns
    pricing_columns = [
        "monthly_base_price", "price_high_end", "second_person_fee", "pet_deposit",
        "al_care_levels_low", "al_care_levels_high",
        "assisted_living_price_low", "assisted_living_price_high",
        "assisted_living_1br_price_low", "assisted_living_1br_price_high", 
        "assisted_living_2br_price_low", "assisted_living_2br_price_high",
        "assisted_living_home_price_low", "assisted_living_home_price_high",
        "independent_living_price_low", "independent_living_price_high",
        "independent_living_1br_price_low", "independent_living_1br_price_high",
        "independent_living_2br_price_low", "independent_living_2br_price_high", 
        "memory_care_price_low", "memory_care_price_high",
        "accepts_altcs", "has_medicaid_contract", "offers_affordable_low_income"
    ]
    
    new_fieldnames = list(original_fieldnames) + pricing_columns
    
    # Initialize pricing columns
    for listing in listings:
        for col in pricing_columns:
            listing[col] = ""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        try:
            page = await login_to_seniorplace(context)
            
            print(f"🔄 Processing {len(listings)} listings for pricing data...")
            print()
            
            successful = 0
            failed = 0
            
            for i, listing in enumerate(listings, 1):
                url = listing.get('url', '').strip()
                title = listing.get('title', 'Unknown')
                
                if not url or 'seniorplace.com' not in url:
                    print(f"⚠️  {i:4d}/{len(listings)} - No Senior Place URL: {title}")
                    failed += 1
                    continue
                
                print(f"💰 {i:4d}/{len(listings)} - {title[:50]:<50}", end=" ")
                
                pricing_data = await scrape_single_listing_pricing(page, url)
                
                if pricing_data:
                    # Update listing with pricing data
                    for field, value in pricing_data.items():
                        listing[field] = value
                    
                    # Set main price field if monthly base price exists
                    if pricing_data.get('monthly_base_price'):
                        listing['price'] = pricing_data['monthly_base_price']
                    
                    successful += 1
                    print("✅")
                else:
                    failed += 1
                    print("❌")
                
                # Small delay to be respectful to the server
                await asyncio.sleep(0.5)  # Half second delay between requests
                
                # Progress updates
                if i % 25 == 0:
                    print(f"   📊 Progress: {successful} successful, {failed} failed")
                
                # Save checkpoint every 100 listings
                if i % 100 == 0:
                    checkpoint_file = f"{output_file}.checkpoint"
                    print(f"   💾 Saving checkpoint at {i}/{len(listings)}...")
                    with open(checkpoint_file, 'w', newline='', encoding='utf-8') as cf:
                        writer = csv.DictWriter(cf, fieldnames=new_fieldnames)
                        writer.writeheader()
                        writer.writerows(listings)
                    print(f"   ✅ Checkpoint saved")
        
        finally:
            await browser.close()
    
    # Write enriched data
    print()
    print("💾 Writing enriched data...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(listings)
    
    print()
    print("🎉 PRICING ENRICHMENT COMPLETE!")
    print("=" * 60)
    print(f"✅ Successfully enriched: {successful} listings")
    print(f"❌ Failed to enrich: {failed} listings")
    print(f"📄 Output file: {output_file}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(enrich_california_listings())
