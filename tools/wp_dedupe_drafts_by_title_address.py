#!/usr/bin/env python3
"""tools/wp_dedupe_drafts_by_title_address.py

Deduplicate WordPress LISTING drafts against published listings by exact title + address match.

Why this exists:
- Some listings were imported from Seniorly first (rich data, already published).
- Later, importing from Senior Place can create duplicate *drafts* for the same facility
  because the published Seniorly listing often lacks `acf.senior_place_url`.

What this script does:
1) Builds a report of draft -> published matches using:
   - normalized title match AND
   - normalized `acf.address` match
2) Optional: `--apply`
   - If the published listing is missing `acf.senior_place_url` but the draft has it,
     the script backfills it into the published listing.
   - Moves the duplicate draft to Trash.

Important:
- This site’s `listing` endpoint does NOT accept setting `status=trash`.
  Use REST DELETE with `force=false` to move to trash.
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    max_attempts: int = 6,
) -> requests.Response:
    """
    Best-effort request wrapper for transient WP/Kinsta failures (e.g. 503).
    Retries with exponential backoff on common retryable status codes and network errors.
    """
    delay = 1.0
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            resp = session.request(method, url, params=params, json=json_body, timeout=timeout)
            if resp.status_code in _RETRYABLE_STATUS:
                time.sleep(delay)
                delay = min(delay * 2, 10.0)
                continue
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_exc = e
            if attempt >= max_attempts:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 10.0)

    raise last_exc or RuntimeError("Request failed unexpectedly")


def load_env_file() -> None:
    """Load `wp_config.env` from repo root into os.environ (no deps)."""
    repo_root = Path(__file__).resolve().parents[1]
    env_file = repo_root / "wp_config.env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        # Strip inline comments: KEY=VALUE  # comment
        if "#" in line:
            line = line[: line.index("#")].strip()
            if not line:
                continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


def _get_title(post: Dict[str, Any]) -> str:
    t = post.get("title")
    if isinstance(t, dict):
        return t.get("rendered", "") or ""
    return t or ""


def _get_acf(post: Dict[str, Any]) -> Dict[str, Any]:
    acf = post.get("acf")
    return acf if isinstance(acf, dict) else {}


def norm_title(s: Optional[str]) -> str:
    s = html.unescape(s or "")
    return _WS.sub(" ", s).strip().lower()


def norm_address(s: Optional[str]) -> str:
    s = html.unescape(s or "").lower()
    s = _NON_ALNUM.sub(" ", s)
    return _WS.sub(" ", s).strip()


def fetch_all(
    session: requests.Session,
    wp_url: str,
    *,
    status: str,
    per_page: int = 100,
    fields: str = "id,title,slug,acf",
) -> List[Dict[str, Any]]:
    """Fetch all listings with a given status (paginated)."""
    out: List[Dict[str, Any]] = []
    page = 1
    while True:
        r = _request_with_retry(
            session,
            "GET",
            f"{wp_url}/wp-json/wp/v2/listing",
            params={"status": status, "per_page": per_page, "page": page, "_fields": fields},
            timeout=30,
        )
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
    return out


def search_published_by_title(
    session: requests.Session,
    wp_url: str,
    *,
    title: str,
    per_page: int = 100,
    fields: str = "id,title,slug,acf",
) -> List[Dict[str, Any]]:
    r = _request_with_retry(
        session,
        "GET",
        f"{wp_url}/wp-json/wp/v2/listing",
        params={"status": "publish", "search": title, "per_page": per_page, "_fields": fields},
        timeout=30,
    )
    return r.json()


def build_duplicate_pairs(
    session: requests.Session,
    wp_url: str,
    drafts: List[Dict[str, Any]],
    *,
    limit: Optional[int] = None,
) -> Tuple[List[Dict[str, str]], int]:
    """Return (pairs, ambiguous_draft_count)."""

    # Group drafts by normalized title for a single published-search per title.
    by_title: Dict[str, List[Tuple[Dict[str, Any], str, str, str]]] = {}
    for d in drafts[:limit] if limit else drafts:
        title = _get_title(d)
        addr = _get_acf(d).get("address", "")
        nt = norm_title(title)
        na = norm_address(addr)
        if nt and na:
            by_title.setdefault(nt, []).append((d, title, addr, na))

    pairs: List[Dict[str, str]] = []
    ambiguous_drafts: set[str] = set()

    # Cache published search results per normalized title.
    pub_cache: Dict[str, List[Tuple[Dict[str, Any], str, str, str]]] = {}

    for idx, (nt, dlist) in enumerate(by_title.items(), 1):
        title_raw_for_search = dlist[0][1]

        if nt not in pub_cache:
            pubs = search_published_by_title(session, wp_url, title=title_raw_for_search)
            pubs_exact: List[Tuple[Dict[str, Any], str, str, str]] = []
            for p in pubs:
                ptitle = _get_title(p)
                if norm_title(ptitle) != nt:
                    continue
                paddr = _get_acf(p).get("address", "")
                pubs_exact.append((p, ptitle, paddr, norm_address(paddr)))
            pub_cache[nt] = pubs_exact

        pubs_exact = pub_cache[nt]
        if not pubs_exact:
            continue

        for (d, dtitle, daddr, dna) in dlist:
            matches: List[Tuple[Dict[str, Any], str, str]] = []
            for (p, ptitle, paddr, pna) in pubs_exact:
                if dna and pna == dna:
                    matches.append((p, ptitle, paddr))

            if not matches:
                continue

            if len(matches) > 1:
                ambiguous_drafts.add(str(d["id"]))

            dacf = _get_acf(d)
            for (p, ptitle, paddr) in matches:
                pacf = _get_acf(p)
                pairs.append(
                    {
                        "draft_id": str(d["id"]),
                        "draft_slug": str(d.get("slug") or ""),
                        "draft_title": dtitle,
                        "draft_address": daddr,
                        "draft_senior_place_url": str(dacf.get("senior_place_url") or ""),
                        "draft_seniorly_url": str(dacf.get("seniorly_url") or ""),
                        "published_id": str(p["id"]),
                        "published_slug": str(p.get("slug") or ""),
                        "published_title": ptitle,
                        "published_address": paddr,
                        "published_senior_place_url": str(pacf.get("senior_place_url") or ""),
                        "published_seniorly_url": str(pacf.get("seniorly_url") or ""),
                    }
                )

        # Gentle rate limit on WP search queries.
        if idx % 25 == 0:
            time.sleep(0.25)

    return pairs, len(ambiguous_drafts)


def write_csv(path: str, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def apply_cleanup(
    session: requests.Session,
    wp_url: str,
    *,
    pairs: List[Dict[str, str]],
    actions_csv_path: str,
) -> None:
    # Group by draft_id
    by_draft: Dict[str, List[Dict[str, str]]] = {}
    for row in pairs:
        by_draft.setdefault(row["draft_id"], []).append(row)

    actions: List[Dict[str, str]] = []
    updated_published = 0
    trashed_drafts = 0
    skipped_ambiguous = 0
    not_found = 0
    errors = 0

    for idx, (draft_id, matches) in enumerate(by_draft.items(), 1):
        if len(matches) != 1:
            skipped_ambiguous += 1
            actions.append(
                {
                    "draft_id": draft_id,
                    "published_id": ",".join(sorted({m["published_id"] for m in matches})),
                    "action": "SKIP_AMBIGUOUS",
                    "merged_senior_place_url": "no",
                    "error": "multiple published matches for same title+address",
                }
            )
            continue

        m = matches[0]
        pub_id = m["published_id"]
        draft_sp = (m.get("draft_senior_place_url") or "").strip()
        pub_sp = (m.get("published_senior_place_url") or "").strip()

        merged = False
        if draft_sp and not pub_sp:
            try:
                resp = session.post(
                    f"{wp_url}/wp-json/wp/v2/listing/{pub_id}",
                    json={"acf": {"senior_place_url": draft_sp}},
                    timeout=30,
                )
                resp.raise_for_status()
                merged = True
                updated_published += 1
            except Exception as e:
                errors += 1
                actions.append(
                    {
                        "draft_id": draft_id,
                        "published_id": pub_id,
                        "action": "ERROR_UPDATE_PUBLISHED",
                        "merged_senior_place_url": "no",
                        "error": str(e)[:200],
                    }
                )
                # If we couldn't preserve the Senior Place URL, do NOT delete the draft.
                continue

        # Trash the draft (DELETE force=false)
        try:
            resp = session.delete(
                f"{wp_url}/wp-json/wp/v2/listing/{draft_id}",
                params={"force": False},
                timeout=30,
            )
            if resp.status_code == 404:
                not_found += 1
                actions.append(
                    {
                        "draft_id": draft_id,
                        "published_id": pub_id,
                        "action": "DRAFT_NOT_FOUND",
                        "merged_senior_place_url": "yes" if merged else "no",
                        "error": "",
                    }
                )
            else:
                resp.raise_for_status()
                trashed_drafts += 1
                actions.append(
                    {
                        "draft_id": draft_id,
                        "published_id": pub_id,
                        "action": "TRASHED_DRAFT",
                        "merged_senior_place_url": "yes" if merged else "no",
                        "error": "",
                    }
                )
        except Exception as e:
            errors += 1
            actions.append(
                {
                    "draft_id": draft_id,
                    "published_id": pub_id,
                    "action": "ERROR_TRASH_DRAFT",
                    "merged_senior_place_url": "yes" if merged else "no",
                    "error": str(e)[:200],
                }
            )

        if idx % 25 == 0:
            time.sleep(0.25)

    write_csv(
        actions_csv_path,
        actions,
        fieldnames=["draft_id", "published_id", "action", "merged_senior_place_url", "error"],
    )

    print(f"Published updated with senior_place_url: {updated_published}")
    print(f"Drafts moved to trash: {trashed_drafts}")
    print(f"Skipped ambiguous: {skipped_ambiguous}")
    print(f"Drafts not found: {not_found}")
    print(f"Errors: {errors}")
    print(f"Actions report: {actions_csv_path}")


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(
        description="Deduplicate WordPress listing drafts against published listings by exact title+address."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes: backfill senior_place_url into published and trash duplicate drafts.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of drafts processed (for testing).",
    )
    parser.add_argument(
        "--output-dir",
        default="data_outputs",
        help="Directory for CSV reports (default: data_outputs).",
    )
    args = parser.parse_args()

    wp_url = (os.environ.get("WP_URL") or "").rstrip("/")
    wp_user = os.environ.get("WP_USER") or os.environ.get("WP_USERNAME")
    wp_pass = os.environ.get("WP_PASS") or os.environ.get("WP_PASSWORD")

    if not (wp_url and wp_user and wp_pass):
        raise SystemExit("Missing WP_URL/WP_USER/WP_PASS (or WP_USERNAME/WP_PASSWORD).")

    session = requests.Session()
    session.auth = HTTPBasicAuth(wp_user, wp_pass)

    drafts = fetch_all(session, wp_url, status="draft")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_dir)
    report_path = str(out_dir / f"draft_dupes_title_address_{ts}.csv")
    actions_path = str(out_dir / f"draft_dupe_cleanup_actions_{ts}.csv")

    pairs, ambiguous_count = build_duplicate_pairs(session, wp_url, drafts, limit=args.limit)

    fieldnames = [
        "draft_id",
        "draft_slug",
        "draft_title",
        "draft_address",
        "draft_senior_place_url",
        "draft_seniorly_url",
        "published_id",
        "published_slug",
        "published_title",
        "published_address",
        "published_senior_place_url",
        "published_seniorly_url",
    ]
    write_csv(report_path, pairs, fieldnames=fieldnames)

    unique_draft_ids = {p["draft_id"] for p in pairs}
    print(f"Drafts fetched: {len(drafts)}")
    print(f"Duplicate draft IDs (title+address match to published): {len(unique_draft_ids)}")
    print(f"Total duplicate pairs (draft->published rows): {len(pairs)}")
    print(f"Ambiguous drafts (match >1 published with same title+address): {ambiguous_count}")
    print(f"Report written: {report_path}")

    if args.apply and pairs:
        apply_cleanup(session, wp_url, pairs=pairs, actions_csv_path=actions_path)


if __name__ == "__main__":
    main()
