#!/usr/bin/env python3
"""Debug why pagination stops at page 8"""

import asyncio
import os
from playwright.async_api import async_playwright

USERNAME = os.getenv("SP_USERNAME")
PASSWORD = os.getenv("SP_PASSWORD")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.wait_for_timeout(2000)
        await page.fill('input[type="email"]', USERNAME)
        await page.fill('input[type="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        
        # Navigate to communities
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(3000)
        
        # Click to page 8
        print("Going to page 8...")
        for i in range(7):
            next_btn = await page.query_selector('button:has-text("Next")')
            if next_btn:
                await next_btn.click()
                await page.wait_for_timeout(2000)
                print(f"  Clicked to page {i+2}")
        
        # Now check the Next button on page 8
        print("\nChecking Next button on page 8:")
        next_btn = await page.query_selector('button:has-text("Next")')
        
        if not next_btn:
            print("  ❌ No Next button found!")
        else:
            print("  ✅ Next button found")
            
            # Check classes
            classes = await next_btn.get_attribute('class')
            print(f"  Classes: {classes}")
            
            # Check is_disabled logic
            is_disabled = await next_btn.evaluate('btn => btn.classList.contains("bg-gray-100") || btn.classList.contains("text-gray-300")')
            print(f"  is_disabled check: {is_disabled}")
            
            # Check if actually disabled
            disabled_attr = await next_btn.get_attribute('disabled')
            print(f"  disabled attribute: {disabled_attr}")
            
            # Get aria-disabled
            aria_disabled = await next_btn.get_attribute('aria-disabled')
            print(f"  aria-disabled: {aria_disabled}")
            
        print("\nPress Enter to close...")
        input()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

