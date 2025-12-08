#!/usr/bin/env python3
"""Quick test to fetch one listing with timeout"""
import asyncio
import os
import json
import sys
from playwright.async_api import async_playwright

# Use a known URL from CSV
URL = "https://app.seniorplace.com/communities/show/6b552075-435a-45f2-8017-9d1508054958"

async def fetch_with_timeout():
    sp_user = os.getenv('SP_USERNAME')
    sp_pass = os.getenv('SP_PASSWORD')
    
    if not sp_user or not sp_pass:
        print("ERROR: SP_USERNAME and SP_PASSWORD must be set")
        return
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            print("Logging in...")
            await page.goto("https://app.seniorplace.com/login", timeout=30000)
            await page.fill('input[name="email"]', sp_user)
            await page.fill('input[name="password"]', sp_pass)
            await page.click('button[type="submit"]')
            await page.wait_for_selector('text=Communities', timeout=15000)
            print("✓ Logged in")
            
            print(f"Loading listing: {URL}")
            await page.goto(URL, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(1500)
            
            # Title
            title_el = await page.query_selector('h1')
            title = await title_el.inner_text() if title_el else 'Unknown'
            
            # Address
            address = city = state = zip_code = ''
            address_els = await page.query_selector_all('address p')
            if len(address_els) >= 1:
                address = (await address_els[0].inner_text()) or ''
            if len(address_els) >= 2:
                location = (await address_els[1].inner_text()) or ''
                parts = location.split(',')
                if len(parts) >= 2:
                    city = parts[0].strip()
                    state_zip = parts[1].strip().split()
                    if len(state_zip) > 0:
                        state = state_zip[0]
                    if len(state_zip) > 1:
                        zip_code = state_zip[1]
            
            # Attributes page
            print("Loading attributes page...")
            attrs_url = URL.rstrip('/') + '/attributes'
            await page.goto(attrs_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1500)
            
            care_types = await page.evaluate("""
                () => {
                    const types = [];
                    const labels = Array.from(document.querySelectorAll('label.inline-flex'));
                    for (const label of labels) {
                        const textEl = label.querySelector('div.ml-2');
                        const input = label.querySelector('input[type="checkbox"]');
                        if (!textEl || !input || !input.checked) continue;
                        const name = (textEl.textContent || '').trim();
                        if (name) types.push(name);
                    }
                    return types;
                }
            """) or []
            
            pricing_desc = await page.evaluate("""
                () => {
                    const result = {};
                    const groups = document.querySelectorAll('.form-group');
                    for (const g of groups) {
                        const labelText = g.textContent || '';
                        const input = g.querySelector('input');
                        const textarea = g.querySelector('textarea');
                        if (labelText.includes('Monthly Base Price') && input) result.monthly_base_price = input.value;
                        if (labelText.includes('High End') && input) result.price_high_end = input.value;
                        if (labelText.includes('Second Person Fee') && input) result.second_person_fee = input.value;
                        if (labelText.includes('Description') && (textarea || input)) {
                            const src = textarea || input;
                            result.description = (src.value || src.textContent || '').trim();
                        }
                    }
                    return result;
                }
            """) or {}
            
            # Featured image
            await page.goto(URL, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(500)
            featured_image = ''
            img_el = await page.query_selector("img")
            if img_el:
                src = await img_el.get_attribute('src')
                if src:
                    if src.startswith('/api/files/'):
                        featured_image = f"https://placement-crm-cdn.s3.us-west-2.amazonaws.com{src}"
                    else:
                        featured_image = src if src.startswith('http') else f"https://app.seniorplace.com{src}"
            
            listing = {
                'title': title.strip(),
                'address': address.strip(),
                'city': city.strip(),
                'state': state.strip(),
                'zip': zip_code.strip(),
                'care_types': care_types,
                'monthly_base_price': pricing_desc.get('monthly_base_price', ''),
                'price_high_end': pricing_desc.get('price_high_end', ''),
                'second_person_fee': pricing_desc.get('second_person_fee', ''),
                'description': pricing_desc.get('description', ''),
                'featured_image': featured_image,
                'url': URL,
            }
            
            print("\n" + "="*80)
            print("FULL LISTING DATA FROM SENIOR PLACE")
            print("="*80)
            print(json.dumps(listing, indent=2, ensure_ascii=False))
            
            await browser.close()
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(fetch_with_timeout())

