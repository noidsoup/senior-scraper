import csv
import os
import sys
import argparse
from typing import Dict, List, Tuple


def load_rows(full_export_path: str) -> List[Dict[str, str]]:
    with open(full_export_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_content_by_id(full_export_path: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for row in load_rows(full_export_path):
        # Handle BOM in column names
        pid = str(row.get("ID") or row.get("\ufeffID") or "").strip()
        if not pid:
            continue
        content = row.get("Content") or ""
        if content.strip():
            mapping[pid] = content
    print(f"Loaded {len(mapping)} content entries from export")
    return mapping


def normalized(s: str) -> str:
    return (s or "").strip().lower()


def build_original_id_to_dupe_content(full_export_path: str) -> Dict[str, str]:
    """Create mapping of original post ID -> content found on its -2 duplicate (if any)."""
    rows = load_rows(full_export_path)
    by_slug: Dict[str, Dict[str, str]] = {}
    by_sp: Dict[str, List[Dict[str, str]]] = {}
    by_site: Dict[str, List[Dict[str, str]]] = {}
    by_title_addr: Dict[Tuple[str, str], List[Dict[str, str]]] = {}

    for r in rows:
        slug = normalized(r.get("Slug", ""))
        by_slug[slug] = r
        sp = normalized(r.get("senior_place_url") or r.get("_senior_place_url") or r.get("Senior Place URL") or "")
        site = normalized(r.get("website") or r.get("_website") or r.get("Website") or "")
        title = normalized(r.get("Title", ""))
        addr = normalized(r.get("address") or r.get("_address") or "")
        if sp:
            by_sp.setdefault(sp, []).append(r)
        if site:
            by_site.setdefault(site, []).append(r)
        by_title_addr.setdefault((title, addr), []).append(r)

    id_to_content: Dict[str, str] = {}

    for r in rows:
        slug = normalized(r.get("Slug", ""))
        if not slug.endswith("-2"):
            continue
        dupe_content = r.get("Content") or ""
        if not dupe_content.strip():
            continue

        # Try base slug
        base_slug = slug[:-2]
        orig = by_slug.get(base_slug)
        reason = None
        if orig and not normalized(orig.get("Slug", "")).endswith("-2"):
            reason = "slug_base"
        # Senior Place URL
        if not orig:
            sp = normalized(r.get("senior_place_url") or r.get("_senior_place_url") or r.get("Senior Place URL") or "")
            if sp and by_sp.get(sp):
                for cand in by_sp[sp]:
                    if not normalized(cand.get("Slug", "")).endswith("-2"):
                        orig = cand
                        reason = "sp_url"
                        break
        # Website
        if not orig:
            site = normalized(r.get("website") or r.get("_website") or r.get("Website") or "")
            if site and by_site.get(site):
                for cand in by_site[site]:
                    if not normalized(cand.get("Slug", "")).endswith("-2"):
                        orig = cand
                        reason = "website"
                        break
        # Title + Address
        if not orig:
            title = normalized(r.get("Title", ""))
            addr = normalized(r.get("address") or r.get("_address") or "")
            for cand in by_title_addr.get((title, addr), []):
                if not normalized(cand.get("Slug", "")).endswith("-2"):
                    orig = cand
                    reason = "title_addr"
                    break

        if not orig:
            continue
        orig_id = (orig.get("ID") or "").strip()
        if not orig_id:
            continue
        # Only set if not already set; prefer first found
        if orig_id not in id_to_content:
            id_to_content[orig_id] = dupe_content

    return id_to_content


def merge_content(care_sync_path: str, content_by_id: Dict[str, str], output_path: str) -> int:
    with open(care_sync_path, newline="", encoding="utf-8") as f_in, open(output_path, "w", newline="", encoding="utf-8") as f_out:
        r = csv.DictReader(f_in)
        fieldnames = list(r.fieldnames or [])
        if "Content" not in fieldnames:
            fieldnames.append("Content")
        w = csv.DictWriter(f_out, fieldnames=fieldnames)
        w.writeheader()
        count = 0
        for row in r:
            pid = str(row.get("ID") or "").strip()
            if pid and pid in content_by_id:
                row["Content"] = content_by_id.get(pid, "")
                count += 1
                print(f"Merged content for ID {pid}: {row.get('Title', 'Unknown')[:50]}...")
            else:
                row.setdefault("Content", "")
            w.writerow(row)
        return count


def autodetect_latest_export(dir_path: str) -> str:
    candidates = []
    for name in os.listdir(dir_path):
        if name.startswith("Listings-Export-") and name.endswith(".csv"):
            full = os.path.join(dir_path, name)
            candidates.append((os.path.getmtime(full), full))
    if not candidates:
        raise FileNotFoundError("No Listings-Export-*.csv files found")
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge post Content from full export into CARE_TYPE_SYNC CSV by ID or from -2 duplicates")
    parser.add_argument("--export", help="Path to today's full Listings-Export CSV. If omitted, auto-detect latest in organized_csvs.")
    parser.add_argument("--input", required=True, help="Path to CARE_TYPE_SYNC CSV to enrich")
    parser.add_argument("--output", help="Output CSV path (default: alongside input with _WITH_CONTENT suffix)")
    parser.add_argument("--prefer-dupe-content", action="store_true", help="Fill content from matching -2 duplicates when originals are blank in export")
    args = parser.parse_args()

    base_dir = os.path.join(os.path.dirname(__file__), "organized_csvs")
    export_path = args.export or autodetect_latest_export(base_dir)

    if args.prefer_dupe_content:
        content_by_id = build_original_id_to_dupe_content(export_path)
        if not content_by_id:
            print("Warning: No -2 dupe content pairs found.")
    else:
        content_by_id = load_content_by_id(export_path)
        if not content_by_id:
            print("Warning: No content found in export or IDs missing.")

    input_path = args.input
    output_path = args.output or (os.path.splitext(input_path)[0] + "_WITH_CONTENT.csv")

    updated = merge_content(input_path, content_by_id, output_path)
    print(f"Merged Content for {updated} rows -> {output_path}")


if __name__ == "__main__":
    main()
