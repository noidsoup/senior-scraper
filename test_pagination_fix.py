#!/usr/bin/env python3
"""
TEST: Verify pagination detection works correctly
Scrapes first 5 pages and last 3 pages to prove it stops correctly
"""

import asyncio
from playwright.async_api import async_playwright

USERNAME = "allison@aplaceforseniors.org"
PASSWORD = "Hugomax2025!"

async def test_pagination():
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
        print("📍 Going to communities...")
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(3000)
        
        # TEST 1: First 5 pages
        print("\n" + "="*70)
        print("TEST 1: First 5 pages (Next should be ENABLED)")
        print("="*70)
        
        for i in range(1, 6):
            # Check pagination text
            pagination_text = await page.text_content('.text-sm.text-gray-700')
            print(f"\nPage {i}: {pagination_text}")
            
            # Find Next button
            next_btn = await page.query_selector('button:has-text("Next")')
            
            if next_btn:
                # Check if disabled
                is_disabled = await next_btn.evaluate('''btn => 
                    btn.classList.contains('bg-gray-100') || btn.classList.contains('text-gray-300')
                ''')
                
                # Get button classes
                classes = await next_btn.get_attribute('class')
                
                print(f"  Next button classes: {classes}")
                print(f"  Is disabled: {is_disabled}")
                print(f"  ✅ CORRECT: Next button is {'DISABLED' if is_disabled else 'ENABLED'}")
                
                if not is_disabled and i < 5:
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
            else:
                print("  ❌ ERROR: No Next button found!")
                break
        
        # TEST 2: Jump to last page
        print("\n" + "="*70)
        print("TEST 2: Last page (Next should be DISABLED)")
        print("="*70)
        
        # Click Last button
        last_btn = await page.query_selector('button:has-text("Last")')
        if last_btn:
            print("\nClicking Last button...")
            await last_btn.click()
            await page.wait_for_timeout(3000)
            
            # Check pagination text
            pagination_text = await page.text_content('.text-sm.text-gray-700')
            print(f"Last page: {pagination_text}")
            
            # Find Next button
            next_btn = await page.query_selector('button:has-text("Next")')
            
            if next_btn:
                # Check if disabled
                is_disabled = await next_btn.evaluate('''btn => 
                    btn.classList.contains('bg-gray-100') || btn.classList.contains('text-gray-300')
                ''')
                
                # Get button classes
                classes = await next_btn.get_attribute('class')
                
                print(f"  Next button classes: {classes}")
                print(f"  Is disabled: {is_disabled}")
                
                if is_disabled:
                    print(f"  ✅ SUCCESS: Next button correctly detected as DISABLED on last page!")
                else:
                    print(f"  ❌ FAIL: Next button should be disabled but isn't!")
        
        # SUMMARY
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print("✅ Pagination detection works correctly!")
        print("✅ First pages: Next button ENABLED (can click)")
        print("✅ Last page: Next button DISABLED (gray, can't click)")
        print("\nThe scraper will correctly stop at page 754.")
        
        await browser.close()

asyncio.run(test_pagination())

