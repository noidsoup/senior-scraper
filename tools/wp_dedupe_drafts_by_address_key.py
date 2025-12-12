#!/usr/bin/env python3
"""
Deduplicate WordPress listing *drafts* against *published* listings using a fuzzy address key.

Why:
- The site often has older published Seniorly listings (rich ACF data) with no `acf.senior_place_url`.
- Importing from Senior Place can create duplicate drafts for the same facility/address.
- Exact title/address matching can miss cases like:
  - "E Latham St" vs "East Latham Street"
  - HTML entities in titles (& vs &#038;)

How it matches:
- Restricts comparisons to the same `state` taxonomy term AND same `location` taxonomy term (city).
- Builds an address key from the STREET line:
  - street number + core street name (drops directions + suffix, expands common abbreviations)
- Scores candidates by title similarity and outputs top candidates per draft.

Apply behavior (`--apply`):
- If the best matching published listing has NO `acf.senior_place_url` and the draft DOES:
  - backfill the draft's `acf.senior_place_url` into the published listing
  - move the draft to Trash (REST DELETE force=false)
- Drafts whose best published match already has a `senior_place_url` are SKIPPED by default.
  Use `--trash-when-published-has-sp-url` to trash those drafts too.

Reads credentials from:
- Environment variables: WP_URL, WP_USER (or WP_USERNAME), WP_PASS (or WP_PASSWORD)
- Or `wp_config.env` in repo root (gitignored)
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
WS = re.compile(r"\s+")

DIR_MAP = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
}

SUFFIX_MAP = {
    "st": "street",
    "street": "street",
    "rd": "road",
    "road": "road",
    "ave": "avenue",
    "av": "avenue",
    "avenue": "avenue",
    "blvd": "boulevard",
    "boulevard": "boulevard",
    "dr": "drive",
    "drive": "drive",
    "ln": "lane",
    "lane": "lane",
    "ct": "court",
    "court": "court",
    "pl": "place",
    "place": "place",
    "cir": "circle",
    "circle": "circle",
    "way": "way",
    "trl": "trail",
    "trail": "trail",
    "pkwy": "parkway",
    "parkway": "parkway",
    "hwy": "highway",
    "highway": "highway",
}

UNIT_WORDS = {"apt", "apartment", "unit", "ste", "suite", "#"}


def load_env_file() -> None:
    env_file = Path(__file__).resolve().parents[1] / "wp_config.env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if "#" in line:
            line = line[: line.index("#")].strip()
            if not line:
                continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


def request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    max_attempts: int = 6,
) -> requests.Response:
    delay = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            r = session.request(method, url, params=params, json=json_body, timeout=timeout)
            if r.status_code in RETRYABLE_STATUS:
                time.sleep(delay)
                delay = min(delay * 2, 10.0)
                continue
            r.raise_for_status()
            return r
        except Exception:
            if attempt >= max_attempts:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 10.0)
    raise RuntimeError("unreachable")


def get_title(post: Dict[str, Any]) -> str:
    t = post.get("title")
    if isinstance(t, dict):
        return html.unescape(t.get("rendered", "") or "")
    return html.unescape(t or "")


def get_acf(post: Dict[str, Any]) -> Dict[str, Any]:
    acf = post.get("acf")
    return acf if isinstance(acf, dict) else {}


def norm_title_for_similarity(s: str) -> str:
    s = html.unescape(s or "")
    s = s.strip().lower()
    s = WS.sub(" ", s)
    s = re.sub(r"[^0-9a-z\s]", "", s)
    return WS.sub(" ", s).strip()


def title_similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    a2 = norm_title_for_similarity(a)
    b2 = norm_title_for_similarity(b)
    if not a2 or not b2:
        return 0.0
    return SequenceMatcher(None, a2, b2).ratio()


def parse_street_line(full_address: str) -> str:
    if not full_address:
        return ""
    # ACF address format is usually "street, city, ST ZIP"
    return full_address.split(",")[0].strip()


@dataclass(frozen=True)
class AddressKey:
    number: str
    core: str


def build_address_key(street_line: str) -> Optional[AddressKey]:
    street = (street_line or "").lower()
    street = re.sub(r"[^0-9a-z\s]", " ", street)
    tokens = [t for t in WS.split(street.strip()) if t]
    if not tokens:
        return None

    number = tokens[0] if tokens[0].isdigit() else ""
    rest = tokens[1:] if number else tokens

    # normalize directions + suffixes
    normed = [DIR_MAP.get(t, t) for t in rest]

    # strip unit markers and the following token (often number/letter)
    cleaned: List[str] = []
    skip_next = False
    for t in normed:
        if skip_next:
            skip_next = False
            continue
        if t in UNIT_WORDS:
            skip_next = True
            continue
        cleaned.append(t)

    if not cleaned and not number:
        return None

    # normalize suffix at end if present
    if cleaned and cleaned[-1] in SUFFIX_MAP:
        cleaned[-1] = SUFFIX_MAP[cleaned[-1]]

    # core = remove suffix + remove directions
    core = cleaned[:]
    if core and core[-1] in set(SUFFIX_MAP.values()):
        core = core[:-1]
    core = [t for t in core if t not in set(DIR_MAP.values())]
    core_str = " ".join(core).strip()

    if not number or not core_str:
        return None
    return AddressKey(number=number, core=core_str)


def fetch_all_pages(
    session: requests.Session,
    wp_url: str,
    params: Dict[str, Any],
    *,
    sleep_s: float = 0.05,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    page = 1
    while True:
        p = dict(params)
        p["per_page"] = 100
        p["page"] = page
        r = request_with_retry(session, "GET", f"{wp_url}/wp-json/wp/v2/listing", params=p)
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
        if sleep_s:
            time.sleep(sleep_s)
    return out


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Backfill URL + trash drafts where safe.")
    parser.add_argument(
        "--trash-when-published-has-sp-url",
        action="store_true",
        help="Also trash drafts when the best published match already has a senior_place_url.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of drafts processed.")
    parser.add_argument("--output-dir", default="data_outputs", help="Where to write CSV reports.")
    args = parser.parse_args()

    wp_url = (os.environ.get("WP_URL") or "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
    wp_user = os.environ.get("WP_USER") or os.environ.get("WP_USERNAME")
    wp_pass = os.environ.get("WP_PASS") or os.environ.get("WP_PASSWORD")
    if not (wp_url and wp_user and wp_pass):
        raise SystemExit("Missing WP_URL/WP_USER/WP_PASS (or WP_USERNAME/WP_PASSWORD).")

    session = requests.Session()
    session.auth = HTTPBasicAuth(wp_user, wp_pass)

    drafts = fetch_all_pages(
        session,
        wp_url,
        params={"status": "draft", "_fields": "id,title,slug,acf,state,location"},
    )
    if args.limit is not None:
        drafts = drafts[: int(args.limit)]

    # Group by (state_id, location_id) for efficient published lookups
    groups: Dict[Tuple[Optional[int], Optional[int]], List[Dict[str, Any]]] = {}
    for d in drafts:
        state_ids = d.get("state") if isinstance(d.get("state"), list) else []
        loc_ids = d.get("location") if isinstance(d.get("location"), list) else []
        state_id = state_ids[0] if state_ids else None
        loc_id = loc_ids[0] if loc_ids else None
        groups.setdefault((state_id, loc_id), []).append(d)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = str(out_dir / f"draft_possible_dupes_fuzzy_{ts}.csv")
    actions_path = str(out_dir / f"draft_possible_dupes_fuzzy_actions_{ts}.csv")

    report_rows: List[Dict[str, str]] = []
    action_rows: List[Dict[str, str]] = []

    updated_pub = 0
    trashed = 0
    skipped_no_candidates = 0
    skipped_published_has_sp_url = 0
    errors = 0

    for (state_id, loc_id), dlist in groups.items():
        if not state_id or not loc_id:
            # Missing taxonomy; skip silently
            continue

        pubs = fetch_all_pages(
            session,
            wp_url,
            params={
                "status": "publish",
                "state": state_id,
                "location": loc_id,
                "_fields": "id,title,slug,acf",
            },
        )

        # Published address index (within city/state)
        addr_index: Dict[AddressKey, List[Dict[str, Any]]] = {}
        for p in pubs:
            acf = get_acf(p)
            addr = (acf.get("address") or "").strip()
            key = build_address_key(parse_street_line(addr))
            if not key:
                continue
            addr_index.setdefault(key, []).append(p)

        for d in dlist:
            dacf = get_acf(d)
            daddr = (dacf.get("address") or "").strip()
            dkey = build_address_key(parse_street_line(daddr))
            if not dkey:
                continue

            candidates = addr_index.get(dkey, [])
            if not candidates:
                skipped_no_candidates += 1
                continue

            dtitle = get_title(d)
            d_sp = (dacf.get("senior_place_url") or "").strip()

            scored: List[Tuple[float, Dict[str, Any]]] = []
            for p in candidates:
                scored.append((title_similarity(dtitle, get_title(p)), p))
            scored.sort(key=lambda x: x[0], reverse=True)

            top = scored[:3]
            for sim, p in top:
                pacf = get_acf(p)
                report_rows.append(
                    {
                        "draft_id": str(d.get("id")),
                        "draft_title": dtitle,
                        "draft_address": daddr,
                        "draft_senior_place_url": d_sp,
                        "draft_state_term_id": str(state_id),
                        "draft_location_term_id": str(loc_id),
                        "published_id": str(p.get("id")),
                        "published_slug": str(p.get("slug") or ""),
                        "published_title": get_title(p),
                        "published_address": str((pacf.get("address") or "")).strip(),
                        "published_senior_place_url": str((pacf.get("senior_place_url") or "")).strip(),
                        "published_seniorly_url": str((pacf.get("seniorly_url") or "")).strip(),
                        "title_similarity": f"{sim:.3f}",
                        "match_reason": "street_number+street_name_core (same location+state)",
                    }
                )

            # Apply action only against the best match
            best_sim, best_pub = scored[0]
            best_pub_id = best_pub["id"]
            best_pub_sp = (get_acf(best_pub).get("senior_place_url") or "").strip()

            if not args.apply:
                continue

            # If published already has senior_place_url, either skip or trash (optional flag)
            if best_pub_sp:
                if args.trash_when_published_has_sp_url:
                    # Trash draft only
                    try:
                        r = request_with_retry(
                            session,
                            "DELETE",
                            f"{wp_url}/wp-json/wp/v2/listing/{d['id']}",
                            params={"force": False},
                        )
                        trashed += 1
                        action_rows.append(
                            {
                                "draft_id": str(d["id"]),
                                "published_id": str(best_pub_id),
                                "title_similarity": f"{best_sim:.3f}",
                                "action": "TRASHED_DRAFT_PUBLISHED_ALREADY_HAS_SP_URL",
                                "error": "",
                            }
                        )
                    except Exception as e:
                        errors += 1
                        action_rows.append(
                            {
                                "draft_id": str(d["id"]),
                                "published_id": str(best_pub_id),
                                "title_similarity": f"{best_sim:.3f}",
                                "action": "ERROR_TRASH_DRAFT",
                                "error": str(e)[:200],
                            }
                        )
                else:
                    skipped_published_has_sp_url += 1
                continue

            # Otherwise, backfill SP URL and trash draft
            if not d_sp:
                skipped_published_has_sp_url += 1
                continue

            try:
                u = request_with_retry(
                    session,
                    "POST",
                    f"{wp_url}/wp-json/wp/v2/listing/{best_pub_id}",
                    json_body={"acf": {"senior_place_url": d_sp}},
                )
                updated_pub += 1
            except Exception as e:
                errors += 1
                action_rows.append(
                    {
                        "draft_id": str(d["id"]),
                        "published_id": str(best_pub_id),
                        "title_similarity": f"{best_sim:.3f}",
                        "action": "ERROR_UPDATE_PUBLISHED",
                        "error": str(e)[:200],
                    }
                )
                continue

            try:
                request_with_retry(
                    session,
                    "DELETE",
                    f"{wp_url}/wp-json/wp/v2/listing/{d['id']}",
                    params={"force": False},
                )
                trashed += 1
                action_rows.append(
                    {
                        "draft_id": str(d["id"]),
                        "published_id": str(best_pub_id),
                        "title_similarity": f"{best_sim:.3f}",
                        "action": "BACKFILLED_SP_URL_AND_TRASHED_DRAFT",
                        "error": "",
                    }
                )
            except Exception as e:
                errors += 1
                action_rows.append(
                    {
                        "draft_id": str(d["id"]),
                        "published_id": str(best_pub_id),
                        "title_similarity": f"{best_sim:.3f}",
                        "action": "ERROR_TRASH_DRAFT",
                        "error": str(e)[:200],
                    }
                )

        time.sleep(0.1)

    # Write reports
    report_fieldnames = [
        "draft_id",
        "draft_title",
        "draft_address",
        "draft_senior_place_url",
        "draft_state_term_id",
        "draft_location_term_id",
        "published_id",
        "published_slug",
        "published_title",
        "published_address",
        "published_senior_place_url",
        "published_seniorly_url",
        "title_similarity",
        "match_reason",
    ]
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=report_fieldnames)
        w.writeheader()
        w.writerows(report_rows)

    action_fieldnames = ["draft_id", "published_id", "title_similarity", "action", "error"]
    with open(actions_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=action_fieldnames)
        w.writeheader()
        w.writerows(action_rows)

    print(f"Drafts checked: {len(drafts)}")
    print(f"Drafts with candidates: {len({r['draft_id'] for r in report_rows})}")
    print(f"Report written: {report_path}")
    if args.apply:
        print(f"Published updated (SP URL backfilled): {updated_pub}")
        print(f"Drafts trashed: {trashed}")
        print(f"Skipped (published already had SP URL): {skipped_published_has_sp_url}")
        print(f"Errors: {errors}")
        print(f"Actions report: {actions_path}")


if __name__ == "__main__":
    main()

