import csv
import argparse
from typing import List, Dict, Tuple


CANONICAL = [
    "Assisted Living Community",
    "Assisted Living Home",
    "Independent Living",
    "Memory Care",
    "Nursing Home",
]

SYNONYM_MAP = {
    # Assisted Living Community
    "assisted living facility": "Assisted Living Community",
    "assisted living community": "Assisted Living Community",
    # Assisted Living Home
    "assisted living home": "Assisted Living Home",
    "board and care home": "Assisted Living Home",
    # Independent Living
    "independent living": "Independent Living",
    # Memory Care
    "memory care": "Memory Care",
    # Nursing Home
    "skilled nursing": "Nursing Home",
    "nursing home": "Nursing Home",
}

# Term ID → Canonical Name (from WP ACF taxonomy)
ID_MAP = {
    5: "Assisted Living Community",
    162: "Assisted Living Home",
    6: "Independent Living",
    3: "Memory Care",
    7: "Nursing Home",
    1: "Uncategorized",
}


def normalize_types(raw: str) -> Tuple[List[str], List[str]]:
    """Return (normalized, unknown) given a raw type string.
    Accepts comma-separated lists; ignores serialized arrays like a:1:{...}.
    """
    if not raw:
        return ([], [])
    s = raw.strip()
    # Handle serialized term IDs like a:1:{i:0;i:162;}
    if s.startswith("a:") and s.endswith("}"):
        import re
        ids = [int(x) for x in re.findall(r"i:(\d+)", s)]
        norm: List[str] = []
        unknown_ids: List[str] = []
        for tid in ids:
            name = ID_MAP.get(tid)
            if name and name not in norm:
                norm.append(name)
            elif name is None:
                unknown_ids.append(str(tid))
        return (norm, unknown_ids)
    parts = [p.strip().lower() for p in s.split(',') if p.strip()]
    norm: List[str] = []
    unknown: List[str] = []
    for p in parts:
        mapped = SYNONYM_MAP.get(p)
        if mapped:
            if mapped not in norm:
                norm.append(mapped)
        else:
            unknown.append(p)
    return (norm, unknown)


def audit(input_csv: str, output_csv: str) -> None:
    with open(input_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames or []

    # Choose candidate columns for type info
    candidate_cols = [c for c in header if c.lower() in {"type", "types", "community type", "community types"}]
    # Fallback: try '_type' if present (some exports)
    if "_type" in header:
        candidate_cols.append("_type")

    out_rows: List[Dict[str, str]] = []
    for r in rows:
        raw_vals: List[str] = []
        for c in candidate_cols:
            v = r.get(c, "")
            if v:
                raw_vals.append(str(v))
        raw_joined = "; ".join(raw_vals)
        norm_total: List[str] = []
        unknown_total: List[str] = []
        for v in raw_vals:
            norm, unknown = normalize_types(v)
            for n in norm:
                if n not in norm_total:
                    norm_total.append(n)
            for u in unknown:
                if u not in unknown_total:
                    unknown_total.append(u)
        status = "ok" if norm_total else ("unknown" if unknown_total else "empty")
        out_rows.append({
            "ID": r.get("ID", ""),
            "Title": r.get("Title", r.get("title", "")),
            "RawType": raw_joined,
            "Normalized": ", ".join(norm_total),
            "Unknown": ", ".join(unknown_total),
            "Status": status,
            "SeniorPlaceURL": next((val for key, val in r.items() if isinstance(val, str) and 'seniorplace.com/communities/show/' in val), ""),
            "SeniorlyURL": next((val for key, val in r.items() if isinstance(val, str) and 'seniorly.com' in val), ""),
        })

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "Title", "RawType", "Normalized", "Unknown", "Status", "SeniorPlaceURL", "SeniorlyURL"])
        writer.writeheader()
        writer.writerows(out_rows)

    # Print quick stats
    total = len(out_rows)
    ok = sum(1 for r in out_rows if r["Status"] == "ok")
    empty = sum(1 for r in out_rows if r["Status"] == "empty")
    unknown = sum(1 for r in out_rows if r["Status"] == "unknown")
    print(f"Audited {total} rows → ok={ok}, empty={empty}, unknown={unknown}")
    print(f"Report: {output_csv}")


def main():
    p = argparse.ArgumentParser(description="Audit and normalize listing types to the 5 canonical categories.")
    p.add_argument('--input', required=True, help='Path to export CSV')
    p.add_argument('--output', required=False, help='Output report CSV path')
    args = p.parse_args()
    out = args.output or (args.input.rsplit('.', 1)[0] + '_types_audit.csv')
    audit(args.input, out)


if __name__ == '__main__':
    main()


