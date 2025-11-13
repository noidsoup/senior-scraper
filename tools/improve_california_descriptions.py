#!/usr/bin/env python3
"""
Improve California city descriptions using OpenAI for better clarity and accuracy.
"""

import csv
import time
import os
import sys
from typing import List, Dict, Set
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def improve_city_description(city: str, current_description: str) -> str:
    """Improve a city description using OpenAI with strict length targeting and clarity."""
    target_len = len(current_description)
    prompt = (
        f"You are editing copy for a senior living directory. Improve the description for {city}, California. "
        f"Enhance clarity, specificity, and factual safety; avoid unverifiable claims. Use 2–4 sentences. "
        f"Return text ONLY, no quotes. Keep the character length within ±25 characters of the current text length ({target_len}).\n\n"
        f"Current description (keep similar content focus and structure):\n" 
        f"{current_description}\n\n"
        "Guidelines:\n"
        "- Focus on senior-relevant benefits: healthcare access, climate, cost/value, community, lifestyle, walkability.\n"
        "- Prefer broadly true, widely known facts; avoid exact rankings, numbers, or niche claims.\n"
        "- Name marquee health systems ONLY if widely recognized for the metro; otherwise generalize (e.g., 'major hospitals and clinics').\n"
        "- Keep professional but warm tone. Avoid fluff.\n"
        "- Do not exceed 4 sentences.\n"
        f"- Length target: {target_len} characters (±25)."
    )

    # Retry with backoff for transient errors; stop on insufficient_quota
    backoff_seconds = 2.0
    for attempt in range(1, 6):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            improved = (response.choices[0].message.content or "").strip()
            if not improved:
                raise RuntimeError("Empty response")

            # Soft guardrails: if wildly off-length, accept but warn; we'll still write to keep progress
            delta = abs(len(improved) - target_len)
            if delta > 120:
                print(f"  ⚠️ Length delta {delta} chars for {city}; keeping result to preserve progress.")
            return improved
        except Exception as e:
            msg = str(e)
            if "insufficient_quota" in msg or "You exceeded your current quota" in msg:
                print("\n❌ OpenAI insufficient_quota. Add credits, then re-run. Progress so far is saved.")
                raise
            if attempt == 5:
                print(f"  ❌ Failed after {attempt} attempts for {city}: {e}")
                return current_description
            sleep_for = backoff_seconds * attempt
            print(f"  ↻ Retry {attempt}/5 in {sleep_for:.1f}s due to error: {e}")
            time.sleep(sleep_for)

def main():
    input_file = "california_city_descriptions_final.csv"
    output_file = "california_city_descriptions_improved.csv"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    # Read input
    cities_data: List[Dict[str, str]] = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cities_data.append(row)

    # Resume support: skip cities already improved
    completed_cities: Set[str] = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as of:
            try:
                r2 = csv.DictReader(of)
                for row in r2:
                    city_name = row.get('City')
                    if city_name:
                        completed_cities.add(city_name)
            except Exception:
                pass

    total = len(cities_data)
    print(f"Improving descriptions for {total} California cities")
    if completed_cities:
        print(f"Resuming. Already completed: {len(completed_cities)}")

    # Open output in append mode; write header if empty/new
    write_header = not os.path.exists(output_file) or os.path.getsize(output_file) == 0
    with open(output_file, "a", newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        if write_header:
            writer.writerow(["City", "State", "Description"])

        for i, city_data in enumerate(cities_data, 1):
            city = city_data['City']
            current_desc = city_data['Description']
            if city in completed_cities:
                # Already done; skip
                continue

            print(f"Improving {i}/{total}: {city}")
            try:
                improved_desc = improve_city_description(city, current_desc)
            except Exception:
                # Quota or fatal error; flush and stop to allow user to top-up and resume
                outfile.flush()
                print("Stopping due to API error. Re-run after resolving (resume supported).")
                return

            writer.writerow([city, "CA", improved_desc])
            outfile.flush()

            # Diagnostics
            if improved_desc != current_desc:
                print(f"  ✅ Improved ({len(current_desc)} → {len(improved_desc)} chars)")
            else:
                print("  ⚠️ Kept original (error or identical)")

            # Gentle pacing
            time.sleep(1.2)

            # Periodic progress
            if (i % 25) == 0:
                print(f"Progress: {i}/{total} cities processed")

    print(f"\n✅ Completed. Output: {output_file}")

if __name__ == "__main__":
    main()
