#!/usr/bin/env python3
"""
Generate AI-improved descriptions for cities without descriptions.
Uses Anthropic Claude Sonnet 4 API to create unique, senior-focused descriptions.
"""

import os
import sys
import time
import csv
from anthropic import Anthropic

def improve_city_description(client: Anthropic, city: str) -> str:
    """Generate an improved description for a city using Claude API"""
    
    prompt = f"""Write a 2-3 sentence description for {city} that would help seniors decide if it's a good place to retire. 

Focus on:
- Geographic location and climate
- Healthcare access (mention specific hospitals/medical centers if it's a well-known area)
- Senior-friendly amenities and lifestyle
- Cost of living if notable
- Unique characteristics that make it special

Be specific and accurate. Avoid generic phrases. Write in a warm, informative tone.

Return ONLY the description text, no quotes or extra formatting."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        description = message.content[0].text.strip()
        # Remove any surrounding quotes
        description = description.strip('"').strip("'")
        
        return description
        
    except Exception as e:
        print(f"❌ Error generating description for {city}: {e}")
        return ""

def main():
    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Fatal error: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Initialize Anthropic client
    client = Anthropic(api_key=api_key)
    
    # Read cities without descriptions
    with open('cities_without_descriptions.txt', 'r') as f:
        cities = [line.strip() for line in f if line.strip()]
    
    print(f"🚀 Generating descriptions for {len(cities)} cities...")
    print(f"⏱️  Estimated time: ~{len(cities) * 3 // 60} minutes")
    print()
    
    # Prepare output CSV and log file
    output_file = 'missing_city_descriptions_generated.csv'
    log_file = 'missing_city_descriptions.log'
    
    results = []
    success_count = 0
    fail_count = 0
    
    # Open log file
    log = open(log_file, 'w')
    log.write(f"Starting generation for {len(cities)} cities\n")
    log.flush()
    
    for i, city in enumerate(cities, 1):
        msg = f"[{i}/{len(cities)} - {i*100//len(cities)}%] {city}..."
        print(msg, end=' ', flush=True)
        log.write(msg + '\n')
        log.flush()
        
        start_time = time.time()
        description = improve_city_description(client, city)
        elapsed = time.time() - start_time
        
        if description:
            results.append({
                'city': city,
                'state': 'California',  # Most are CA, will manually fix CO ones
                'description': description
            })
            success_count += 1
            print(f"✅ ({elapsed:.1f}s)")
            log.write(f"✅ Generated in {elapsed:.1f}s\n")
        else:
            fail_count += 1
            print(f"❌ Failed ({elapsed:.1f}s)")
            log.write(f"❌ Failed after {elapsed:.1f}s\n")
        log.flush()
        
        # Rate limiting: 1 second delay between requests
        if i < len(cities):
            time.sleep(1)
    
    # Write results to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['city', 'state', 'description'])
        writer.writeheader()
        writer.writerows(results)
    
    summary = f"""
{'=' * 80}
✅ Complete! Generated {success_count} descriptions
❌ Failed: {fail_count}
📄 Output: {output_file}

Next step: Update WordPress using:
  python3 update_wp_locations_api.py --csv {output_file} --force
"""
    print(summary)
    log.write(summary)
    log.close()

if __name__ == '__main__':
    main()

