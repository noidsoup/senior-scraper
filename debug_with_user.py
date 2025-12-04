#!/usr/bin/env python3
"""
Open Senior Place in browser to debug with user
"""

import asyncio
from playwright.async_api import async_playwright

import os
USERNAME = os.getenv("SP_USERNAME", "")
PASSWORD = os.getenv("SP_PASSWORD", "")

if not USERNAME or not PASSWORD:
    print("❌ Error: Set SP_USERNAME and SP_PASSWORD environment variables")
    exit(1)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', USERNAME)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        
        # Go to communities
        print("📍 Opening communities page...")
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(3000)
        
        print("\n✅ Browser open - will stay open for 5 minutes")
        print("Navigate around, check pagination, etc.")
        await page.wait_for_timeout(300000)  # 5 minutes
        
        await browser.close()

asyncio.run(main())

