import csv
import asyncio
import re
from typing import Dict, List
from playwright.async_api import async_playwright

INPUT_CSV = 'Listings_Export_2025_June_26_2013_cleaned.csv'
OUTPUT_CSV = 'Listings_Export_2025_June_26_2013_cleaned_with_prices.csv'
import os
LOGIN_URL = 'https://app.seniorplace.com/login'
USERNAME = os.getenv('SENIORPLACE_USER')
PASSWORD = os.getenv('SENIORPLACE_PASS')

# Selector for the Monthly Base Price input on the Attributes tab
MONTHLY_BASE_PRICE_SELECTOR = 'input[aria-label="Monthly Base Price"]'

# Labels we will try to extract from the Finances section on the Attributes tab.
# This list is intentionally broad to handle communities that expose different sets of fields.
FINANCE_LABELS = {
    # Top-level finance fields
    "Monthly Base Price": "monthly_base_price",
    "Price (High End)": "price_high_end",
    "Second Person Fee": "second_person_fee",
    "Pet Deposit": "pet_deposit",
    "Pet Deposit (if applicable)": "pet_deposit",

    # Common ranges
    "AL Care Levels (low)": "al_care_levels_low",
    "AL Care Levels (high)": "al_care_levels_high",

    # Assisted Living Community ranges
    "Assisted Living -- Price (low)": "assisted_living_price_low",
    "Assisted Living -- Price (high)": "assisted_living_price_high",
    "Assisted Living -- One Bedroom Price (low)": "assisted_living_1br_price_low",
    "Assisted Living -- One Bedroom Price (high)": "assisted_living_1br_price_high",
    "Assisted Living -- Two Bedroom Price (low)": "assisted_living_2br_price_low",
    "Assisted Living -- Two Bedroom Price (high)": "assisted_living_2br_price_high",

    # Assisted Living Home ranges (some properties use this phrasing)
    "Assisted Living Home -- Price (low)": "assisted_living_home_price_low",
    "Assisted Living Home -- Price (high)": "assisted_living_home_price_high",

    # Independent Living ranges
    "Independent Living -- Price (low)": "independent_living_price_low",
    "Independent Living -- Price (high)": "independent_living_price_high",
    "Independent Living -- One Bedroom Price (low)": "independent_living_1br_price_low",
    "Independent Living -- One Bedroom Price (high)": "independent_living_1br_price_high",
    "Independent Living -- Two Bedroom Price (low)": "independent_living_2br_price_low",
    "Independent Living -- Two Bedroom Price (high)": "independent_living_2br_price_high",

    # Memory Care ranges
    "Memory Care -- Price (low)": "memory_care_price_low",
    "Memory Care -- Price (high)": "memory_care_price_high",
}

# Checkbox/boolean flags (labels shown on page)
FINANCE_CHECKBOXES = {
    "Accepts ALTCS": "accepts_altcs",
    "Has Medicaid Contract": "has_medicaid_contract",
    "Offers Affordable / Low-Income Options": "offers_affordable_low_income",
}

# Simple textarea notes
FINANCE_TEXTAREAS = {
    "Community Fee Notes": "community_fee_notes",
    "Other Pricing Notes": "other_pricing_notes",
}

# Spend-down options list (multi-select via checkboxes)
SPEND_DOWN_OPTIONS = [
    "2+ years Private Pay",
    "1+ year Private Pay",
    "6+ months Private Pay",
    "Direct Medicaid",
]

# Helper to find the Senior Place link in a row
def get_seniorplace_url(row):
    for key in row:
        val = row[key] or ''
        if 'seniorplace.com/communities/show/' in val:
            return val.strip()
    return None

def get_price_column_name(header):
    # Find the column that is exactly 'price' (case-insensitive)
    for col in header:
        if col.strip().lower() == 'price':
            return col
    raise Exception('No price column found!')

async def scrape_price(context, url):
    print(f"[DEBUG] Processing: {url}")
    page = await context.new_page()
    try:
        await page.goto(url, timeout=20000)
        print("[DEBUG] Navigated to page")
        await page.wait_for_timeout(1000)  # Let the page settle
        await page.wait_for_selector('a[data-subpage="attributes"]', timeout=15000)
        print("[DEBUG] Found Attributes tab selector")
        # Try/catch the click in case the tab is already active or not clickable
        try:
            await page.click('a[data-subpage="attributes"]', timeout=5000)
            print("[DEBUG] Clicked Attributes tab")
        except Exception as e:
            print(f"[DEBUG] Could not click Attributes tab: {e}")
        await page.wait_for_selector('//div[contains(@class, "form-group")]//div[contains(text(), "Monthly Base Price")]', timeout=15000)
        print("[DEBUG] Found Monthly Base Price label")
        label = await page.query_selector('//div[contains(@class, "form-group")]//div[contains(text(), "Monthly Base Price")]')
        if label:
            group = await label.evaluate_handle('el => el.closest(".form-group")')
            price_input = await group.query_selector('input')
            if price_input:
                value = await price_input.get_attribute('value')
                print(f"[DEBUG] Extracted value: {value}")
                if value and value.strip().replace('$','').replace(',','').isdigit():
                    return value.strip()
                else:
                    print("[DEBUG] Value is empty or not a number")
            else:
                print("[DEBUG] Could not find input for Monthly Base Price")
        else:
            print("[DEBUG] Could not find label for Monthly Base Price")
    except Exception as e:
        print(f"[DEBUG] Exception in scrape_price: {e}")
    finally:
        await page.close()
    return None


def currency_to_number_str(value: str) -> str:
    """Convert currency-ish text like "$4,495" to a plain numeric string like "4495".
    Returns empty string when not parseable."""
    if not value:
        return ""
    value = value.strip()
    # Some fields might already be numeric
    digits = re.sub(r"[^0-9\.]+", "", value)
    # Avoid returning just "." or empty
    if not digits or digits == ".":
        return ""
    # Strip leading zeros responsibly
    # Keep decimals if present (rare for these fields, but safe)
    return digits


