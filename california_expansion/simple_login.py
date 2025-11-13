#!/usr/bin/env python3
"""
Simple login script - just logs in and opens the communities page
"""
import asyncio
import os
from playwright.async_api import async_playwright

async def simple_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.wait_for_timeout(2000)
        
        await page.fill('#email', os.getenv("SP_USERNAME", ""))
        await page.fill('#password', os.getenv("SP_PASSWORD", ""))
        await page.click('#signin')
        await page.wait_for_timeout(5000)
        
        # Go to communities page
        print("🏠 Opening communities page...")
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(3000)
        
        print("✅ Ready! You can now manually select the California filter.")
        print("⏳ Browser will stay open for you to interact with...")
        print("   Press Ctrl+C to close when done")
        
        # Keep browser open indefinitely with a loop
        try:
            while True:
                await page.wait_for_timeout(1000)
        except KeyboardInterrupt:
            print("\n👋 Closing browser...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(simple_login())
