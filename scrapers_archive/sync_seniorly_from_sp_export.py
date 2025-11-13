#!/usr/bin/env python3
"""
Generate a CSV to update Seniorly listings' community types based on Senior Place export.

Inputs:
- organized_csvs/02_CURRENT_SITE_STATE_BACKUP.csv  (current site state; detect Seniorly via `website`)
- organized_csvs/seniorplace_data_export.csv       (original Senior Place export; join by title)

Output:
- organized_csvs/CARE_TYPE_SYNC_<timestamp>.csv with columns:
  ID, Title, seniorplace_url, seniorly_url, seniorplace_types, normalized_types

Notes:
- Title match uses a normalized form (lowercased, alnum + space only, collapsed spaces)
- Senior Place types are mapped to canonical categories using our approved mapping
"""

import csv
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Tuple


# File paths (absolute for clarity)
REPO_ROOT = "/Users/nicholas/Repos/senior-scrapr"
CURRENT_CSV = os.path.join(REPO_ROOT, "organized_csvs", "02_CURRENT_SITE_STATE_BACKUP.csv")
SP_EXPORT_CSV = os.path.join(REPO_ROOT, "organized_csvs", "seniorplace_data_export.csv")
SP_VS_SR_BY_TITLE = os.path.join(REPO_ROOT, "organized_csvs", "SENIORPLACE_VS_SENIORLY_DUPES.csv")


# Our canonical mapping system (Senior Place -> Canonical CMS Type)
SENIORPLACE_TO_CANONICAL: Dict[str, str] = {
    "Independent Living": "Independent Living",
    "Assisted Living Facility": "Assisted Living Community",
    "Assisted Living Home": "Assisted Living Home",
    "Memory Care": "Memory Care",
    "Skilled Nursing": "Nursing Home",
    "Continuing Care Retirement Community": "Assisted Living Community",
    "In-Home Care": "Home Care",
    "Home Health": "Home Care",
    "Hospice": "Home Care",
    "Respite Care": "Assisted Living Community",
    "Board and Care Home": "Assisted Living Home",
    "Board And Care Home": "Assisted Living Home",
    "Adult Care Home": "Assisted Living Home",
}


def normalize_title(value: str) -> str:
    """Normalize a title for matching: lowercase, alnum+space, single spaces."""
    if not value:
        return ""
    value = value.lower()
    # keep letters/numbers/spaces
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    # collapse whitespace
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_sp_types(raw: str) -> List[str]:
    if not raw:
        return []
    # Split on commas and strip whitespace
    return [part.strip() for part in raw.split(",") if part.strip()]


def map_to_canonical(types: List[str]) -> List[str]:
    canonical: List[str] = []
    for t in types:
        mapped = SENIORPLACE_TO_CANONICAL.get(t, t)
        if mapped and mapped not in canonical:
            canonical.append(mapped)
    return canonical


def normalize_url_for_match(url: str) -> str:
    """Normalize URL for exact-match lookups: lowercase, strip trailing slash, trim."""
    u = (url or "").strip().lower()
    if u.endswith('/'):
        u = u[:-1]
    return u


def sanitize_row_keys(row: Dict[str, str]) -> Dict[str, str]:
    """Return a copy with BOM removed from first key if present and keys stripped of whitespace."""
    return { (k.lstrip("\ufeff").strip() if isinstance(k, str) else k): v for k, v in row.items() }


def load_seniorplace_index(path: str) -> Dict[str, Tuple[str, str, str]]:
    """Return dict: normalized_title -> (seniorplace_types_raw, seniorplace_url, seniorly_url_if_present).

    Some rows in the export may have Seniorly URLs in the `url` field; prefer app.seniorplace.com when available.
    """
    index: Dict[str, Tuple[str, str, str]] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Expected columns: title, type, url
        for row in reader:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            norm = normalize_title(title)
            types_raw = (row.get("type") or "").strip()
            url_field = (row.get("url") or "").strip()
            seniorplace_url = url_field
            seniorly_url = ""
            # Heuristic: if the url looks like Seniorly, keep it separately, and leave seniorplace_url blank
            if url_field:
                if "app.seniorplace.com" in url_field:
                    seniorplace_url = url_field
                elif "seniorly.com" in url_field:
                    seniorly_url = url_field
                    seniorplace_url = ""
            # Prefer first seen with non-empty types; otherwise keep first
            if norm not in index:
                index[norm] = (types_raw, seniorplace_url, seniorly_url)
            else:
                existing_types, existing_sp_url, existing_sr_url = index[norm]
                replace = False
                if not existing_types and types_raw:
                    replace = True
                # Prefer keeping a Senior Place URL if we don't have one yet
                if not existing_sp_url and seniorplace_url:
                    replace = True
                if replace:
                    index[norm] = (types_raw, seniorplace_url, seniorly_url)
    return index


def load_sp_url_overrides(path: str) -> Dict[str, str]:
    """Optional: load title->website_sp mapping from SENIORPLACE_VS_SENIORLY_DUPES.csv."""
    overrides: Dict[str, str] = {}
    if not os.path.exists(path):
        return overrides
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Expected columns: title, website_sp
        for row in reader:
            title = (row.get("title") or "").strip()
            sp_url = (row.get("website_sp") or "").strip()
            if not title or not sp_url:
                continue
            overrides[normalize_title(title)] = sp_url
    return overrides


