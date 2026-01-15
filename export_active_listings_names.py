#!/usr/bin/env python3
"""
Export a simple CSV list of ALL active listings (published) from WordPress.

Output:
  - active_listings_names.csv (default) with a single column: name

Auth:
  - For published listings, WordPress often allows public access.
  - If your site restricts the listing endpoint, set WP_USER/WP_PASS (or WP_USERNAME/WP_PASSWORD)
    in `wp_config.env` (gitignored) or your environment.
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
from pathlib import Path
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth


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


def strip_html(text: str) -> str:
    if not text:
        return ""
    # Remove HTML tags and decode entities
    no_tags = re.sub(r"<[^>]*>", "", text)
    return html.unescape(no_tags).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a one-column CSV of all active (published) listings."
    )
    parser.add_argument(
        "--output",
        default="active_listings_names.csv",
        help="Output CSV path (default: active_listings_names.csv)",
    )
    parser.add_argument(
        "--wp-url",
        default=None,
        help="Override WP_URL (default: env WP_URL or https://aplaceforseniorscms.kinsta.cloud)",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=100,
        help="WordPress REST API per_page (default: 100, max is typically 100)",
    )
    parser.add_argument(
        "--status",
        default="publish",
        help="WP post status to export (default: publish). Use 'any' for all statuses (requires auth).",
    )
    parser.add_argument(
        "--include-status",
        action="store_true",
        help="Include a second CSV column: status (useful with --status any).",
    )

    args = parser.parse_args()

    load_env_file()

    wp_url = (args.wp_url or os.getenv("WP_URL") or "https://aplaceforseniorscms.kinsta.cloud").rstrip(
        "/"
    )
    wp_user = os.getenv("WP_USER") or os.getenv("WP_USERNAME")
    wp_pass = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")

    auth: Optional[HTTPBasicAuth] = None
    if wp_user and wp_pass:
        auth = HTTPBasicAuth(wp_user, wp_pass)

    out_path = Path(args.output)

    endpoint = f"{wp_url}/wp-json/wp/v2/listing"
    page = 1
    total_written = 0

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "status"] if args.include_status else ["name"])

        while True:
            params = {
                "status": str(args.status).strip(),
                "per_page": int(args.per_page),
                "page": page,
                "_fields": "id,title,status",
            }

            # Non-publish statuses generally require authentication.
            if params["status"] != "publish" and auth is None:
                raise SystemExit(
                    f"Status '{params['status']}' requires authentication. "
                    "Set WP_USER + WP_PASSWORD in wp_config.env (or env) and re-run."
                )

            r = requests.get(endpoint, params=params, auth=auth, timeout=30)
            if r.status_code in (401, 403) and auth is None:
                raise SystemExit(
                    f"WordPress returned {r.status_code} (auth required). "
                    "Set WP_USER + WP_PASSWORD in wp_config.env and re-run."
                )
            if r.status_code != 200:
                raise SystemExit(f"WordPress error {r.status_code}: {r.text[:300]}")

            batch = r.json()
            if not batch:
                break

            for item in batch:
                title_obj = item.get("title")
                rendered = (
                    title_obj.get("rendered", "") if isinstance(title_obj, dict) else (title_obj or "")
                )
                name = strip_html(str(rendered))
                if name:
                    if args.include_status:
                        writer.writerow([name, item.get("status", "")])
                    else:
                        writer.writerow([name])
                    total_written += 1

            total_pages = int(r.headers.get("X-WP-TotalPages", 1))
            if page >= total_pages:
                break
            page += 1

    label = "active" if str(args.status).strip() == "publish" else str(args.status).strip()
    print(f"✅ Wrote {total_written:,} {label} listing names to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

