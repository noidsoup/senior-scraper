import json
import re

SENIORLY_FILE = "seniorly_data_resume.jsonl"
SENIORPLACE_FILE = "seniorplace_data.jsonl"

def load_jsonl(filepath):
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data

def normalize_address(address):
    return re.sub(r'\W+', '', address.lower()).strip()

def check_duplicates(seniorly, seniorplace):
    seniorly_keys = {normalize_address(entry["address"]) for entry in seniorly}
    seniorplace_keys = {normalize_address(entry["address"]) for entry in seniorplace}

    duplicates = seniorly_keys & seniorplace_keys
    print(f"✅ Found {len(duplicates)} duplicate addresses.")

    if duplicates:
        print("\nSample duplicate addresses:")
        for key in list(duplicates)[:10]:
            print(f"- {key}")

def main():
    seniorly = load_jsonl(SENIORLY_FILE)
    seniorplace = load_jsonl(SENIORPLACE_FILE)
    check_duplicates(seniorly, seniorplace)

if __name__ == "__main__":
    main()
