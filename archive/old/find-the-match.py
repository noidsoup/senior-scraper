import json
import csv
import re

# Enhanced address normalization

def normalize_address(raw):
    raw = raw.lower()
    raw = re.sub(r'[.,]', '', raw)

    corrections = {
        "dirve": "drive",
        "drvie": "drive",
        "strret": "street",
        "strt": "street",
        "stret": "street",
        "avenew": "avenue",
        "aveneu": "avenue",
        "rd": "road",
        "rd.": "road",
        "blvd": "boulevard",
        "dr": "drive",
        "ln": "lane",
        "st": "street",
        "ave": "avenue",
        "apt": "apartment",
        "ste": "suite",
        "e": "east",
        "w": "west",
        "n": "north",
        "s": "south"
    }

    for wrong, right in corrections.items():
        raw = re.sub(rf'\b{wrong}\b', right, raw)

    raw = re.sub(r'\s+', ' ', raw).strip()
    return raw

# Load CRM (SeniorPlace) listings
with open("seniorplace_data.jsonl", "r", encoding="utf-8") as f:
    crm_listings = [json.loads(line) for line in f if line.strip()]

# Load Seniorly CSV listings
seniorly_listings = []
with open("seniorly_data_resume.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        row["normalized_address"] = normalize_address(row["address"])
        seniorly_listings.append(row)

# Normalize CRM addresses into a set
crm_addresses = {
    normalize_address(listing["address"]) for listing in crm_listings
}

# Match by normalized address
matches = [s for s in seniorly_listings if s["normalized_address"] in crm_addresses]

# Write result
with open("matching_seniorly_listings.csv", "w", newline="", encoding="utf-8") as f:
    fieldnames = list(matches[0].keys()) if matches else []
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(matches)

print(f"✅ Found {len(matches)} matching Seniorly listings written to matching_seniorly_listings.csv")