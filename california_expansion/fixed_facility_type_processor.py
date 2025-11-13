#!/usr/bin/env python3
"""
Fixed Facility Type Processor with Proper Checkpointing
Processes the deduped California listings and updates BOTH 'type' and 'normalized_types' columns 
with proper incremental saving. This is the key script that populates the normalized_types field
for WordPress import. Based on the pattern from memory.md - saves CSV data every 100 facilities, 
not just progress index.
"""

import asyncio
import csv
import json
import os
import sys
import argparse
from playwright.async_api import async_playwright
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Type mapping from memory.md - same as WordPress preparation
# All possible SeniorPlace community types mapped to our canonical types
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
    "Respite Care": "Home Care",
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
    """Visit a facility's /attributes page and extract CHECKED community types only."""
    try:
        attributes_url = f"{url.rstrip('/')}/attributes"
        print(f"🔍 Visiting: {attributes_url}")
        await page.goto(attributes_url, wait_until="networkidle", timeout=30000)

        # Wait for the community type section label/text to ensure correct page state
        try:
            await page.wait_for_selector('text=Community Type', timeout=10000)
        except Exception:
            print("⚠️ 'Community Type' section not found; page may not be attributes. Skipping.")
            return []

        # Use robust in-page evaluation to grab ONLY Community Type checkboxes
        types = await page.evaluate(
            """
            () => {
              const out = [];
              // Find the "Community Type" section heading
              const headings = Array.from(document.querySelectorAll('h3, h2, div'));
              let communityTypeSection = null;
              
              for (const heading of headings) {
                if ((heading.textContent || '').includes('Community Type')) {
                  communityTypeSection = heading.parentElement;
                  break;
                }
              }
              
              if (!communityTypeSection) return out;
              
              // Only get checkboxes within the Community Type section
              const labels = Array.from(communityTypeSection.querySelectorAll('label.inline-flex'));
              for (const label of labels) {
                const textEl = label.querySelector('div.ml-2');
                const input = label.querySelector('input[type="checkbox"]');
                if (!textEl || !input) continue;
                if (!input.checked) continue; // only CHECKED types
                const name = (textEl.textContent || '').trim();
                // Filter out non-type entries
                if (name && !name.includes('Medicaid') && !name.includes('ALTCS') && !name.includes('Affordable')) {
                  out.push(name);
                }
              }
              return out;
            }
            """
        )

        if types:
            print(f"✅ Found types: {types}")
            return [t.strip() for t in types if t and t.strip()]
        else:
            print("⚠️ No checked community types found")
            return []

    except Exception as e:
        print(f"❌ Error visiting attributes page for {url}: {e}")
        return []

