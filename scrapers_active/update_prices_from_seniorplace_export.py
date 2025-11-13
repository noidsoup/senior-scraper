import os
import re
import csv
import argparse
import asyncio
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright


LOGIN_URL = "https://app.seniorplace.com/login"


def currency_to_number_str(value: str) -> str:
    if not value:
        return ""
    digits = re.sub(r"[^0-9.]+", "", str(value))
    return digits if digits and digits != "." else ""


# Senior Place → Canonical type mapping
TYPE_LABEL_MAP: Dict[str, str] = {
    "assisted living facility": "Assisted Living Community",
    "assisted living home": "Assisted Living Home",
    "independent living": "Independent Living",
    "memory care": "Memory Care",
    "skilled nursing": "Nursing Home",
    # Client-confirmed additions
    "continuing care retirement community": "Assisted Living Community",
    "in-home care": "Home Care",
    "home health": "Home Care",
    "hospice": "Home Care",
    "respite care": "Assisted Living Community",
}

# Canonical → WP Term ID (provided from CMS)
CANONICAL_TO_ID: Dict[str, int] = {
    "Assisted Living Community": 5,
    "Assisted Living Home": 162,
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    # New CMS type per client
    "Home Care": 488,
}


def php_serialize_int_array(ids: List[int]) -> str:
    # Build a PHP serialized array of integers: a:N:{i:0;i:ID0;i:1;i:ID1;}
    items = ''.join(f"i:{i};i:{ids[i]};" for i in range(len(ids)))
    return f"a:{len(ids)}:{{{items}}}"


def get_price_column_name(header: List[str]) -> str:
    for col in header:
        if col.strip().lower() == "price":
            return col
    raise Exception("No price column found in export")


def get_seniorplace_url(row: Dict[str, str]) -> Optional[str]:
    for key, value in row.items():
        val = (value or "").strip()
        if "seniorplace.com/communities/show/" in val:
            return val
    return None


async def click_attributes_tab(page) -> None:
    # Navigate directly to the attributes subpage for reliability
    current = page.url
    if not current.endswith('/attributes'):
        if current.endswith('/'):
            await page.goto(current + 'attributes', timeout=30000)
        else:
            await page.goto(current + '/attributes', timeout=30000)
    # Wait for the Finances header to ensure the section is rendered
    await page.wait_for_selector('text=Finances', timeout=20000)


async def get_input_value_by_label(page, label_text: str) -> str:
    # Find the label by visible text within the label group, then climb to the form-group and read the input
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
    """Scrape ALL label->value pairs from the Finances block without relying on exact selectors.
    Returns a dict with raw labels as keys (e.g., "Monthly Base Price")."""
    await page.wait_for_selector('text=Finances', timeout=20000)
    # Run in page context to walk the DOM efficiently
    data = await page.evaluate(
        """
        () => {
          const result = {};
          // Find the block that has the header 'Finances'
          const blocks = Array.from(document.querySelectorAll('div.input-form-block-no-bottom-margin'));
          const financeBlock = blocks.find(b => b.querySelector('.text-lg') && b.querySelector('.text-lg').textContent.trim().toLowerCase() === 'finances');
          if (!financeBlock) return result;
          // Each form-group typically has a label-group and an input
          const groups = Array.from(financeBlock.querySelectorAll('div.form-group'));
          for (const g of groups) {
            const labelDiv = g.querySelector('div.label-group div');
            const input = g.querySelector('input');
            if (!labelDiv || !input) continue;
            const rawLabel = (labelDiv.textContent || '').replace(/\u00A0/g, ' ').replace(/\s+/g, ' ').trim();
            const value = input.value || input.getAttribute('value') || '';
            if (rawLabel) {
              result[rawLabel] = value;
            }
          }
          return result;
        }
        """
    )
    return {k: currency_to_number_str(v) for k, v in (data or {}).items() if v}


