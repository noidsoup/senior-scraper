#!/usr/bin/env python3
"""
Generate AI descriptions for California cities for senior living.
Based on the existing format from generate_descriptions.py
"""

import csv
import time
import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_city_description(city):
    """Generate a senior living description for a California city."""
    prompt = f"""Write a short paragraph (2–4 sentences) describing why {city}, California is a good place for senior living. Focus on healthcare, climate, cost of living, peacefulness, and lifestyle. Match this tone: 'Tucson combines natural beauty with rich cultural history, offering seniors warm weather, affordable living, and access to excellent healthcare.'"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using latest model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating description for {city}: {e}")
        return f"Error generating description for {city}"

def main():
    # Read cities from the generated file
    cities_file = "california_cities.txt"
    output_file = "california_city_descriptions.csv"
    
    if not os.path.exists(cities_file):
        print(f"Error: {cities_file} not found. Please run the city extraction command first.")
        return
    
    # Read cities
    with open(cities_file, 'r') as f:
        cities = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(cities)} California cities to process")
    
    # Write descriptions to CSV
    with open(output_file, "w", newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["City", "State", "Description"])
        
        for i, city in enumerate(cities, 1):
            print(f"Processing {i}/{len(cities)}: {city}")
            desc = generate_city_description(city)
            writer.writerow([city, "CA", desc])
            
            # Rate limiting - be respectful to OpenAI API
            time.sleep(1.5)
            
            # Save progress every 50 cities
            if i % 50 == 0:
                print(f"Progress: {i}/{len(cities)} cities processed")
                outfile.flush()
    
    print(f"✅ Generated descriptions for {len(cities)} California cities")
    print(f"📁 Output saved to: {output_file}")

if __name__ == "__main__":
    main()
