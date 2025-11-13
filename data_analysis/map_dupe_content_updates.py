import csv
import os
import sys
import argparse
import datetime
from typing import Dict, List, Optional, Tuple
import requests


def normalized(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def load_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get(row: Dict[str, str], key: str) -> str:
    return row.get(key) or ""


def find_pairs(rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Find pairs of (-2 slug) duplicates and their likely originals.
    Returns (groups, updates_fill_blank, overwrites_if_allowed)
    - groups: review file with details and match reason
    - updates_fill_blank: ID (original), Content (from -2) when original Content is blank
    - overwrites_if_allowed: same as updates but where original Content is non-blank (for user decision)
    """
    # Index originals by multiple keys
    by_slug: Dict[str, Dict[str, str]] = {}
    by_sp: Dict[str, Dict[str, str]] = {}
    by_site: Dict[str, Dict[str, str]] = {}
    by_title_address: Dict[Tuple[str, str], Dict[str, str]] = {}

    for r in rows:
        slug = normalized(get(r, "Slug"))
        content = get(r, "Content")
        title = normalized(get(r, "Title"))
        address = normalized(get(r, "address") or get(r, "_address"))
        website = normalized(get(r, "website") or get(r, "_website"))
        senior_place_url = normalized(
            get(r, "senior_place_url") or get(r, "_senior_place_url") or get(r, "Senior Place URL")
        )

        # Consider all rows as potential originals; we'll exclude -2 when matching by slug_no2
        if slug:
            by_slug[slug] = r
        if senior_place_url:
            by_sp[senior_place_url] = r
        if website:
            by_site[website] = r
        if title or address:
            by_title_address[(title, address)] = r

    groups: List[Dict[str, str]] = []
    updates_fill_blank: List[Dict[str, str]] = []
    overwrites_if_allowed: List[Dict[str, str]] = []

    for dupe in rows:
        d_slug = normalized(get(dupe, "Slug"))
        if not d_slug.endswith("-2"):
            continue

        d_content = get(dupe, "Content")
        if not d_content.strip():
            # No content to transfer
            continue

        d_title = normalized(get(dupe, "Title"))
        d_address = normalized(get(dupe, "address") or get(dupe, "_address"))
        d_site = normalized(get(dupe, "website") or get(dupe, "_website"))
        d_sp = normalized(get(dupe, "senior_place_url") or get(dupe, "_senior_place_url") or get(dupe, "Senior Place URL"))

        original: Optional[Dict[str, str]] = None
        reason = ""

        # 1) slug without -2
        if d_slug.endswith("-2"):
            base_slug = d_slug[:-2]
            candidate = by_slug.get(base_slug)
            if candidate and normalized(get(candidate, "Slug")) == base_slug:
                # Ensure candidate is not itself a -2
                if not normalized(get(candidate, "Slug")).endswith("-2"):
                    original = candidate
                    reason = "slug_base_match"

        # 2) Senior Place URL
        if original is None and d_sp:
            candidate = by_sp.get(d_sp)
            if candidate and normalized(get(candidate, "Slug")) != d_slug:
                original = candidate
                reason = "same_senior_place_url"

        # 3) Website
        if original is None and d_site:
            candidate = by_site.get(d_site)
            if candidate and normalized(get(candidate, "Slug")) != d_slug:
                original = candidate
                reason = "same_website"

        # 4) Title + Address
        if original is None and (d_title or d_address):
            candidate = by_title_address.get((d_title, d_address))
            if candidate and normalized(get(candidate, "Slug")) != d_slug:
                original = candidate
                reason = "same_title_and_address"

        if original is None:
            continue

        o_content = get(original, "Content")
        o_id = get(original, "ID")
        o_slug = get(original, "Slug")
        d_id = get(dupe, "ID")

        groups.append({
            "original_id": o_id,
            "original_slug": o_slug,
            "original_title": get(original, "Title"),
            "dupe_id": d_id,
            "dupe_slug": get(dupe, "Slug"),
            "dupe_title": get(dupe, "Title"),
            "match_reason": reason,
            "original_content_length": str(len(o_content or "")),
            "dupe_content_length": str(len(d_content or "")),
        })

        if not (o_content or "").strip():
            updates_fill_blank.append({
                "ID": o_id,
                "Slug": o_slug,
                "Title": get(original, "Title"),
                "Content": d_content,
            })
        else:
            overwrites_if_allowed.append({
                "ID": o_id,
                "Slug": o_slug,
                "Title": get(original, "Title"),
                "Content": d_content,
            })

    return groups, updates_fill_blank, overwrites_if_allowed


def write_csv(path: str, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(description="Map -2 duplicates to originals and prepare content updates")
    parser.add_argument("--input", required=False, help="Path to WP listings export CSV. If omitted, auto-pick newest Listings-Export in organized_csvs")
    args = parser.parse_args()

    csv_path = args.input
    if not csv_path:
        root = os.path.dirname(__file__)
        oc = os.path.join(root, "organized_csvs")
        candidates = []
        if os.path.isdir(oc):
            for name in os.listdir(oc):
                if name.endswith(".csv") and name.startswith("Listings-Export-"):
                    full = os.path.join(oc, name)
                    candidates.append((os.path.getmtime(full), full))
        if not candidates:
            print("Error: No Listings-Export CSV found in organized_csvs. Provide --input.")
            sys.exit(1)
        candidates.sort(key=lambda x: x[0], reverse=True)
        csv_path = candidates[0][1]

    rows = load_csv(csv_path)
    print(f"Loaded {len(rows)} rows from {csv_path}")
    groups, updates_fill_blank, overwrites_if_allowed = find_pairs(rows)

    # Try to resolve missing IDs via WP REST API (by slug) for originals
    def resolve_id(slug: str) -> Optional[str]:
        if not slug:
            return None
        try:
            resp = requests.get('https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2/listing', params={'slug': slug}, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json() or []
            if isinstance(data, list):
                for item in data:
                    if (item or {}).get('slug') == slug:
                        return str(item.get('id') or '')
            return None
        except Exception:
            return None

    # Patch IDs for groups and updates
    # Build a quick slug->ID cache to minimize API calls
    slug_to_id: Dict[str, str] = {}
    for g in groups:
        oslug = g.get('original_slug', '')
        if oslug and not slug_to_id.get(oslug):
            rid = resolve_id(oslug)
            if rid:
                slug_to_id[oslug] = rid
        dslug = g.get('dupe_slug', '')
        if dslug and not slug_to_id.get(dslug):
            rid = resolve_id(dslug)
            if rid:
                slug_to_id[dslug] = rid

    for g in groups:
        if not (g.get('original_id') or '').strip():
            rid = slug_to_id.get(g.get('original_slug', ''), '')
            if rid:
                g['original_id'] = rid
        if not (g.get('dupe_id') or '').strip():
            rid = slug_to_id.get(g.get('dupe_slug', ''), '')
            if rid:
                g['dupe_id'] = rid

    for u in updates_fill_blank:
        if not (u.get('ID') or '').strip():
            # Find matching group by original slug then backfill
            # We can only map if we also output a slug, so add slug to updates for traceability
            pass
    print(f"Paired {len(groups)} -2 listings with originals")
    print(f"Prepared {len(updates_fill_blank)} content updates (fill blanks)")
    print(f"Found {len(overwrites_if_allowed)} potential overwrites (original has content)")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(os.path.dirname(__file__), "organized_csvs")
    os.makedirs(out_dir, exist_ok=True)

    groups_path = os.path.join(out_dir, f"DUPLICATE_GROUPS_{ts}.csv")
    updates_path = os.path.join(out_dir, f"CONTENT_UPDATES_FILL_BLANKS_{ts}.csv")
    overwrites_path = os.path.join(out_dir, f"CONTENT_UPDATES_OVERWRITES_{ts}.csv")

    write_csv(
        groups_path,
        groups,
        [
            "original_id",
            "original_slug",
            "original_title",
            "dupe_id",
            "dupe_slug",
            "dupe_title",
            "match_reason",
            "original_content_length",
            "dupe_content_length",
        ],
    )
    write_csv(updates_path, updates_fill_blank, ["ID", "Slug", "Title", "Content"])
    write_csv(overwrites_path, overwrites_if_allowed, ["ID", "Slug", "Title", "Content"])

    print("Written:")
    print(f"  Review groups: {groups_path}")
    print(f"  Updates (fill blanks): {updates_path}")
    print(f"  Potential overwrites: {overwrites_path}")


if __name__ == "__main__":
    main()