async def scrape_types_block(page) -> Tuple[List[str], List[str]]:
    """Scrape checked community types; return (canonical_names, raw_labels)."""
    await page.wait_for_selector('text=Community Type', timeout=20000)
    types = await page.evaluate(
        """
        () => {
          const out = [];
          // Find the section that contains 'Community Type(s)'
          const labels = Array.from(document.querySelectorAll('label.inline-flex'));
          for (const label of labels) {
            const textEl = label.querySelector('div.ml-2');
            const input = label.querySelector('input[type="checkbox"]');
            if (!textEl || !input) continue;
            if (!input.checked) continue;
            const name = (textEl.textContent || '').trim();
            if (name) out.push(name);
          }
          return out;
        }
        """
    )
    # Map to canonical
    canonical: List[str] = []
    for t in (types or []):
        key = t.strip().lower()
        mapped = TYPE_LABEL_MAP.get(key)
        if mapped and mapped not in canonical:
            canonical.append(mapped)
    return canonical, (types or [])


async def scrape_finances(context, url: str) -> Dict[str, str]:
    labels = [
        # Core
        "Monthly Base Price",
        "Price (High End)",
        "Second Person Fee",
        "Pet Deposit",
        "Pet Deposit (if applicable)",
        # Assisted Living Community
        "Assisted Living -- Price (low)",
        "Assisted Living -- Price (high)",
        "Assisted Living -- One Bedroom Price (low)",
        "Assisted Living -- One Bedroom Price (high)",
        "Assisted Living -- Two Bedroom Price (low)",
        "Assisted Living -- Two Bedroom Price (high)",
        # Assisted Living Home
        "Assisted Living Home -- Price (low)",
        "Assisted Living Home -- Price (high)",
        # Independent Living
        "Independent Living -- Price (low)",
        "Independent Living -- Price (high)",
        "Independent Living -- One Bedroom Price (low)",
        "Independent Living -- One Bedroom Price (high)",
        "Independent Living -- Two Bedroom Price (low)",
        "Independent Living -- Two Bedroom Price (high)",
        # Memory Care
        "Memory Care -- Price (low)",
        "Memory Care -- Price (high)",
        # Care level range (optional)
        "AL Care Levels (low)",
        "AL Care Levels (high)",
    ]

    result: Dict[str, str] = {}
    page = await context.new_page()
    try:
        print(f"[LOAD] {url}")
        await page.goto(url, timeout=30000)
        await click_attributes_tab(page)
        # Try generic block scrape first
        try:
            block = await scrape_finances_block(page)
            if block:
                for label, val in block.items():
                    key = re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_")
                    result[key] = val
                    print(f"  [FIELD] {label} → {val}")
        except Exception as e:
            print(f"  [DEBUG] Block scrape failed: {e}")
        # Scrape and attach types
        try:
            canonical_types, raw_types = await scrape_types_block(page)
            if canonical_types:
                result["normalized_types"] = ", ".join(canonical_types)
                result["normalized_type_ids"] = ", ".join(str(CANONICAL_TO_ID[c]) for c in canonical_types if c in CANONICAL_TO_ID)
            if raw_types:
                result["raw_types"] = ", ".join(raw_types)
        except Exception as e:
            print(f"  [DEBUG] Type scrape failed: {e}")
        for label in labels:
            try:
                val = await get_input_value_by_label(page, label)
                if val:
                    key = re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_")
                    result[key] = val
                    print(f"  [FIELD] {label} → {val}")
            except Exception as e:
                pass
        return result
    except Exception as e:
        print(f"[ERROR] scrape_finances failed: {e}")
        return result
    finally:
        await page.close()


def choose_lowest_price(finance: Dict[str, str], include_care_levels: bool) -> Optional[Tuple[str, str]]:
    """Return (price_str, source_key) using a strict whitelist suitable for 'starting at'.
    Priority: monthly_base_price → lowest of allowed *_price_low fields.
    Excludes: second_person_fee, deposits, fees, care levels, and any *_price_high.
    """
    # 1) Prefer explicit monthly base price
    base = finance.get("monthly_base_price")
    if base and base.strip():
        try:
            _ = int(float(base))
            return (str(_), "monthly_base_price")
        except Exception:
            pass

    # 2) Consider only allowed low-price fields
    allowed_prefixes = [
        "independent_living",
        "assisted_living_home",
        "assisted_living",
        "memory_care",
    ]
    allowed_suffix = "price_low"

    candidates: List[Tuple[str, int]] = []  # (key, value)
    for k, v in finance.items():
        if not v:
            continue
        # skip obvious non-base costs
        if "second_person" in k or "deposit" in k or "fee" in k:
            continue
        if "care_levels" in k and not include_care_levels:
            continue
        # accept keys like assisted_living_price_low, assisted_living_studio_price_low, etc.
        if any(k.startswith(pref) for pref in allowed_prefixes) and k.endswith(allowed_suffix):
            try:
                candidates.append((k, int(float(v))))
            except Exception:
                continue

    if not candidates:
        return None
    best_key, best_val = min(candidates, key=lambda kv: kv[1])
    return (str(best_val), best_key)


