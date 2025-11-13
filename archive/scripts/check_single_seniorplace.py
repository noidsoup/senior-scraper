import os
import re
import argparse
import asyncio
from typing import Dict, List, Optional
from playwright.async_api import async_playwright


LOGIN_URL = "https://app.seniorplace.com/login"


def currency_to_number_str(value: str) -> str:
    if not value:
        return ""
    digits = re.sub(r"[^0-9.]+", "", str(value))
    return digits if digits and digits != "." else ""


async def click_attributes_tab(page) -> None:
    current = page.url
    if not current.endswith('/attributes'):
        if current.endswith('/'):
            await page.goto(current + 'attributes', timeout=30000)
        else:
            await page.goto(current + '/attributes', timeout=30000)
    await page.wait_for_selector('text=Finances', timeout=20000)


async def get_input_value_by_label(page, label_text: str) -> str:
    label = page.locator("div.form-group div.label-group div", has_text=label_text).first
    if not await label.count():
        return ""
    group = label.locator("xpath=ancestor::div[contains(@class,'form-group')][1]")
    input_el = group.locator('input').first
    if not await input_el.count():
        return ""
    try:
        value = await input_el.input_value()
    except Exception:
        value = await input_el.get_attribute('value')
    return currency_to_number_str(value or "")


async def scrape_finances_block(page) -> Dict[str, str]:
    await page.wait_for_selector('text=Finances', timeout=20000)
    data = await page.evaluate(
        """
        () => {
          const result = {};
          const blocks = Array.from(document.querySelectorAll('div.input-form-block-no-bottom-margin'));
          const financeBlock = blocks.find(b => b.querySelector('.text-lg') && b.querySelector('.text-lg').textContent.trim().toLowerCase() === 'finances');
          if (!financeBlock) return result;
          const groups = Array.from(financeBlock.querySelectorAll('div.form-group'));
          for (const g of groups) {
            const labelDiv = g.querySelector('div.label-group div');
            const input = g.querySelector('input');
            if (!labelDiv || !input) continue;
            const rawLabel = (labelDiv.textContent || '').replace(/\u00A0/g, ' ').replace(/\s+/g, ' ').trim();
            const value = input.value || input.getAttribute('value') || '';
            if (rawLabel) result[rawLabel] = value;
          }
          return result;
        }
        """
    )
    return {k: currency_to_number_str(v) for k, v in (data or {}).items() if v}


async def scrape_finances(context, url: str) -> Dict[str, str]:
    labels = [
        "Monthly Base Price",
        "Price (High End)",
        "Second Person Fee",
        "Pet Deposit",
        "Pet Deposit (if applicable)",
        "Assisted Living -- Price (low)",
        "Assisted Living -- Price (high)",
        "Assisted Living -- One Bedroom Price (low)",
        "Assisted Living -- One Bedroom Price (high)",
        "Assisted Living -- Two Bedroom Price (low)",
        "Assisted Living -- Two Bedroom Price (high)",
        "Assisted Living Home -- Price (low)",
        "Assisted Living Home -- Price (high)",
        "Independent Living -- Price (low)",
        "Independent Living -- Price (high)",
        "Independent Living -- One Bedroom Price (low)",
        "Independent Living -- One Bedroom Price (high)",
        "Independent Living -- Two Bedroom Price (low)",
        "Independent Living -- Two Bedroom Price (high)",
        "Memory Care -- Price (low)",
        "Memory Care -- Price (high)",
        "AL Care Levels (low)",
        "AL Care Levels (high)",
    ]

    result: Dict[str, str] = {}
    page = await context.new_page()
    try:
        print(f"[LOAD] {url}")
        await page.goto(url, timeout=30000)
        await click_attributes_tab(page)
        for label in labels:
            try:
                val = await get_input_value_by_label(page, label)
                key = re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_")
                result[key] = val
                print(f"  {label:55s} → {val}")
            except Exception as e:
                print(f"  {label:55s} → (error: {e})")
        return result
    finally:
        await page.close()


def choose_lowest(finance: Dict[str, str], include_care_levels: bool) -> Optional[str]:
    values: List[int] = []
    for k, v in finance.items():
        if not v:
            continue
        if not include_care_levels and "care_levels" in k:
            continue
        try:
            values.append(int(float(v)))
        except Exception:
            pass
    return str(min(values)) if values else None


async def run(args):
    headless = not args.headful
    username = args.username or os.getenv("SENIORPLACE_USER")
    password = args.password or os.getenv("SENIORPLACE_PASS")
    if not username or not password:
        raise RuntimeError("Missing Senior Place credentials. Pass --username/--password or set SENIORPLACE_USER/SENIORPLACE_PASS env vars.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()

        # Login
        page = await context.new_page()
        print("Logging in…")
        await page.goto(LOGIN_URL)
        await page.fill('#email', username)
        await page.fill('#password', password)
        await page.click('#signin')
        await page.wait_for_selector('text=Communities', timeout=20000)
        await page.close()
        print("Login OK")

        # Try block scrape first for visibility
        page = await context.new_page()
        await page.goto(args.url, timeout=30000)
        await click_attributes_tab(page)
        block = await scrape_finances_block(page)
        if block:
            print("\n[ALL FIELDS]")
            for k, v in block.items():
                print(f"  {k:55s} → {v}")
        await page.close()

        finance = await scrape_finances(context, args.url)
        lowest = choose_lowest(finance, include_care_levels=args.include_care_levels)
        print(f"\nLowest derived price{' (incl care levels)' if args.include_care_levels else ''}: {lowest}")

        await browser.close()


def build_parser():
    parser = argparse.ArgumentParser(description="Check a single Senior Place listing's Finances and compute lowest price.")
    parser.add_argument("--url", required=True, help="Senior Place listing URL (communities/show/…)")
    parser.add_argument("--headful", action="store_true", help="Run headful for debugging")
    parser.add_argument("--include-care-levels", action="store_true", help="Include AL Care Levels in lowest calc")
    parser.add_argument("--username", required=False)
    parser.add_argument("--password", required=False)
    return parser


if __name__ == "__main__":
    asyncio.run(run(build_parser().parse_args()))