async def process_facility_types_with_checkpointing(
    input_csv: str,
    output_csv: str,
    username: str,
    password: str,
    headless: bool = True,
    resume: bool = True,
    delay_ms: int = 500
) -> Tuple[int, int]:
    """Process facility types with proper checkpointing - saves CSV data every 100 facilities.
    Returns (successful, failed).
    """

    checkpoint_file = f"{output_csv}.checkpoint"

    print(f"📖 Reading {input_csv}...")

    # Read the existing CSV
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("❌ No rows found in input CSV")
        return (0, 0)

    print(f"📊 Found {len(rows)} facilities to process")
    print(f"🔍 Sample type from original: {rows[0].get('type', 'NOT_FOUND')}")

    # Add normalized_types column if it doesn't exist
    if 'normalized_types' not in rows[0]:
        print("➕ Adding normalized_types column...")
        for row in rows:
            row['normalized_types'] = ''
        print("✅ Added normalized_types column")

    # Check for existing checkpoint
    start_index = 0
    if resume and os.path.exists(checkpoint_file):
        print(f"🔄 Found checkpoint file, resuming from where we left off...")
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint_reader = csv.DictReader(f)
            checkpoint_rows = list(checkpoint_reader)
            if len(checkpoint_rows) == len(rows):
                # Check how many rows actually have normalized_types filled
                filled_count = len([r for r in checkpoint_rows if r.get('normalized_types')])
                if filled_count == len(rows):
                    print(f"✅ Checkpoint complete - all {len(rows)} facilities already processed!")
                    # Write final from checkpoint to ensure output exists
                    with open(output_csv, 'w', encoding='utf-8', newline='') as out_f:
                        writer = csv.DictWriter(out_f, fieldnames=checkpoint_rows[0].keys())
                        writer.writeheader()
                        writer.writerows(checkpoint_rows)
                    return (filled_count, 0)
                else:
                    # Find the first row that needs processing (empty normalized_types)
                    for idx, row in enumerate(checkpoint_rows):
                        if not row.get('normalized_types'):
                            start_index = idx
                            break
                    # Use checkpoint data as starting point
                    rows = checkpoint_rows
                    print(f"🔄 Resuming from facility {start_index + 1} ({filled_count} already done, {len(rows) - filled_count} remaining)")
            else:
                start_index = len(checkpoint_rows)
                print(f"🔄 Resuming from facility {start_index + 1}")

    successful = 0
    failed = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        # Login
        print("🔐 Logging in...")
        await page.goto("https://app.seniorplace.com/login", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1000)

        await page.fill('#email', username)
        await page.fill('#password', password)
        await page.click('#signin')
        # Wait for something indicative of a logged-in state
        await page.wait_for_timeout(3000)

        print("✅ Logged in successfully")

        # Process each facility starting from checkpoint
        print(f"🔄 Processing facilities {start_index + 1} to {len(rows)}...")

        for i in range(start_index, len(rows)):
            row = rows[i]
            title = row.get('title', 'Unknown')
            url = row.get('url', '')
            print(f"\n📋 Processing {i+1}/{len(rows)}: {title}")

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

                # Update BOTH the type and normalized_types columns
                row['type'] = ', '.join(normalized_types)
                row['normalized_types'] = ', '.join(normalized_types)

                print(f"✅ Updated type/normalized_types to: {row['normalized_types']}")
                successful += 1
            else:
                print(f"⚠️ Could not determine types for {title}")
                print(f"🔍 Current type value: {row.get('type', 'NOT_FOUND')}")
                print(f"🔍 Current normalized_types value: {row.get('normalized_types', 'NOT_FOUND')}")
                failed += 1

            # Be respectful
            await page.wait_for_timeout(delay_ms)

            # Progress updates every 25 facilities
            if (i + 1) % 25 == 0:
                print(f"   📊 Progress: {successful} successful, {failed} failed")

            # Save actual CSV data every 100 facilities
            if (i + 1) % 100 == 0:
                print(f"   💾 Saving checkpoint at {i+1}/{len(rows)}...")
                with open(checkpoint_file, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                print(f"   ✅ Checkpoint saved with actual data")

        await browser.close()

    # Write the final updated CSV
    print(f"\n💾 Writing final updated CSV to {output_csv}...")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # Clean up checkpoint file
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print("🗑️ Cleaned up checkpoint file")

    return (successful, failed)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update normalized types from Senior Place /attributes page")
    parser.add_argument("--input", default="california_seniorplace_data_DEDUPED.csv", help="Input CSV path")
    parser.add_argument("--output", default="california_seniorplace_data_fixed.csv", help="Output CSV path")
    parser.add_argument("--username", default=os.environ.get("SENIORPLACE_USER"), help="Senior Place username (or set SENIORPLACE_USER)")
    parser.add_argument("--password", default=os.environ.get("SENIORPLACE_PASS"), help="Senior Place password (or set SENIORPLACE_PASS)")
    parser.add_argument("--headful", action="store_true", help="Run browser headful (default headless)")
    parser.add_argument("--no-resume", action="store_true", dest="no_resume", help="Do not resume from checkpoint")
    parser.add_argument("--delay-ms", type=int, default=500, dest="delay_ms", help="Delay between requests in milliseconds")

    args = parser.parse_args()

    if not args.username or not args.password:
        print("❌ Missing credentials. Pass --username/--password or set SENIORPLACE_USER/SENIORPLACE_PASS.")
        sys.exit(1)

    success, fail = asyncio.run(
        process_facility_types_with_checkpointing(
            input_csv=args.input,
            output_csv=args.output,
            username=args.username,
            password=args.password,
            headless=(not args.headful),
            resume=(not args.no_resume),
            delay_ms=args.delay_ms,
        )
    )

    print("✅ Done! Check the updated CSV file.")
    print(f"📊 Final stats: {success} successful, {fail} failed")