async def click_attributes_tab(page) -> None:
    await page.wait_for_selector('a[data-subpage="attributes"]', timeout=15000)
    try:
        await page.click('a[data-subpage="attributes"]', timeout=5000)
    except Exception:
        pass
    await page.wait_for_timeout(500)


async def get_input_value_by_label(page, label_text: str) -> str:
    # Find the closest .form-group for a label div containing the text
    xpath = (
        f"//div[contains(@class,'form-group')]//div[contains(@class,'label-group')]"
        f"//div[normalize-space()[contains(., '{label_text}')]]/ancestor::div[contains(@class,'form-group')][1]"
    )
    group = await page.query_selector(xpath)
    if not group:
        return ""
    input_el = await group.query_selector('input')
    if not input_el:
        return ""
    value = await input_el.get_attribute('value')
    return currency_to_number_str(value or "")


async def get_textarea_value_by_label(page, label_text: str) -> str:
    # Locate label text and then the nearest textarea
    xpath = (
        f"//label[.//div[normalize-space()[contains(., '{label_text}')]]]"
    )
    label_node = await page.query_selector(xpath)
    if not label_node:
        return ""
    textarea = await label_node.query_selector('textarea')
    if not textarea:
        return ""
    value = await textarea.input_value()
    return (value or "").strip()


async def get_checkbox_checked_by_label(page, label_text: str) -> str:
    # Find input[type=checkbox] whose sibling label text contains the label
    xpath = (
        f"//label[contains(@class,'inline-flex')][.//div[contains(normalize-space(), '{label_text}')]]//input[@type='checkbox']"
    )
    node = await page.query_selector(xpath)
    if not node:
        return ""
    checked = await node.is_checked()
    return "1" if checked else "0"


async def get_spend_down_selected(page) -> List[str]:
    selected: List[str] = []
    for option in SPEND_DOWN_OPTIONS:
        xpath = (
            f"//div[contains(@class,'options')]//label[contains(@class,'inline-flex')][.//div[contains(normalize-space(), '{option}')]]//input[@type='checkbox']"
        )
        node = await page.query_selector(xpath)
        if not node:
            continue
        if await node.is_checked():
            selected.append(option)
    return selected


async def scrape_finances(context, url) -> Dict[str, str]:
    """Scrape a wide set of finance fields from the Attributes tab.
    Returns a dict of normalized column_name -> value (strings)."""
    page = await context.new_page()
    results: Dict[str, str] = {}
    try:
        await page.goto(url, timeout=25000)
        await click_attributes_tab(page)

        # Inputs by label
        for label, key in FINANCE_LABELS.items():
            try:
                value = await get_input_value_by_label(page, label)
                if value != "":
                    results[key] = value
            except Exception:
                continue

        # Textareas
        for label, key in FINANCE_TEXTAREAS.items():
            try:
                value = await get_textarea_value_by_label(page, label)
                if value:
                    results[key] = value
            except Exception:
                continue

        # Checkboxes
        for label, key in FINANCE_CHECKBOXES.items():
            try:
                value = await get_checkbox_checked_by_label(page, label)
                if value != "":
                    results[key] = value
            except Exception:
                continue

        # Spend-down multi-select
        try:
            selected = await get_spend_down_selected(page)
            if selected:
                results["accepted_spend_down_periods"] = ", ".join(selected)
        except Exception:
            pass

    except Exception as e:
        print(f"[DEBUG] Exception in scrape_finances: {e}")
    finally:
        await page.close()

    return results

async def main():
    updated = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        # Login once
        page = await context.new_page()
        if not USERNAME or not PASSWORD:
            raise RuntimeError("Missing Senior Place credentials. Set SENIORPLACE_USER and SENIORPLACE_PASS env vars before running.")
        await page.goto(LOGIN_URL)
        await page.fill('#email', USERNAME)
        await page.fill('#password', PASSWORD)
        await page.click('#signin')
        await page.wait_for_selector('text=Communities', timeout=15000)
        await page.close()

        # Read CSV
        with open(INPUT_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            header = reader.fieldnames
            if header is None and rows:
                header = list(rows[0].keys())
            if header is not None:
                header = [str(h) for h in header]
            else:
                header = []
        price_col = get_price_column_name(header)

        # Ensure our finance columns exist in the header (append if missing)
        extra_columns = sorted(set(list(FINANCE_LABELS.values()) + list(FINANCE_CHECKBOXES.values()) + list(FINANCE_TEXTAREAS.values()) + ["accepted_spend_down_periods"]))
        for col in extra_columns:
            if col not in header:
                header.append(col)

        for row in rows:
            url = get_seniorplace_url(row)
            if not url:
                continue

            # Always try to scrape finances; this fills many columns. Use best-effort.
            finance = await scrape_finances(context, url)
            for k, v in finance.items():
                row[k] = v

            # Backfill the generic price column from Monthly Base Price when missing
            if (not row.get(price_col) or str(row.get(price_col)).strip() == '') and finance.get('monthly_base_price'):
                row[price_col] = finance['monthly_base_price']
                updated.append({'ID': row.get('ID', ''), 'Title': row.get('Title', ''), 'URL': url, 'Price': finance['monthly_base_price']})

        await browser.close()

        # Write new CSV
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)

    # Print summary
    print(f"\nUpdated {len(updated)} listings with new prices:")
    for u in updated:
        print(f"ID: {u['ID']}, Title: {u['Title']}, URL: {u['URL']}, Price: {u['Price']}")

if __name__ == '__main__':
    asyncio.run(main()) 