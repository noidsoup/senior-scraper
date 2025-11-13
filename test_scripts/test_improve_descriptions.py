#!/usr/bin/env python3
"""
Test script to improve a few California city descriptions first.
"""

import csv
import time
import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def improve_city_description(city, current_description):
    """Improve a city description using OpenAI."""
    prompt = f"""Please improve this description for {city}, California as a senior living destination. Make it more accurate, specific, and engaging while maintaining the exact same length and format.

Current description: "{current_description}"

Requirements:
1. Keep 2-4 sentences (same as current)
2. Maintain similar length (300-350 characters)
3. Focus on senior living benefits (healthcare, climate, cost, community, lifestyle)
4. Be specific about what makes {city} unique
5. Use accurate, verifiable information
6. Match the tone: professional but warm, informative but engaging
7. Include specific details about healthcare, climate, or local amenities when relevant
8. Avoid generic language - be specific to {city}
9. Keep the same structure and flow as the original

Improved description:"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error improving description for {city}: {e}")
        return current_description  # Return original if error

def main():
    # Test with a few cities first
    test_cities = ["Los Angeles", "San Francisco", "Sacramento", "Fresno", "Oakland"]
    
    print(f"Testing improvements for {len(test_cities)} cities")
    
    # Read existing descriptions
    cities_data = []
    with open("california_city_descriptions_final.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['City'] in test_cities:
                cities_data.append(row)
    
    print(f"Found {len(cities_data)} test cities to improve")
    
    # Write improved descriptions to CSV
    output_file = "test_improved_descriptions.csv"
    with open(output_file, "w", newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["City", "State", "Description"])
        
        for i, city_data in enumerate(cities_data, 1):
            city = city_data['City']
            current_desc = city_data['Description']
            
            print(f"\n--- Improving {i}/{len(cities_data)}: {city} ---")
            print(f"ORIGINAL: {current_desc}")
            print(f"Length: {len(current_desc)} characters")
            
            improved_desc = improve_city_description(city, current_desc)
            print(f"IMPROVED: {improved_desc}")
            print(f"Length: {len(improved_desc)} characters")
            
            writer.writerow([city, "CA", improved_desc])
            
            # Rate limiting
            time.sleep(2)
    
    print(f"\n✅ Test completed! Check {output_file}")

if __name__ == "__main__":
    main()
