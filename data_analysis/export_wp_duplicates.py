import csv
import datetime
import os
import sys
import argparse
from typing import Any, Dict, List, Optional, Tuple

import requests


WP_BASE = "https://aplaceforseniorscms.kinsta.cloud"
WP_API_LISTING = f"{WP_BASE}/wp-json/wp/v2/listing"


def fetch_all_listings(per_page: int = 100) -> List[Dict[str, Any]]:
    """Fetch all listing posts from WordPress REST API with pagination."""
    page = 1
    results: List[Dict[str, Any]] = []
    while True:
        params = {"per_page": per_page, "page": page, "_embed": ""}
        resp = requests.get(WP_API_LISTING, params=params, timeout=30)
        if resp.status_code == 400 and "rest_post_invalid_page_number" in resp.text:
            break
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        results.extend(data)
        total_pages = int(resp.headers.get("X-WP-TotalPages", page))
        if page >= total_pages:
            break
        page += 1
    return results


def get_acf_value(post: Dict[str, Any], key: str) -> Optional[Any]:
    acf = post.get("acf") or {}
    return acf.get(key)


def normalized(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def post_summary(post: Dict[str, Any]) -> Dict[str, Any]:
    post_id = post.get("id")
    slug = post.get("slug") or ""
    title = (post.get("title", {}) or {}).get("rendered", "")
    permalink = post.get("link") or ""
    address = get_acf_value(post, "address") or get_acf_value(post, "_address") or ""
    website = get_acf_value(post, "website") or get_acf_value(post, "_website") or ""
    senior_place_url = get_acf_value(post, "senior_place_url") or ""
    seniorly_url = get_acf_value(post, "seniorly_url") or ""
    return {
        "id": post_id,
        "slug": slug,
        "title": title,
        "permalink": permalink,
        "address": address,
        "website": website,
        "senior_place_url": senior_place_url,
        "seniorly_url": seniorly_url,
    }


def detect_duplicates(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect duplicates via multiple keys and slug "-2" suffix.

    Accepts either API-shaped posts (dicts with WP fields) or pre-normalized
    summary dicts (keys: id, slug, title, permalink, address, website,
    senior_place_url, seniorly_url).
    """
    summaries: List[Dict[str, Any]]
    if not posts:
        summaries = []
    else:
        first = posts[0]
        # If title is already a string, assume posts are pre-normalized summaries
        if isinstance(first.get("title"), str):
            summaries = posts
        else:
            summaries = [post_summary(p) for p in posts]

    # Index by different keys
    index_title: Dict[str, List[Dict[str, Any]]] = {}
    index_address: Dict[str, List[Dict[str, Any]]] = {}
    index_website: Dict[str, List[Dict[str, Any]]] = {}
    index_sp: Dict[str, List[Dict[str, Any]]] = {}
    index_srly: Dict[str, List[Dict[str, Any]]] = {}

    for s in summaries:
        t = normalized(s["title"])
        a = normalized(s["address"])
        w = normalized(s["website"])
        sp = normalized(s["senior_place_url"])
        sy = normalized(s["seniorly_url"])
        if t:
            index_title.setdefault(t, []).append(s)
        if a:
            index_address.setdefault(a, []).append(s)
        if w:
            index_website.setdefault(w, []).append(s)
        if sp:
            index_sp.setdefault(sp, []).append(s)
        if sy:
            index_srly.setdefault(sy, []).append(s)

    duplicate_rows: List[Dict[str, Any]] = []

    def add_group(rows: List[Dict[str, Any]], reason: str) -> None:
        for r in rows:
            duplicate_rows.append({
                **r,
                "duplicate_reason": reason,
                "ends_with_dash_2": str(r.get("slug", "").endswith("-2")).lower(),
            })

    # 1) Slug ends with -2
    add_group([s for s in summaries if s.get("slug", "").endswith("-2")], "slug_ends_with_-2")

    # 2) Same Senior Place URL
    for k, rows in index_sp.items():
        if len(rows) > 1:
            add_group(rows, "same_senior_place_url")

    # 3) Same website
    for k, rows in index_website.items():
        if len(rows) > 1:
            add_group(rows, "same_website")

    # 4) Same title + address
    composite: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for s in summaries:
        k = (normalized(s["title"]), normalized(s["address"]))
        if any(k):
            composite.setdefault(k, []).append(s)
    for k, rows in composite.items():
        if len(rows) > 1:
            add_group(rows, "same_title_and_address")

    # 5) Same Seniorly URL
    for k, rows in index_srly.items():
        if len(rows) > 1:
            add_group(rows, "same_seniorly_url")

    # De-duplicate rows by (id, reason) to avoid duplicates in our output
    seen: set = set()
    unique_rows: List[Dict[str, Any]] = []
    for r in duplicate_rows:
        key = (r.get("id"), r.get("slug"), r.get("duplicate_reason"))
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(r)

    return unique_rows


def write_csv(rows: List[Dict[str, Any]], output_path: str) -> None:
    fieldnames = [
        "id",
        "slug",
        "title",
        "permalink",
        "address",
        "website",
        "senior_place_url",
        "seniorly_url",
        "duplicate_reason",
        "ends_with_dash_2",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def fetch_id_by_slug(slug: str, timeout: int = 20) -> Optional[int]:
    """Resolve listing ID from WP REST API by slug."""
    if not slug:
        return None
    try:
        resp = requests.get(WP_API_LISTING, params={"slug": slug}, timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json() or []
        if isinstance(data, list):
            for item in data:
                if (item or {}).get("slug") == slug:
                    try:
                        return int(item.get("id"))
                    except Exception:
                        return None
        return None
    except Exception:
        return None


def load_listings_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Load listing-like rows from a WP All Export CSV into our summary structure."""
    rows: List[Dict[str, Any]] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try to extract fields by known column names
            post_id = row.get("ID") or row.get("Id") or row.get("id") or ""
            slug = row.get("Slug") or ""
            title = row.get("Title") or ""
            permalink = row.get("Permalink") or ""
            address = row.get("address") or row.get("_address") or ""
            website = row.get("website") or row.get("_website") or ""
            senior_place_url = row.get("senior_place_url") or row.get("_senior_place_url") or ""
            seniorly_url = row.get("seniorly_url") or row.get("_seniorly_url") or ""

            # Some exports might use different casing or spacing
            if not senior_place_url:
                senior_place_url = row.get("Senior Place URL") or row.get("Senior_Place_URL") or ""
            if not seniorly_url:
                seniorly_url = row.get("Seniorly URL") or row.get("Seniorly_URL") or ""

            rows.append({
                "id": post_id,
                "slug": slug,
                "title": title,
                "permalink": permalink,
                "address": address,
                "website": website,
                "senior_place_url": senior_place_url,
                "seniorly_url": seniorly_url,
            })
    return rows


def find_latest_listing_export(directory: str) -> Optional[str]:
    """Find the newest CSV that looks like a WP listings export in a directory."""
    try:
        candidates = []
        for name in os.listdir(directory):
            if not name.lower().endswith(".csv"):
                continue
            if name.startswith("Listings-Export-") or name.startswith("Listings_Export_") or name.startswith("CURRENT Listings-Export"):
                full = os.path.join(directory, name)
                candidates.append((os.path.getmtime(full), full))
        if not candidates:
            # Fallback to any CSV
            for name in os.listdir(directory):
                if name.lower().endswith(".csv"):
                    full = os.path.join(directory, name)
                    candidates.append((os.path.getmtime(full), full))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    except Exception:
        return None


def main() -> None:
    try:
        parser = argparse.ArgumentParser(description="Export potential duplicate listings to CSV")
        parser.add_argument("--input", help="Path to WP listings export CSV. If omitted, auto-detect newest in organized_csvs.")
        parser.add_argument("--use-api", action="store_true", help="Fetch from WP REST API instead of CSV")
        parser.add_argument("--only-dash-2", action="store_true", help="Only include listings whose slug ends with -2")
        parser.add_argument("--emit-delete-csv", action="store_true", help="Also emit a deletion-ready CSV (ID + Status=trash) for WP All Import")
        args = parser.parse_args()

        listings: List[Dict[str, Any]] = []
        if args.use_api:
            print("Fetching listings from WordPress API...")
            listings = fetch_all_listings()
            print(f"Fetched {len(listings)} listings")
        else:
            csv_path = args.input
            if not csv_path:
                default_dir = os.path.join(os.path.dirname(__file__), "organized_csvs")
                csv_path = find_latest_listing_export(default_dir)
            if not csv_path or not os.path.exists(csv_path):
                raise FileNotFoundError("Could not find listings CSV. Provide --input or place it in organized_csvs.")
            print(f"Loading listings from CSV: {csv_path}")
            listings = load_listings_from_csv(csv_path)
            print(f"Loaded {len(listings)} rows from CSV")

        dupes = detect_duplicates(listings)
        if args.only_dash_2:
            dupes = [r for r in dupes if str(r.get("ends_with_dash_2", "")).lower() == "true"]
        print(f"Identified {len(dupes)} potential duplicates")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(os.path.dirname(__file__), "organized_csvs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"WP_DUPLICATES_{ts}.csv")
        write_csv(dupes, out_path)
        print(f"Wrote {len(dupes)} rows to {out_path}")

        # Optionally emit a deletion-ready CSV for WP All Import
        if args.emit_delete_csv:
            delete_rows = []
            for r in dupes:
                # Only meaningful if we filtered to -2, but we'll still guard by value
                if str(r.get("ends_with_dash_2", "")).lower() == "true":
                    delete_rows.append({
                        "ID": r.get("id", ""),
                        "Slug": r.get("slug", ""),
                        "Title": r.get("title", ""),
                        "Permalink": r.get("permalink", ""),
                        "Status": "trash",
                    })
            del_path = os.path.join(out_dir, f"DELETE_DASH2_{ts}.csv")
            with open(del_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["ID", "Slug", "Title", "Permalink", "Status"])
                writer.writeheader()
                for row in delete_rows:
                    writer.writerow(row)
            print(f"Wrote {len(delete_rows)} rows to {del_path} (deletion-ready)")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


