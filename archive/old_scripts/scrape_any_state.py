#!/usr/bin/env python3
"""
Simple Senior Place Scraper - ANY STATE
No WordPress needed - just outputs CSV
"""

import asyncio
import csv
import argparse
from datetime import datetime
from playwright.async_api import async_playwright

# Senior Place credentials
USERNAME = "allison@aplaceforseniors.org"
PASSWORD = "Hugomax2025!"

# Type mapping to normalized names
TYPE_MAPPING = {
    'assisted living facility': 'Assisted Living Community',
    'assisted living home': 'Assisted Living Home',
    'independent living': 'Independent Living',
    'memory care': 'Memory Care',
    'skilled nursing': 'Nursing Home',
    'continuing care retirement community': 'Assisted Living Community',
    'in-home care': 'Home Care',
    'home health': 'Home Care',
    'hospice': 'Home Care',
    'respite care': 'Assisted Living Community',
}


async def scrape_state(state_code: str, output_file: str):
    """Scrape all listings for a state from Senior Place"""
    
    print(f"🚀 Scraping {state_code} from Senior Place...")
    print(f"Output: {output_file}")
    print()
    
    all_listings = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login
            print("🔐 Logging in...")
            await page.goto("https://app.seniorplace.com/login")
            await page.fill('input[name="email"]', USERNAME)
            await page.fill('input[name="password"]', PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_selector('text=Communities', timeout=15000)
            print("✅ Logged in\n")
            
            # Go to state search
            search_url = f"https://app.seniorplace.com/communities?state={state_code}"
            await page.goto(search_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Get total pages
            try:
                pagination = await page.query_selector('.pagination')
                if pagination:
                    page_links = await pagination.query_selector_all('a')
                    total_pages = 1
                    for link in page_links:
                        text = await link.inner_text()
                        if text.isdigit():
                            total_pages = max(total_pages, int(text))
                else:
                    total_pages = 1
            except:
                total_pages = 1
            
            print(f"📊 Found {total_pages} pages\n")
            
            # Scrape each page
            for page_num in range(1, total_pages + 1):
                if page_num > 1:
                    page_url = f"{search_url}&page={page_num}"
                    await page.goto(page_url, wait_until="networkidle")
                    await page.wait_for_timeout(2000)
                
                print(f"📄 Page {page_num}/{total_pages}...", end=" ")
                
                # Extract listings from page
                listings = await page.evaluate("""
                    () => {
                        const results = [];
                        const cards = document.querySelectorAll('.community-card, .listing-card, [data-community-id]');
                        
                        cards.forEach(card => {
                            const titleEl = card.querySelector('h3, h2, .title, .community-name');
                            const linkEl = card.querySelector('a[href*="/communities/show/"]');
                            const imgEl = card.querySelector('img');
                            const addressEl = card.querySelector('.address, .location');
                            
                            if (titleEl && linkEl) {
                                results.push({
                                    title: titleEl.textContent.trim(),
                                    url: linkEl.href,
                                    featured_image: imgEl ? imgEl.src : '',
                                    address: addressEl ? addressEl.textContent.trim() : ''
                                });
                            }
                        });
                        
                        return results;
                    }
                """)
                
                all_listings.extend(listings)
                print(f"Found {len(listings)} listings")
                
                await asyncio.sleep(1)  # Be nice to the server
            
            print(f"\n✅ Scraped {len(all_listings)} total listings")
            print("\n🔍 Enriching with details (pricing, care types)...\n")
            
            # Enrich each listing with details
            enriched = []
            for i, listing in enumerate(all_listings, 1):
                try:
                    detail_page = await context.new_page()
                    
                    # Go to attributes page
                    attrs_url = f"{listing['url'].rstrip('/')}/attributes"
                    await detail_page.goto(attrs_url, wait_until="networkidle", timeout=20000)
                    await detail_page.wait_for_timeout(1000)
                    
                    # Get care types
                    care_types = await detail_page.evaluate("""
                        () => {
                            const types = [];
                            const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                            
                            for (const label of labels) {
                                const textEl = label.querySelector("div.ml-2");
                                const input = label.querySelector('input[type="checkbox"]');
                                
                                if (!textEl || !input) continue;
                                if (!input.checked) continue;
                                
                                const name = (textEl.textContent || "").trim();
                                if (name) types.push(name);
                            }
                            
                            return types;
                        }
                    """)
                    
                    # Get pricing
                    pricing = await detail_page.evaluate("""
                        () => {
                            const result = {};
                            const labels = document.querySelectorAll('.form-group');
                            
                            for (const group of labels) {
                                const labelText = group.textContent;
                                const input = group.querySelector('input');
                                
                                if (labelText.includes('Monthly Base Price') && input) {
                                    result.price = input.value;
                                }
                                if (labelText.includes('High End') && input) {
                                    result.price_high = input.value;
                                }
                            }
                            
                            return result;
                        }
                    """)
                    
                    # Normalize care types
                    normalized_types = []
                    for ct in care_types:
                        mapped = TYPE_MAPPING.get(ct.lower(), ct)
                        if mapped not in normalized_types:
                            normalized_types.append(mapped)
                    
                    # Add enriched data
                    listing['care_types_raw'] = ', '.join(care_types)
                    listing['care_types_normalized'] = ', '.join(normalized_types)
                    listing['price'] = pricing.get('price', '').replace('$', '').replace(',', '')
                    listing['price_high'] = pricing.get('price_high', '').replace('$', '').replace(',', '')
                    
                    enriched.append(listing)
                    
                    if i % 10 == 0:
                        print(f"  ✅ {i}/{len(all_listings)} enriched")
                    
                    await detail_page.close()
                    await asyncio.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"  ⚠️  Failed: {listing.get('title', 'Unknown')} - {e}")
                    enriched.append(listing)  # Add without enrichment
                    if 'detail_page' in locals():
                        await detail_page.close()
            
            # Save to CSV
            print(f"\n💾 Saving to {output_file}...")
            
            fieldnames = [
                'title', 'address', 'url', 'featured_image',
                'care_types_raw', 'care_types_normalized',
                'price', 'price_high'
            ]
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(enriched)
            
            print(f"✅ DONE! {len(enriched)} listings saved to {output_file}")
            
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Scrape Senior Place by state")
    parser.add_argument('--state', required=True, help='State code (e.g., AZ, CA, CO)')
    parser.add_argument('--output', help='Output CSV file (default: [state]_seniorplace_data.csv)')
    
    args = parser.parse_args()
    
    state = args.state.upper()
    output = args.output or f"{state}_seniorplace_data_{datetime.now().strftime('%Y%m%d')}.csv"
    
    asyncio.run(scrape_state(state, output))


if __name__ == "__main__":
    main()

