import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

INPUT_JSONL = "seniorly_data_resume.jsonl"
OUTPUT_JSONL = "seniorly_data_fixed.jsonl"

def load_listings():
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def is_bad_image(url):
    return (
        not url
        or url.lower().endswith('.svg')
        or 'headshot' in url.lower()
        or 'logo' in url.lower()
        or 'avatar' in url.lower()
        or 'icon' in url.lower()
        or url.lower().endswith('.pdf.png')
    )

async def get_valid_images(page, url):
    try:
        await page.goto(url)
        await page.wait_for_selector('#gallery img', timeout=8000)
        img_elements = await page.query_selector_all('#gallery img')

        valid_images = []
        fallback_streetview = None

        for img in img_elements:
            src = await img.get_attribute('src')
            if not src:
                continue

            if 'maps.googleapis.com' in src:
                fallback_streetview = src
                continue

            if 'cloudfront.net' in src and not is_bad_image(src):
                valid_images.append(src)

        if not valid_images and fallback_streetview:
            print("   🛑 No valid photos — using Street View as fallback")
            valid_images.append(fallback_streetview)

        return list(dict.fromkeys(valid_images))
    except Exception as e:
        print(f"⚠️ Error loading images from {url}: {e}")
        return []

async def fix_featured_images():
    listings = load_listings()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        with open(OUTPUT_JSONL, "w", encoding="utf-8") as f_out:
            for i, listing in enumerate(listings):
                url = listing.get("url")
                current_image = listing.get("featured_image")
                needs_fix = is_bad_image(current_image) or not current_image

                print(f"\n{i+1}/{len(listings)} - {listing.get('title', 'Unknown')[:40]}")
                print(f"   Current featured_image: {current_image or 'None'}")

                if needs_fix:
                    print(f"   🔄 Fixing image for: {url}")
                    images = await get_valid_images(page, url)
                    if images:
                        listing["featured_image"] = images[0]
                        listing["photos"] = images[1:]
                        print(f"   ✅ Updated featured_image: {images[0]}")
                        print(f"   🖼️ Total images found: {len(images)}")
                    else:
                        listing["featured_image"] = None
                        listing["photos"] = []
                        print("   🚫 No valid images found in #gallery")
                else:
                    print("   ✅ Featured image is fine. No update needed.")

                f_out.write(json.dumps(listing, ensure_ascii=False) + "\n")

        await browser.close()
    print("\n✅ All done! Updated listings saved to", OUTPUT_JSONL)

if __name__ == "__main__":
    asyncio.run(fix_featured_images())
