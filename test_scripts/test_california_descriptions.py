#!/usr/bin/env python3
"""
Test script to generate AI descriptions for a few California cities first.
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
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating description for {city}: {e}")
        return f"Error generating description for {city}"

def main():
    # Test with a few major California cities
    test_cities = [
        "Los Angeles",
        "San Francisco", 
        "San Diego",
        "Sacramento",
        "Fresno",
        "Oakland",
        "Long Beach",
        "Bakersfield",
        "Anaheim",
        "Santa Ana"
    ]
    
    print(f"Testing with {len(test_cities)} major California cities")
    
    # Write descriptions to CSV
    output_file = "test_california_city_descriptions.csv"
    with open(output_file, "w", newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["City", "State", "Description"])
        
        for i, city in enumerate(test_cities, 1):
            print(f"Processing {i}/{len(test_cities)}: {city}")
            desc = generate_city_description(city)
            writer.writerow([city, "CA", desc])
            print(f"  Generated: {desc[:100]}...")
            
            # Rate limiting
            time.sleep(1.5)
    
    print(f"✅ Test completed! Generated descriptions for {len(test_cities)} cities")
    print(f"📁 Output saved to: {output_file}")

if __name__ == "__main__":
    main()