def main() -> int:
    if not os.path.exists(CURRENT_CSV):
        print(f"Missing current site CSV: {CURRENT_CSV}")
        return 2
    if not os.path.exists(SP_EXPORT_CSV):
        print(f"Missing Senior Place export CSV: {SP_EXPORT_CSV}")
        return 2

    sp_index = load_seniorplace_index(SP_EXPORT_CSV)
    # Apply SP URL overrides when available
    sp_overrides = load_sp_url_overrides(SP_VS_SR_BY_TITLE)
    if sp_overrides:
        patched = 0
        for norm_title, (types_raw, sp_url, sr_url) in list(sp_index.items()):
            if not sp_url and norm_title in sp_overrides:
                sp_index[norm_title] = (types_raw, sp_overrides[norm_title], sr_url)
                patched += 1
        if patched:
            print(f"Applied {patched} Senior Place URL overrides from SENIORPLACE_VS_SENIORLY_DUPES.csv")
    print(f"Loaded Senior Place index: {len(sp_index)} titles")

    seniorly_rows: List[Dict[str, str]] = []
    with open(CURRENT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Sanitize header names
        reader.fieldnames = [fn.lstrip("\ufeff").strip() for fn in (reader.fieldnames or [])]
        for row in reader:
            row = sanitize_row_keys(row)
            website = (row.get("website") or "").strip().lower()
            if not website:
                continue
            if "seniorly.com" not in website:
                continue
            seniorly_rows.append(row)

    print(f"Found Seniorly listings in current site: {len(seniorly_rows)}")

    output_rows: List[Dict[str, str]] = []
    unmatched: int = 0
    matched: int = 0

    # Build a quick lookup from Seniorly URL -> ID using current CSV
    seniorly_url_to_id: Dict[str, str] = {}
    with open(CURRENT_CSV, "r", encoding="utf-8") as f:
        reader2 = csv.DictReader(f)
        reader2.fieldnames = [fn.lstrip("\ufeff").strip() for fn in (reader2.fieldnames or [])]
        title_to_id: Dict[str, str] = {}
        for r in reader2:
            r = sanitize_row_keys(r)
            site_id_raw = (r.get("ID") or r.get("Id") or r.get("id") or "").strip()
            url_raw = (r.get("website") or r.get("Website") or "").strip()
            if site_id_raw and url_raw and "seniorly.com" in url_raw.lower():
                seniorly_url_to_id[normalize_url_for_match(url_raw)] = site_id_raw
            # Also collect title->ID fallback (prefer titles that have seniorly website)
            title_raw = (r.get("Title") or r.get("title") or "").strip()
            if site_id_raw and title_raw:
                norm_t = normalize_title(title_raw)
                # Only set if not present or if this row has a Seniorly URL (higher confidence)
                if norm_t not in title_to_id or (url_raw and "seniorly.com" in url_raw.lower()):
                    title_to_id[norm_t] = site_id_raw

    for row in seniorly_rows:
        row = sanitize_row_keys(row)
        title = (row.get("Title") or row.get("title") or "").strip()
        seniorly_url = (row.get("website") or row.get("Website") or "").strip()
        # Derive ID by exact website match in current CSV as requested
        norm_title = normalize_title(title)
        site_id = seniorly_url_to_id.get(normalize_url_for_match(seniorly_url), (row.get("ID") or row.get("Id") or row.get("id") or "").strip())
        if not site_id:
            site_id = title_to_id.get(norm_title, "")

        sp_types_raw, sp_sp_url, sp_sr_url = ("", "", "")
        if norm_title in sp_index:
            sp_types_raw, sp_sp_url, sp_sr_url = sp_index[norm_title]
        else:
            unmatched += 1
            continue  # Only include updated Seniorly listings that matched SP

        sp_types = parse_sp_types(sp_types_raw)
        canonical_types = map_to_canonical(sp_types)
        if not canonical_types:
            # If SP had no types, skip to avoid writing empty updates
            unmatched += 1
            continue

        matched += 1
        output_rows.append({
            "ID": site_id,
            "Title": title,
            # Prefer Senior Place app URL; if absent, leave blank
            "seniorplace_url": sp_sp_url,
            "seniorly_url": seniorly_url,
            "seniorplace_types": ", ".join(sp_types),
            "normalized_types": ", ".join(canonical_types),
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(REPO_ROOT, "organized_csvs", f"CARE_TYPE_SYNC_{timestamp}.csv")

    if output_rows:
        fieldnames = [
            "ID",
            "Title",
            "seniorplace_url",
            "seniorly_url",
            "seniorplace_types",
            "normalized_types",
        ]
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)
        print(f"Wrote {len(output_rows)} updated Seniorly listings → {out_path}")
    else:
        print("No matching Seniorly listings with Senior Place types found; nothing written.")

    print(f"Matched: {matched} | Unmatched/Skipped: {unmatched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


