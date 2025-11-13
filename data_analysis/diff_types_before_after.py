#!/usr/bin/env python3
"""
Compare BEFORE vs AFTER listings and report type taxonomy changes.

Inputs (defaults):
- BEFORE: organized_csvs/04_PRE_IMPORT_BACKUP.csv (snapshot before import)
- AFTER:  organized_csvs/02_CURRENT_SITE_STATE_BACKUP.csv (current site)

Output:
- organized_csvs/TYPE_DIFF_<timestamp>.csv with columns:
  ID, Title, before_types, after_types, status (UNCHANGED/CHANGED/ADDED/REMOVED)
and prints a summary of counts.

We decode types from either:
- readable column normalized_types (if present), else
- serialized taxonomy `_type` field like a:1:{i:0;i:162;} using the approved ID->Category mapping.
"""

import csv
import os
from datetime import datetime
from typing import Dict, Tuple

REPO_ROOT = "/Users/nicholas/Repos/senior-scrapr"
DEFAULT_BEFORE = os.path.join(REPO_ROOT, "organized_csvs", "04_PRE_IMPORT_BACKUP.csv")
DEFAULT_AFTER = os.path.join(REPO_ROOT, "organized_csvs", "02_CURRENT_SITE_STATE_BACKUP.csv")

ID_TO_CATEGORY = {
    "1": "Uncategorized",
    "3": "Memory Care",
    "5": "Assisted Living Community",
    "6": "Independent Living",
    "7": "Nursing Home",
    "99": "Assisted Living Home",
    "162": "Assisted Living Home",
    "488": "Home Care",
}

def sanitize_keys(row: Dict[str, str]) -> Dict[str, str]:
    return { (k.lstrip("\ufeff").strip() if isinstance(k, str) else k): v for k, v in row.items() }

def decode_types(row: Dict[str, str]) -> str:
    # prefer normalized_types if present
    nt = (row.get("normalized_types") or row.get("Normalized Types") or "").strip()
    if nt:
        # normalize spacing and comma separation
        parts = [p.strip() for p in nt.split(",") if p.strip()]
        return ", ".join(sorted(set(parts)))

    # fallback to `_type` serialized
    php = (row.get("_type") or row.get("type") or "").strip()
    if not php:
        return ""
    try:
        import re
        ids = re.findall(r"i:\d+;i:(\d+);", php)
        cats = []
        for tid in ids:
            if tid in ID_TO_CATEGORY and ID_TO_CATEGORY[tid] not in cats:
                cats.append(ID_TO_CATEGORY[tid])
        return ", ".join(sorted(cats))
    except:
        return ""

def load_index(path: str) -> Dict[str, Tuple[str, str]]:
    # return ID -> (Title, types)
    index: Dict[str, Tuple[str, str]] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = sanitize_keys(row)
            _id = (row.get("ID") or row.get("Id") or row.get("id") or "").strip()
            title = (row.get("Title") or row.get("title") or "").strip()
            types = decode_types(row)
            if _id:
                index[_id] = (title, types)
    return index

def main(before_csv: str = DEFAULT_BEFORE, after_csv: str = DEFAULT_AFTER) -> int:
    before = load_index(before_csv)
    after = load_index(after_csv)

    added = 0
    removed = 0
    changed = 0
    unchanged = 0

    rows = []

    all_ids = set(before.keys()) | set(after.keys())
    for _id in sorted(all_ids, key=lambda x: int(x) if x.isdigit() else x):
        title_before, types_before = before.get(_id, ("", ""))
        title_after, types_after = after.get(_id, (title_before, ""))

        if _id not in before and _id in after:
            status = "ADDED"
            added += 1
        elif _id in before and _id not in after:
            status = "REMOVED"
            removed += 1
        else:
            if types_before == types_after:
                status = "UNCHANGED"
                unchanged += 1
            else:
                status = "CHANGED"
                changed += 1

        rows.append({
            "ID": _id,
            "Title": title_after or title_before,
            "before_types": types_before,
            "after_types": types_after,
            "status": status,
        })

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(REPO_ROOT, "organized_csvs", f"TYPE_DIFF_{ts}.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "Title", "before_types", "after_types", "status"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"ADDED: {added}")
    print(f"REMOVED: {removed}")
    print(f"CHANGED: {changed}")
    print(f"UNCHANGED: {unchanged}")
    print(f"Wrote: {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


