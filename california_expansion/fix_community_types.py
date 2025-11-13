#!/usr/bin/env python3
"""
Fix community types by visiting each facility's individual page
and extracting the correct types from the Attributes section
"""
import asyncio
import csv
import json
import os
from playwright.async_api import async_playwright
from typing import List, Dict, Optional

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

async def get_facility_types(page, url: str) -> List[str]:
    """Visit a facility's individual page and extract community types from Attributes section"""
    try:
        print(f"🔍 Visiting: {url}")
        await page.goto(url)
        await page.wait_for_timeout(500)
        
        # Click the "Attributes" tab/button first
        print("🔍 Looking for Attributes tab...")
        attributes_tab = await page.query_selector('button:has-text("Attributes"), a:has-text("Attributes"), [role="tab"]:has-text("Attributes")')
        if attributes_tab:
            await attributes_tab.click()
            await page.wait_for_timeout(500)
            print("✅ Clicked Attributes tab")
        else:
            print("⚠️ Could not find Attributes tab")
            return []
        
        # Look for checked checkboxes in the community types section
        types = []
        
        # Find all checked checkboxes
        checked_checkboxes = await page.query_selector_all('input[type="checkbox"]:checked')
        print(f"🔍 Found {len(checked_checkboxes)} checked checkboxes")
        
        for cb in checked_checkboxes:
            try:
                # Get the label text associated with this checkbox
                label = await cb.evaluate_handle('el => el.closest("label")')
                if label:
                    text = await label.inner_text()
                    if text and text.strip():
                        # Check if this looks like a community type
                        text_clean = text.strip()
                        if any(keyword in text_clean.lower() for keyword in ['assisted', 'living', 'memory', 'nursing', 'independent', 'care', 'home', 'facility']):
                            types.append(text_clean)
                            print(f"  ✅ Found type: {text_clean}")
            except Exception as e:
                print(f"  ⚠️ Error processing checkbox: {e}")
        
        if types:
            print(f"✅ Found types: {types}")
            return types
        else:
            print(f"⚠️ No community types found for {url}")
            return []
            
    except Exception as e:
        print(f"❌ Error visiting {url}: {e}")
        return []

async def fix_community_types():
    """Fix community types by visiting each facility's page with proper checkpointing"""
    
    # Read the existing CSV
    input_csv = "california_seniorplace_data_DEDUPED.csv"
    output_csv = "california_seniorplace_data_fixed.csv"
    checkpoint_file = f"{output_csv}.checkpoint"
    
    print(f"📖 Reading {input_csv}...")
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"📊 Found {len(rows)} facilities to process")
    print(f"🔍 Sample type from original: {rows[0].get('type', 'NOT_FOUND')}")
    
    # Check for existing checkpoint
    start_index = 0
    if os.path.exists(checkpoint_file):
        print(f"🔄 Found checkpoint file, resuming from where we left off...")
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_reader = csv.DictReader(f)
            checkpoint_rows = list(checkpoint_reader)
            if len(checkpoint_rows) == len(rows):
                print(f"✅ Checkpoint complete - all {len(rows)} facilities already processed!")
                return
            else:
                start_index = len(checkpoint_rows)
                print(f"🔄 Resuming from facility {start_index + 1}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Run in background
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.wait_for_timeout(2000)
        
        await page.fill('#email', "allison@aplaceforseniors.org")
        await page.fill('#password', "Hugomax2025!")
        await page.click('#signin')
        await page.wait_for_timeout(5000)
        
        print("✅ Logged in successfully")
        
        # Process each facility starting from checkpoint
        print(f"🔄 Processing facilities {start_index + 1} to {len(rows)}...")
        
        successful = 0
        failed = 0
        
        for i in range(start_index, len(rows)):
            row = rows[i]
            print(f"\n📋 Processing {i+1}/{len(rows)}: {row.get('title', 'Unknown')}")
            
            url = row.get('url', '')
            if not url:
                print("⚠️ No URL found, skipping")
                failed += 1
                continue
            
            # Get the correct community types
            types = await get_facility_types(page, url)
            
            if types:
                # Normalize the types
                normalized_types = normalize_type(types)
                print(f"🔍 Raw types found: {types}")
                print(f"🔍 Normalized types: {normalized_types}")
                row['type'] = ', '.join(normalized_types)
                print(f"✅ Updated types to: {normalized_types}")
                successful += 1
            else:
                print(f"⚠️ Could not determine types for {row.get('title', 'Unknown')}")
                print(f"🔍 Current type value: {row.get('type', 'NOT_FOUND')}")
                failed += 1
            
            # Add a small delay to be respectful
            await page.wait_for_timeout(500)
            
            # Progress updates
            if (i + 1) % 25 == 0:
                print(f"   📊 Progress: {successful} successful, {failed} failed")
            
            # Save checkpoint every 100 facilities
            if (i + 1) % 100 == 0:
                print(f"   💾 Saving checkpoint at {i+1}/{len(rows)}...")
                with open(checkpoint_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                print(f"   ✅ Checkpoint saved")
        
        await browser.close()
    
    # Write the final updated CSV
    print(f"\n💾 Writing final updated CSV to {output_csv}...")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    
    # Clean up checkpoint file
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print(f"🗑️ Cleaned up checkpoint file")
    
    print("✅ Done! Check the updated CSV file.")
    print(f"📊 Final stats: {successful} successful, {failed} failed")

if __name__ == "__main__":
    asyncio.run(fix_community_types())
