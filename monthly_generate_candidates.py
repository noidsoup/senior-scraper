#!/usr/bin/env python3
"""
Monthly candidate generator

Purpose:
- Compare the latest scraped Senior Place CSVs against WordPress to determine NEW listings to add.
- Output a single consolidated candidates CSV in data/processed/ suitable for review and import.

Usage examples:
    # Auto-discover newest CSV per state (AZ, CA, CO, ID, NM, UT) and generate candidates
    python3 monthly_generate_candidates.py

    # Specify output explicitly
    python3 monthly_generate_candidates.py --output data/processed/monthly_candidates_manual.csv

    # Limit which states to include
    python3 monthly_generate_candidates.py --states AZ NM UT

Notes:
- Dedupe is performed primarily by the Senior Place URL (authoritative).
- Titles are normalized to WordPress format to improve readability.
"""

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# Reuse existing utilities from the safe importer
from import_to_wordpress_api_safe import get_existing_urls, normalize_title


ALLOWED_STATES: Tuple[str, ...] = ("AZ", "CA", "CO", "ID", "NM", "UT")

# Same blocklist used by importer (defensive filtering at source)
TITLE_BLOCKLIST_PATTERNS: Tuple[str, ...] = (
    r"\bdo\s+not\s+refer\b",
    r"\bdo\s+not\s+use\b",
    r"\bnot\s+signing\b",
    r"\bsurgery\b",
    r"\bsurgical\b",
    r"\beye\s+surgery\b",
)


def is_blocklisted(title: str) -> bool:
    if not title:
        return False
    for pat in TITLE_BLOCKLIST_PATTERNS:
        if re.search(pat, title, flags=re.IGNORECASE):
            return True
    return False


def find_latest_state_files(
    search_dir: Path,
    states: Iterable[str]
) -> Dict[str, Path]:
    """Find the newest *_seniorplace_data_YYYYMMDD.csv for each requested state."""
    newest: Dict[str, Tuple[str, Path]] = {}
    pattern = re.compile(r"^([A-Z]{2})_seniorplace_data_(\d{8})\.csv$")

    for entry in search_dir.iterdir():
        if not entry.is_file():
            continue
        m = pattern.match(entry.name)
        if not m:
            continue
        state, datestr = m.group(1), m.group(2)
        if state not in states:
            continue
        # Track by most recent date string lexicographically (YYYYMMDD)
        current = newest.get(state)
        if current is None or datestr > current[0]:
            newest[state] = (datestr, entry)

    # Convert to state -> Path dict
    return {s: p for s, (_, p) in newest.items()}


def is_valid_row(row: Dict[str, str]) -> bool:
    """Basic filtering for a usable listing row."""
    if not row.get("url"):
        return False
    if not row.get("title"):
        return False
    if is_blocklisted(row.get("title", "")):
        return False
    # care_types must exist and not be empty or "[]"
    care_types = (row.get("care_types") or "").strip()
    if not care_types or care_types == "[]":
        return False
    # Require address (WordPress shows it on frontend)
    if not (row.get("address") or "").strip():
        return False
    return True


def normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    """Return a shallow copy with normalized title and cleaned whitespace."""
    cleaned: Dict[str, str] = dict(row)
    cleaned["title"] = normalize_title(row.get("title", "")) or row.get("title", "")
    for key, value in list(cleaned.items()):
        if isinstance(value, str):
            cleaned[key] = value.strip()
    # Uppercase state abbreviation if present
    if cleaned.get("state"):
        cleaned["state"] = cleaned["state"].upper()
    return cleaned


def write_candidates_csv(output_path: Path, rows: List[Dict[str, str]]) -> None:
    """Write candidates with a stable column order used by the importer."""
    field_order = [
        "title",
        "address",
        "city",
        "state",
        "zip",
        "url",
        "featured_image",
        "care_types",
        "care_types_raw",
    ]

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=field_order)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in field_order})


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate monthly candidates CSV for WordPress import")
    parser.add_argument(
        "--states",
        nargs="+",
        default=list(ALLOWED_STATES),
        help="States to include (default: AZ CA CO ID NM UT)",
    )
    parser.add_argument(
        "--search-dir",
        default=str(Path.cwd()),
        help="Directory containing *_seniorplace_data_YYYYMMDD.csv files (default: current dir)",
    )
    parser.add_argument(
        "--output",
        default=str(Path("data/processed") / f"monthly_candidates_{datetime.now().strftime('%Y%m%d')}.csv"),
        help="Output CSV path (default: data/processed/monthly_candidates_YYYYMMDD.csv)",
    )
    parser.add_argument(
        "--wp-pages",
        type=int,
        default=None,
        help="Limit pages to fetch from WP for existing URLs (default: all)",
    )
    args = parser.parse_args()

    states = [s.upper() for s in args.states]
    for s in states:
        if s not in ALLOWED_STATES:
            print(f"Warning: state {s} is not in allowed set {ALLOWED_STATES}")

    search_dir = Path(args.search_dir)
    if not search_dir.exists():
        print(f"Error: search dir not found: {search_dir}")
        return 2

    # Build WordPress existing URL cache (authoritative dedupe)
    print("Building WordPress duplicate cache (this may take a moment)...", flush=True)
    wp_urls: Set[str] = get_existing_urls(limit_pages=args.wp_pages)
    print(f"Have {len(wp_urls)} existing URLs in WordPress", flush=True)

    # Select newest CSV per state
    latest_files = find_latest_state_files(search_dir, states)
    if not latest_files:
        print("No matching CSVs found.")
        return 3

    print("Using input files:", flush=True)
    for st, path in sorted(latest_files.items()):
        print(f"  {st}: {path.name}")

    candidates: List[Dict[str, str]] = []
    seen_urls: Set[str] = set()

    total_rows = 0
    skipped_invalid = 0
    skipped_existing = 0

    for st, csv_path in latest_files.items():
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                if not is_valid_row(row):
                    skipped_invalid += 1
                    continue

                normalized = normalize_row(row)

                # Only allowed states
                row_state = (normalized.get("state") or "").upper()
                if row_state and row_state not in states:
                    skipped_invalid += 1
                    continue

                sp_url = normalized["url"].strip()
                if sp_url in wp_urls:
                    skipped_existing += 1
                    continue
                if sp_url in seen_urls:
                    # Duplicate within this run (across files) – keep first occurrence
                    skipped_existing += 1
                    continue

                seen_urls.add(sp_url)
                candidates.append(normalized)

    output_path = Path(args.output)
    write_candidates_csv(output_path, candidates)

    print("\nCandidate generation complete:", flush=True)
    print(f"  Total rows scanned:   {total_rows}")
    print(f"  Skipped invalid:      {skipped_invalid}")
    print(f"  Skipped existing:     {skipped_existing}")
    print(f"  New candidates:       {len(candidates)}")
    print(f"  Output CSV:           {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())


