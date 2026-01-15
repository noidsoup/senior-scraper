#!/usr/bin/env python3
"""
Parse "raw" FUB (Follow Up Boss) copy/pastes into structured records.

Supported input formats (auto-detected):
  1) JSON: list[dict] or dict
  2) CSV: header row + comma-separated values
  3) TSV: header row + tab-separated values (common from spreadsheets/CRMs)
  4) Key: Value blocks separated by blank lines (common email/CRM detail copy)

Outputs:
  - JSON (default): samples/fub_sample_records.json
  - Optional CSV (if headers are consistent): samples/fub_sample_records.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _looks_like_json(text: str) -> bool:
    s = text.lstrip()
    return s.startswith("{") or s.startswith("[")


def _parse_json(text: str) -> List[Dict[str, Any]]:
    obj = json.loads(text)
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        return [obj]
    return []


def _parse_delimited(text: str, delimiter: str) -> List[Dict[str, Any]]:
    f = io.StringIO(text)
    reader = csv.DictReader(f, delimiter=delimiter)
    out: List[Dict[str, Any]] = []
    for row in reader:
        # drop completely empty rows
        if not any((v or "").strip() for v in row.values()):
            continue
        out.append({k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return out


KEYVAL_RE = re.compile(r"^\s*([^:]{1,80})\s*:\s*(.*?)\s*$")


def _parse_keyval_blocks(text: str) -> List[Dict[str, Any]]:
    blocks = re.split(r"\n\s*\n+", text.strip(), flags=re.MULTILINE)
    out: List[Dict[str, Any]] = []
    for b in blocks:
        rec: Dict[str, Any] = {}
        for line in b.splitlines():
            m = KEYVAL_RE.match(line)
            if not m:
                # If there's a stray line, append to a special notes field
                if line.strip():
                    rec["_notes"] = (str(rec.get("_notes", "")) + "\n" + line.strip()).strip()
                continue
            k = m.group(1).strip()
            v = m.group(2).strip()
            if k in rec:
                # repeated key -> make it a list
                if not isinstance(rec[k], list):
                    rec[k] = [rec[k]]
                rec[k].append(v)
            else:
                rec[k] = v
        if rec:
            out.append(rec)
    return out


def detect_and_parse(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    raw = text.strip("\ufeff")
    if not raw.strip():
        return "empty", []

    if _looks_like_json(raw):
        try:
            return "json", _parse_json(raw)
        except Exception:
            pass

    # TSV is common if user copy/pastes from tables
    if "\t" in raw.splitlines()[0]:
        try:
            return "tsv", _parse_delimited(raw, "\t")
        except Exception:
            pass

    # CSV heuristic: first line has multiple commas and later lines too
    first = raw.splitlines()[0]
    if first.count(",") >= 2:
        try:
            return "csv", _parse_delimited(raw, ",")
        except Exception:
            pass

    # Fallback: key: value blocks
    return "keyval", _parse_keyval_blocks(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse FUB raw paste into JSON/CSV.")
    parser.add_argument(
        "--input",
        default=None,
        help="Path to raw paste text file. If omitted, reads from stdin.",
    )
    parser.add_argument("--out-dir", default="samples", help="Output directory (default: samples)")
    parser.add_argument(
        "--write-csv",
        action="store_true",
        help="Also write CSV if records have a consistent set of keys.",
    )
    args = parser.parse_args()

    text = ""
    if args.input:
        text = Path(args.input).read_text(encoding="utf-8", errors="replace")
    else:
        text = io.TextIOWrapper(getattr(__import__("sys"), "stdin").buffer, encoding="utf-8", errors="replace").read()

    kind, records = detect_and_parse(text)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "fub_sample_records.json"
    json_path.write_text(json.dumps({"format": kind, "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Parsed {len(records)} records (format={kind}) -> {json_path}")

    if args.write_csv and records:
        keys = list(records[0].keys())
        if all(set(r.keys()) == set(keys) for r in records):
            csv_path = out_dir / "fub_sample_records.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                for r in records:
                    w.writerow(r)
            print(f"✅ Wrote CSV -> {csv_path}")
        else:
            print("ℹ️ Skipped CSV: records don't share a consistent key set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

