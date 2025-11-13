#!/usr/bin/env python3
"""
Debug script to inspect Senior Place filter options
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_filters():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login using the same approach as the working scraper
        await page.goto("https://app.seniorplace.com/login")
        await page.wait_for_timeout(2000)
        
        # Check if login form is present
        email_field = await page.query_selector('#email')
        if not email_field:
            print("❌ Email field not found - checking page content...")
            content = await page.content()
            print(f"Page title: {await page.title()}")
            await page.screenshot(path="login_debug.png")
            raise Exception("Login form not found")
        
        await page.fill('#email', "melanie@aplaceforseniors.com")
        await page.fill('#password', "Melanie123!")
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(5000)
        
        # Check if we're logged in
        current_url = page.url
        print(f"Current URL after login: {current_url}")
        
        # Go to communities page
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(5000)  # Wait longer for page load
        
        # Check current URL again
        current_url = page.url
        print(f"Current URL after navigation: {current_url}")
        
        # Check if we can see the page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Take screenshot
        await page.screenshot(path="debug_communities.png")
        print("📸 Screenshot saved: debug_communities.png")
        
        # Find all filter-related elements
        print("\n🔍 Looking for filter elements...")
        
        # Check for filter buttons
        filter_buttons = await page.query_selector_all('button, a, [role="button"]')
        print(f"Found {len(filter_buttons)} potential filter buttons:")
        for i, btn in enumerate(filter_buttons[:15]):
            try:
                text = await btn.inner_text()
                if text and any(word in text.lower() for word in ['filter', 'more', 'state', 'location', 'search']):
                    print(f"  {i}: '{text.strip()}'")
            except:
                pass
        
        # Check for dropdowns/selects
        selects = await page.query_selector_all('select, [role="combobox"]')
        print(f"\nFound {len(selects)} select elements:")
        for i, sel in enumerate(selects):
            try:
                options = await sel.query_selector_all('option')
                print(f"  Select {i}: {len(options)} options")
                for j, opt in enumerate(options[:5]):  # First 5 options
                    text = await opt.inner_text()
                    if text.strip():
                        print(f"    Option {j}: '{text.strip()}'")
            except:
                pass
        
        # Check for input fields
        inputs = await page.query_selector_all('input')
        print(f"\nFound {len(inputs)} input elements:")
        for i, inp in enumerate(inputs):
            try:
                placeholder = await inp.get_attribute('placeholder') or ''
                name = await inp.get_attribute('name') or ''
                if placeholder or name:
                    print(f"  Input {i}: placeholder='{placeholder}', name='{name}'")
            except:
                pass
        
        # Look specifically for "More filters" or similar
        print("\n🔍 Searching for 'More filters' specifically...")
        more_filters_texts = [
            'More filters', 'more filters', 'More Filters', 'MORE FILTERS',
            'Advanced filters', 'Filter options', 'Additional filters'
        ]
        
        for text in more_filters_texts:
            elements = await page.query_selector_all(f'text="{text}"')
            if elements:
                print(f"✅ Found element with text: '{text}'")
                for el in elements:
                    tag = await el.evaluate('el => el.tagName')
                    print(f"  Tag: {tag}")
            else:
                print(f"❌ No element found with text: '{text}'")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_filters())
