#!/usr/bin/env python3
"""
Compatibility module kept for older scripts/tests.

Upstream work introduced `import_to_wordpress_api.py` as the primary importer, but a number
of scripts/tests still import helpers from `import_to_wordpress_api_safe.py`.

This file intentionally contains ONLY shared helpers (normalization, blocklist checks,
care type term mapping, and a small image downloader) and does NOT embed credentials.

Credentials are read from environment variables and/or `wp_config.env` (gitignored).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth

try:
    # Prefer the canonical patterns from the core module.
    from core.constants import TITLE_BLOCKLIST_PATTERNS
except Exception:  # pragma: no cover
    TITLE_BLOCKLIST_PATTERNS = [
        r"\bdo\s+not\s+refer\b",
        r"\bdo\s+not\s+use\b",
        r"\bnot\s+signing\b",
        r"\bsurgery\b",
        r"\bsurgical\b",
    ]


def load_env_file() -> None:
    """Load wp_config.env from repo root into os.environ (no external deps)."""
    env_file = Path(__file__).resolve().parent / "wp_config.env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        # Strip inline comments
        if "#" in line:
            line = line[: line.index("#")].strip()
            if not line:
                continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


load_env_file()

WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
WP_USER = os.getenv("WP_USER") or os.getenv("WP_USERNAME")
WP_PASS = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")


# Care type mapping to taxonomy term IDs (WordPress)
CARE_TYPE_MAPPING = {
    "Assisted Living Community": 5,
    "Assisted Living Home": 162,
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    "Home Care": 488,
}


def get_existing_urls(limit_pages: Optional[int] = None) -> set[str]:
    """
    Fetch all existing Senior Place URLs already stored in WordPress.

    Used to prevent duplicate imports when the Senior Place URL is already present.
    """
    if not WP_USER or not WP_PASS:
        raise RuntimeError("Missing WP_USER/WP_PASS (or WP_USERNAME/WP_PASSWORD).")

    urls: set[str] = set()
    page = 1
    while True:
        if limit_pages is not None and page > int(limit_pages):
            break
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/listing",
            params={"per_page": 100, "page": page, "_fields": "acf"},
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            timeout=30,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for post in batch:
            sp_url = ((post.get("acf") or {}).get("senior_place_url") or "").strip()
            if sp_url:
                urls.add(sp_url)
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
    return urls


def normalize_title(title: Optional[str]) -> Optional[str]:
    """
    Normalize title for WordPress:
    - Strip common business suffixes (LLC/INC/etc)
    - Strip DBA and everything after it
    - Handle "(The)" suffix by moving "The" to the front
    - Title Case with minor-words lowercased
    """
    if title is None:
        return None
    t = title.strip()
    if not t:
        return ""

    # Move "(The)" suffix to front: "Foo (The)" -> "The Foo"
    m = re.search(r"\s*\((the)\)\s*$", t, flags=re.IGNORECASE)
    if m:
        t = re.sub(r"\s*\(the\)\s*$", "", t, flags=re.IGNORECASE).strip()
        t = f"The {t}".strip()

    # Strip DBA patterns (remove everything after DBA)
    t = re.sub(r"\s+(d\.?b\.?a\.?|d/b/a|doing\s+business\s+as)\s+.*$", "", t, flags=re.IGNORECASE)

    # Strip common business suffixes
    suffixes = [
        r"\s+llc\.?$",
        r"\s+l\.l\.c\.?$",
        r"\s+inc\.?$",
        r"\s+incorporated\.?$",
        r"\s+corp\.?$",
        r"\s+corporation\.?$",
        r"\s+co\.?$",
        r"\s+company\.?$",
        r"\s+ltd\.?$",
        r"\s+limited\.?$",
        r"\s+lp\.?$",
        r"\s+llp\.?$",
        r"\s+pllc\.?$",
        r"\s+p\.l\.l\.c\.?$",
    ]
    for suf in suffixes:
        t = re.sub(suf, "", t, flags=re.IGNORECASE).strip()

    # Cleanup punctuation/whitespace
    t = re.sub(r",?\s*$", "", t).strip()
    t = re.sub(r"\s+", " ", t).strip()

    # Title case
    t = t.title()
    words = t.split()
    minor = {"of", "the", "at", "by", "in", "on", "for", "and", "or"}
    for i in range(1, len(words)):
        if words[i].lower() in minor:
            words[i] = words[i].lower()
    return " ".join(words)


def normalize_address(address: Optional[str]) -> Optional[str]:
    """Uppercase, remove punctuation, normalize whitespace (used for dupe checks)."""
    if not address:
        return None
    cleaned = re.sub(r"[^0-9A-Za-z]+", " ", address)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().upper()
    return cleaned or None


def _parse_multiline_address(raw: str) -> Tuple[str, str, str, str]:
    """
    Parse common Senior Place multiline address:
      street\ncity\nST ZIP\nDirections
    Returns: (full_address, city, state, zip)
    """
    parts = [p.strip() for p in (raw or "").splitlines() if p.strip()]
    # Drop trailing "Directions" line (and any lines after it)
    filtered = []
    for p in parts:
        if p.lower().startswith("directions"):
            break
        filtered.append(p)
    parts = filtered

    street = parts[0] if len(parts) > 0 else ""
    city = parts[1] if len(parts) > 1 else ""
    state = ""
    zip_code = ""
    if len(parts) > 2:
        # Expect "AZ 85001"
        tokens = parts[2].split()
        if tokens:
            state = tokens[0].upper()
        if len(tokens) > 1:
            zip_code = tokens[1]

    full = street
    if city:
        full += f", {city}"
    if state or zip_code:
        full += f", {state} {zip_code}".rstrip()
    return full.strip().strip(","), city, state, zip_code


def normalize_listing_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single CSV row from orchestrator/scraper output into importer-friendly shape.
    This is intentionally conservative; it preserves existing keys when possible.
    """
    out = dict(row or {})

    # Map Senior Place URL into 'url' for legacy scripts
    if out.get("senior_place_url") and not out.get("url"):
        out["url"] = out["senior_place_url"]

    # Map normalized_types into care_types if needed
    if out.get("normalized_types") and not out.get("care_types"):
        out["care_types"] = out["normalized_types"]

    # Handle multiline address format when city/state/zip missing
    addr = out.get("address") or ""
    if "\n" in addr and (not out.get("city") or not out.get("state") or not out.get("zip")):
        full, city, st, z = _parse_multiline_address(addr)
        out["address"] = full
        if city:
            out["city"] = city
        if st:
            out["state"] = st
        if z:
            out["zip"] = z

    return out


def get_care_type_term_ids(care_types: Optional[str]) -> List[int]:
    if not care_types:
        return []
    ids: List[int] = []
    for part in str(care_types).split(","):
        ct = part.strip()
        if not ct:
            continue
        term_id = CARE_TYPE_MAPPING.get(ct)
        if term_id and term_id not in ids:
            ids.append(term_id)
    return ids


def is_blocklisted_title(title: Optional[str]) -> bool:
    if not title:
        return False
    t = title.strip().lower()
    if not t:
        return False
    return any(re.search(p, t, flags=re.IGNORECASE) for p in TITLE_BLOCKLIST_PATTERNS)


def _download_image_bytes(url: str, *, timeout: int = 30) -> Optional[bytes]:
    """
    Minimal image downloader used by image backfill scripts.
    Returns bytes on success, else None.
    """
    if not url or not str(url).strip():
        return None
    r = requests.get(str(url).strip(), timeout=timeout)
    if r.status_code != 200:
        return None
    return r.content or None