async def run(args):
    headless = not args.headful
    username = args.username or os.getenv("SENIORPLACE_USER")
    password = args.password or os.getenv("SENIORPLACE_PASS")
    if not username or not password:
        raise RuntimeError("Missing Senior Place credentials. Pass --username/--password or set SENIORPLACE_USER/SENIORPLACE_PASS env vars.")

    # Read WP export
    with open(args.input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = list(reader)
        header = reader.fieldnames or []

    price_col = get_price_column_name(header)
    # Ensure helper columns exist so we can write normalized types safely
    for extra_col in ["normalized_types", "normalized_type_ids", "raw_types"]:
        if extra_col not in header:
            header.append(extra_col)
    print(f"Loaded {len(rows)} rows from {args.input}; price column: '{price_col}'")

    updated = 0
    processed = 0
    kept_existing = 0
    no_url = 0
    no_finances = 0
    type_updates = 0
    type_serialized_updates = 0
    changes_log: List[Dict[str, str]] = []
    type_changes_log: List[Dict[str, str]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()

        # Login once
        print("Logging in to Senior Place…")
        page = await context.new_page()
        await page.goto(LOGIN_URL)
        await page.fill('#email', username)
        await page.fill('#password', password)
        await page.click('#signin')
        await page.wait_for_selector('text=Communities', timeout=20000)
        await page.close()
        print("Login successful.")

        for idx, row in enumerate(rows, start=1):
            if args.max and processed >= args.max:
                break
            processed += 1
            url = get_seniorplace_url(row)
            title = row.get("Title") or row.get("title") or "(no title)"
            rid = row.get("ID") or row.get("id") or "?"
            print(f"\n[{processed}] ID={rid} Title={title}")

            if not url:
                print("  [SKIP] No Senior Place URL found in row.")
                no_url += 1
                continue

            print(f"  [URL] {url}")

            try:
                finance = await scrape_finances(context, url)
                if not finance:
                    print("  [WARN] No finance fields found.")
                    no_finances += 1
                # Write normalized types even if finance is empty or price not derived
                if finance.get("normalized_types") or finance.get("raw_types"):
                    if args.print_normalized_types:
                        print(f"  [TYPES] SeniorPlace: {finance.get('raw_types','')}  →  Normalized: {finance.get('normalized_types','')}  (IDs: {finance.get('normalized_type_ids','')})")
                    row["normalized_types"] = finance["normalized_types"]
                    row["normalized_type_ids"] = finance.get("normalized_type_ids", "")
                    row["raw_types"] = finance.get("raw_types", "")
                    type_updates += 1
                    if args.write_type_ids_into:
                        try:
                            id_list = [int(x) for x in finance.get("normalized_type_ids", "").split(',') if x.strip()]
                            if id_list:
                                serialized = php_serialize_int_array(id_list)
                                old_serialized = row.get(args.write_type_ids_into, "")
                                row[args.write_type_ids_into] = serialized
                                type_serialized_updates += 1
                                print(f"  [TYPES] Wrote {serialized} into column '{args.write_type_ids_into}'")
                                type_changes_log.append({
                                    "ID": str(rid),
                                    "Title": str(title),
                                    "URL": url,
                                    "OldSerialized": old_serialized,
                                    "NormalizedTypes": row.get("normalized_types", ""),
                                    "NormalizedTypeIDs": row.get("normalized_type_ids", ""),
                                    "SerializedWritten": serialized,
                                })
                        except Exception as e:
                            print(f"  [TYPES] Could not serialize types: {e}")
                    else:
                        # Log normalized types even if we didn't serialize
                        type_changes_log.append({
                            "ID": str(rid),
                            "Title": str(title),
                            "URL": url,
                            "OldSerialized": row.get('_type', ''),
                            "NormalizedTypes": row.get("normalized_types", ""),
                            "NormalizedTypeIDs": row.get("normalized_type_ids", ""),
                            "SerializedWritten": "",
                        })
                decision = choose_lowest_price(finance, include_care_levels=args.include_care_levels)
                lowest, source = (decision[0], decision[1]) if decision else (None, None)
                print(f"  [DECIDE] Lowest price{' (incl care levels)' if args.include_care_levels else ''}: {lowest}  [from: {source}]")

                if lowest is None:
                    print("  [SKIP] Could not derive lowest price.")
                    continue

                existing = (row.get(price_col) or "").strip()
                if existing and not args.force:
                    print(f"  [KEEP] Existing price present ('{existing}'); use --force to overwrite.")
                    kept_existing += 1
                    continue

                row[price_col] = lowest
                updated += 1
                print(f"  [WRITE] Set {price_col} → {lowest}")
                changes_log.append({
                    "ID": str(rid),
                    "Title": str(title),
                    "URL": url,
                    "OldPrice": existing,
                    "NewPrice": lowest,
                    "Source": source or "",
                })

                # (Types already written above)
            except Exception as e:
                print(f"  [ERROR] {e}")

        await browser.close()

    # Write output
    out_path = args.output or os.path.splitext(args.input)[0] + "_with_prices.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    # Write updates log CSV next to output
    log_path = os.path.splitext(out_path)[0] + "_updates_log.csv"
    if changes_log:
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ID", "Title", "URL", "OldPrice", "NewPrice", "Source"])
            writer.writeheader()
            writer.writerows(changes_log)

    type_log_path = os.path.splitext(out_path)[0] + "_type_updates_log.csv"
    if type_changes_log:
        with open(type_log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ID", "Title", "URL", "OldSerialized", "NormalizedTypes", "NormalizedTypeIDs", "SerializedWritten"])
            writer.writeheader()
            writer.writerows(type_changes_log)

    print(f"\nUpdated {updated} of {processed} processed rows → {out_path}")
    print(f"Kept existing (not overwritten): {kept_existing}")
    print(f"Skipped: no Senior Place URL = {no_url}, no finance fields = {no_finances}")
    if type_updates:
        print(f"Normalized types written for {type_updates} updated rows (columns: normalized_types, normalized_type_ids)")
    if type_serialized_updates:
        print(f"Also updated '{args.write_type_ids_into}' with PHP-serialized IDs for {type_serialized_updates} rows")
    if changes_log:
        print(f"Update details: {log_path}")
    if type_changes_log:
        print(f"Type update details: {type_log_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update WP All Export CSV prices by scraping Senior Place Attributes → Finances.")
    parser.add_argument("--input", required=True, help="Path to WP All Export CSV.")
    parser.add_argument("--output", required=False, help="Output CSV path (default: adds _with_prices suffix).")
    parser.add_argument("--username", required=False, help="Senior Place email (or SENIORPLACE_USER env var).")
    parser.add_argument("--password", required=False, help="Senior Place password (or SENIORPLACE_PASS env var).")
    parser.add_argument("--headful", action="store_true", help="Run Chromium headful for debugging.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing price values.")
    parser.add_argument("--max", type=int, default=0, help="Process at most N rows (0 = all).")
    parser.add_argument("--include-care-levels", action="store_true", help="Allow AL Care Level fees to be considered for the minimum price.")
    parser.add_argument("--write-type-ids-into", required=False, default=None, help="Column name to overwrite with PHP-serialized taxonomy IDs (e.g., '_type').")
    parser.add_argument("--print-normalized-types", action="store_true", help="Print human-readable normalized types in terminal logs.")
    return parser


if __name__ == "__main__":
    asyncio.run(run(build_arg_parser().parse_args()))


