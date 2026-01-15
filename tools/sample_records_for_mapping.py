#!/usr/bin/env python3
"""
Create a small (10–20) representative sample of Senior Place records for mapping/testing.

This script intentionally selects EDGE CASES (missing fields, weird punctuation/casing,
non-ascii chars, likely "blocked" titles, duplicates/near-duplicates) plus a few normal
records across states.

Outputs (default under ./samples):
  - senior_place_sample_records.csv
  - senior_place_sample_records.json
  - senior_place_sample_notes.md
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


CANON_FIELDS = [
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


BUSINESS_SUFFIX_RE = re.compile(
    r"""
    (?:,?\s*(?:llc|l\.l\.c|inc|inc\.|incorporated|corp|corp\.|corporation|co|co\.|company|ltd|ltd\.|limited)\s*)$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def norm_title_key(title: str) -> str:
    t = _norm_space(title).lower()
    t = re.sub(r"\(the\)\s*$", "", t).strip()
    t = re.sub(r"\s+(d\.?b\.?a\.?|d/b/a|doing\s+business\s+as)\s+.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(BUSINESS_SUFFIX_RE, "", t).strip()
    t = re.sub(r"[^0-9a-z]+", " ", t)
    t = _norm_space(t)
    return t


def norm_addr_key(addr: str) -> str:
    a = _norm_space(addr).lower()
    a = re.sub(r"[^0-9a-z]+", " ", a)
    a = _norm_space(a)
    return a


def has_non_ascii(s: str) -> bool:
    return any(ord(ch) > 127 for ch in (s or ""))


CAPS_ONLY_RE = re.compile(r"^[A-Z0-9\s\-\.,\"'\(\)]+$")


def is_all_caps_title(title: str) -> bool:
    t = (title or "").strip()
    return bool(t) and bool(CAPS_ONLY_RE.match(t))


@dataclass(frozen=True)
class Record:
    data: Dict[str, str]
    src: str


def read_csv_records(path: Path) -> List[Record]:
    """
    Read one of the SeniorPlace CSV exports and normalize fields into CANON_FIELDS.
    Handles both 'new' schema (title,address,city,state,zip,url,featured_image,care_types,care_types_raw)
    and older schema (title,description,address,location-name,price,type,featured_image,url).
    """
    out: List[Record] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize older schema
            title = _norm_space(row.get("title", ""))
            address = _norm_space(row.get("address", ""))
            city = _norm_space(row.get("city", "") or row.get("location-name", ""))
            state = _norm_space(row.get("state", ""))
            z = _norm_space(row.get("zip", ""))
            url = _norm_space(row.get("url", "") or row.get("website", ""))
            featured_image = _norm_space(row.get("featured_image", ""))

            # Older schema uses `type` (single string) but newer schema uses care_types + care_types_raw
            care_types = _norm_space(row.get("care_types", "") or row.get("type", ""))
            care_types_raw = _norm_space(row.get("care_types_raw", "") or row.get("type", ""))

            # If address is "street, City, ST ZIP" but city/state/zip are blank, try parsing
            if address and (not city or not state or not z):
                m = re.search(r",\s*([^,]+),\s*([A-Za-z]{2})\s*(\d{5})\s*$", address)
                if m:
                    if not city:
                        city = _norm_space(m.group(1))
                    if not state:
                        state = _norm_space(m.group(2).upper())
                    if not z:
                        z = _norm_space(m.group(3))

            data = {
                "title": title,
                "address": address,
                "city": city,
                "state": state,
                "zip": z,
                "url": url,
                "featured_image": featured_image,
                "care_types": care_types,
                "care_types_raw": care_types_raw,
            }
            out.append(Record(data=data, src=str(path)))
    return out


def tag_record(r: Record) -> List[str]:
    d = r.data
    title = d.get("title", "")
    addr = d.get("address", "")
    city = d.get("city", "")
    state = d.get("state", "")
    z = d.get("zip", "")
    img = d.get("featured_image", "")
    care = d.get("care_types", "")
    care_raw = d.get("care_types_raw", "")

    tags: List[str] = []
    if not (care or care_raw):
        tags.append("missing_care_types")
    if not img:
        tags.append("missing_featured_image")
    if not (addr and city and state and z):
        tags.append("missing_location_fields")
    if is_all_caps_title(title):
        tags.append("all_caps_title")
    if has_non_ascii(title) or has_non_ascii(addr) or has_non_ascii(city):
        tags.append("non_ascii_chars")
    if any(ch in title for ch in [",", '"', "'", ";"]):
        tags.append("punctuation_in_title")
    if any(x in title.lower() for x in [" llc", " inc", " dba", "l.l.c", "corp", "corporation"]):
        tags.append("business_suffix_in_title")
    if any(x in title.lower() for x in ["do not refer", "referral", "go to", "closed"]):
        tags.append("likely_blocklisted_or_admin_note")
    return tags


def select_one(
    records: Sequence[Record],
    *,
    predicate,
    used_urls: Set[str],
    prefer_tags: Optional[Set[str]] = None,
) -> Optional[Tuple[Record, List[str]]]:
    for r in records:
        url = (r.data.get("url") or "").strip()
        if url and url in used_urls:
            continue
        tags = tag_record(r)
        if prefer_tags and not (set(tags) & prefer_tags):
            continue
        if predicate(r, tags):
            if url:
                used_urls.add(url)
            return r, tags
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Select 10–20 Senior Place sample records.")
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=[
            "AZ_seniorplace_data_20251030.csv",
            "CO_seniorplace_data_20251030.csv",
            "UT_seniorplace_data_20251030.csv",
            "ID_seniorplace_data_20251030.csv",
            "NM_seniorplace_data_20251030.csv",
            "current_scraped_data/AZ_seniorplace_data_20251027.csv",
            "current_scraped_data/CA_seniorplace_data_20251027.csv",
            "archive/old/seniorplace_data_export.csv",
        ],
        help="Input CSV paths (default: common repo exports)",
    )
    parser.add_argument("--count", type=int, default=15, help="Target number of sample records")
    parser.add_argument("--out-dir", default="samples", help="Output directory (default: samples)")
    args = parser.parse_args()

    in_paths = [Path(p) for p in args.inputs if Path(p).exists()]
    if not in_paths:
        raise SystemExit("No input files found. Provide --inputs <csv1> <csv2> ...")

    all_recs: List[Record] = []
    for p in in_paths:
        all_recs.extend(read_csv_records(p))

    # Build indexes for dupes/near-dupes
    by_title: Dict[str, List[Record]] = defaultdict(list)
    by_title_city: Dict[Tuple[str, str], List[Record]] = defaultdict(list)
    for r in all_recs:
        tk = norm_title_key(r.data.get("title", ""))
        ck = _norm_space(r.data.get("city", "")).lower()
        if tk:
            by_title[tk].append(r)
            by_title_city[(tk, ck)].append(r)

    # Identify a dupe-ish title (same normalized title appears multiple times)
    dupe_title_keys = [k for k, v in by_title.items() if len(v) >= 2]
    dupe_title_keys.sort(key=lambda k: len(by_title[k]), reverse=True)

    used_urls: Set[str] = set()
    selected: List[Dict[str, Any]] = []

    def add(rec: Record, tags: List[str], note: str) -> None:
        row = dict(rec.data)
        row["_src"] = rec.src
        row["_tags"] = tags
        row["_note"] = note
        selected.append(row)

    # 1) Targeted edge cases
    targets = [
        ("missing_care_types", {"missing_care_types"}),
        ("missing_featured_image", {"missing_featured_image"}),
        ("missing_location_fields", {"missing_location_fields"}),
        ("non_ascii_chars", {"non_ascii_chars"}),
        ("all_caps_title", {"all_caps_title"}),
        ("business_suffix_in_title", {"business_suffix_in_title"}),
        ("punctuation_in_title", {"punctuation_in_title"}),
        ("likely_blocklisted_or_admin_note", {"likely_blocklisted_or_admin_note"}),
    ]

    # We want variety across sources/states; stable ordering
    all_recs_sorted = sorted(
        all_recs,
        key=lambda r: (
            r.data.get("state", ""),
            r.data.get("city", ""),
            r.data.get("title", ""),
            r.data.get("url", ""),
        ),
    )

    for label, prefer in targets:
        pick = select_one(
            all_recs_sorted,
            predicate=lambda _r, tags: label in tags,
            used_urls=used_urls,
            prefer_tags=prefer,
        )
        if pick:
            r, tags = pick
            add(r, tags, f"Selected for edge case: {label}")

    # 2) Add a duplicate/near-duplicate pair (same title key, different addresses/urls)
    if dupe_title_keys:
        for k in dupe_title_keys:
            recs = by_title[k]
            # pick two with distinct address keys if possible
            recs2 = sorted(recs, key=lambda r: (r.data.get("state", ""), r.data.get("city", ""), r.data.get("address", "")))
            first: Optional[Record] = None
            first_addr = ""
            for r in recs2:
                u = (r.data.get("url") or "").strip()
                if u and u in used_urls:
                    continue
                first = r
                first_addr = norm_addr_key(r.data.get("address", ""))
                break
            if not first:
                continue
            second: Optional[Record] = None
            for r in recs2:
                if r is first:
                    continue
                u = (r.data.get("url") or "").strip()
                if u and u in used_urls:
                    continue
                if norm_addr_key(r.data.get("address", "")) != first_addr:
                    second = r
                    break
            if not second and len(recs2) >= 2:
                # fall back to second distinct url
                for r in recs2:
                    if r is first:
                        continue
                    u = (r.data.get("url") or "").strip()
                    if u and u in used_urls:
                        continue
                    second = r
                    break
            if second:
                for r, note in [(first, "Dupe pair A (same normalized title)"), (second, "Dupe pair B (same normalized title)")]:
                    u = (r.data.get("url") or "").strip()
                    if u:
                        used_urls.add(u)
                    add(r, tag_record(r) + ["duplicate_title_group"], note)
                break

    # 3) Fill remaining with "normal" records across states
    def is_normal(_r: Record, tags: List[str]) -> bool:
        # Minimal tags = more "normal"
        noisy = {
            "likely_blocklisted_or_admin_note",
            "missing_location_fields",
        }
        return len(set(tags) - noisy) <= 1

    # Ensure we cover each state seen in inputs (where state is present)
    desired_states = sorted({(r.data.get("state") or "").strip() for r in all_recs_sorted if (r.data.get("state") or "").strip()})
    selected_states = {(row.get("state") or "").strip() for row in selected if (row.get("state") or "").strip()}

    for st in desired_states:
        if len(selected) >= int(args.count):
            break
        if st in selected_states:
            continue
        for r in all_recs_sorted:
            u = (r.data.get("url") or "").strip()
            if u and u in used_urls:
                continue
            if (r.data.get("state") or "").strip() != st:
                continue
            tags = tag_record(r)
            if is_normal(r, tags):
                if u:
                    used_urls.add(u)
                add(r, tags, f"Baseline record to cover state: {st}")
                selected_states.add(st)
                break

    # Fill remaining with additional normal-ish records
    for r in all_recs_sorted:
        if len(selected) >= int(args.count):
            break
        u = (r.data.get("url") or "").strip()
        if u and u in used_urls:
            continue
        tags = tag_record(r)
        if is_normal(r, tags) and r.data.get("state"):
            if u:
                used_urls.add(u)
            add(r, tags, "Normal-ish record (baseline mapping)")

    # Trim hard to requested count, stable
    selected = selected[: int(args.count)]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "senior_place_sample_records.csv"
    json_path = out_dir / "senior_place_sample_records.json"
    notes_path = out_dir / "senior_place_sample_notes.md"

    # CSV: include canonical fields + url + minimal metadata
    csv_fields = CANON_FIELDS + ["_tags", "_note", "_src"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for row in selected:
            out_row = {k: row.get(k, "") for k in csv_fields}
            # stringify tags list
            if isinstance(out_row.get("_tags"), list):
                out_row["_tags"] = ",".join(out_row["_tags"])
            w.writerow(out_row)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    # Notes: quick summary of which tags we covered
    tag_counts: Dict[str, int] = defaultdict(int)
    for row in selected:
        for t in (row.get("_tags") or []):
            tag_counts[str(t)] += 1

    lines = []
    lines.append("# Senior Place sample records (mapping/test set)\n")
    lines.append(f"- Total: **{len(selected)}**\n")
    lines.append("- Inputs:\n")
    for p in in_paths:
        lines.append(f"  - `{p}`\n")
    lines.append("\n## Tag coverage\n")
    for t, c in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- **{t}**: {c}\n")
    lines.append("\n## Records\n")
    for i, row in enumerate(selected, 1):
        lines.append(f"\n### {i}. {row.get('title','').strip()}\n")
        lines.append(f"- **url**: {row.get('url','')}\n")
        lines.append(f"- **location**: {row.get('city','')}, {row.get('state','')} {row.get('zip','')}\n")
        lines.append(f"- **tags**: {', '.join(row.get('_tags') or [])}\n")
        lines.append(f"- **note**: {row.get('_note','')}\n")

    notes_path.write_text("".join(lines), encoding="utf-8")

    print(f"✅ Wrote sample set: {csv_path} ({len(selected)} rows)")
    print(f"✅ Wrote: {json_path}")
    print(f"✅ Wrote: {notes_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

