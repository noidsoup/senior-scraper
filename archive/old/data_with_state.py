import json
import re
import csv
from pathlib import Path

# Map of state abbreviations to full names
state_map = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
}

# Fallback for common miswritten forms
state_fallbacks = {
    "ARIZ": "AZ", "ARIZONA": "AZ", "NM NM": "NM"
}

input_path = Path("seniorplace_data_non_az.jsonl")
jsonl_output_path = Path("seniorplace_non_az_with_states.jsonl")
csv_output_path = Path("seniorplace_non_az_with_states.csv")

state_regex = re.compile(r",\s*([A-Z]{2})(?:\s+\d{5})?\s*$", re.IGNORECASE)

matched = 0
unmatched = 0
unmatched_examples = []

with input_path.open("r", encoding="utf-8") as infile, \
     jsonl_output_path.open("w", encoding="utf-8") as jsonl_outfile, \
     csv_output_path.open("w", encoding="utf-8", newline="") as csv_outfile:

    csv_writer = None

    for line in infile:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            print("Bad JSON:", line)
            continue

        address = obj.get("address", "").strip()
        abbr = None

        match = state_regex.search(address)
        if match:
            abbr = match.group(1).upper()
        else:
            upper_address = address.upper()
            for fallback, fallback_abbr in state_fallbacks.items():
                if fallback in upper_address:
                    abbr = fallback_abbr
                    break

        state = state_map.get(abbr)
        obj["state"] = state

        if state:
            matched += 1
        else:
            unmatched += 1
            if len(unmatched_examples) < 20:
                unmatched_examples.append(f"- '{address}' → Abbreviation detected: {repr(abbr)}")

        # Write to JSONL
        jsonl_outfile.write(json.dumps(obj) + "\n")

        # Write to CSV
        if csv_writer is None:
            headers = list(obj.keys())
            csv_writer = csv.DictWriter(csv_outfile, fieldnames=headers)
            csv_writer.writeheader()
        csv_writer.writerow(obj)

print()
print("✅ Matched:", matched)
print("❗ Unmatched:", unmatched)
if unmatched_examples:
    print("\n⚠️ Failed to match state in these addresses:")
    for example in unmatched_examples:
        print(example)
print("\n📄 Output written to:")
print("-", jsonl_output_path)
print("-", csv_output_path)
