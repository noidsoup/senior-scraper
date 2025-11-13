#!/usr/bin/env python3
"""
Preview script to show what the California city descriptions will look like.
This creates a template CSV with sample descriptions for major cities.
"""

import csv

def create_sample_descriptions():
    """Create sample descriptions for major California cities."""
    sample_descriptions = {
        "Los Angeles": "Los Angeles offers seniors year-round sunshine, world-class healthcare facilities, and diverse cultural attractions. The city provides access to top medical centers like UCLA and Cedars-Sinai, while offering a range of housing options from beachside communities to urban high-rises. With its mild climate and endless entertainment options, LA provides an active lifestyle for seniors who want to stay engaged and connected.",
        
        "San Francisco": "San Francisco combines stunning natural beauty with excellent healthcare and a vibrant senior community. The city's temperate climate, walkable neighborhoods, and extensive public transportation make it ideal for active seniors. With world-renowned medical facilities like UCSF and a strong focus on wellness, San Francisco offers both urban amenities and peaceful retreats in Golden Gate Park.",
        
        "San Diego": "San Diego provides seniors with perfect weather, beautiful beaches, and exceptional healthcare options. The city's laid-back lifestyle, low crime rates, and abundance of outdoor activities make it ideal for retirement. With top medical facilities like Scripps and Sharp HealthCare, plus a strong senior community, San Diego offers both relaxation and active living opportunities.",
        
        "Sacramento": "Sacramento offers seniors affordable living in California's capital with access to excellent state healthcare programs. The city's tree-lined streets, historic charm, and proximity to the Sierra Nevada mountains provide both urban convenience and natural beauty. With lower costs than coastal cities and quality medical facilities, Sacramento is an attractive option for budget-conscious seniors.",
        
        "Fresno": "Fresno provides seniors with affordable living in California's Central Valley, surrounded by agricultural beauty and mountain views. The city offers a slower pace of life with access to quality healthcare facilities and a growing senior community. With its central location and lower cost of living, Fresno is an excellent choice for seniors seeking value and tranquility.",
        
        "Oakland": "Oakland offers seniors diverse neighborhoods, cultural richness, and easy access to San Francisco's amenities. The city's vibrant arts scene, excellent restaurants, and proximity to nature provide an engaging lifestyle. With improving healthcare options and a strong sense of community, Oakland appeals to seniors who want urban excitement with a more affordable cost of living.",
        
        "Long Beach": "Long Beach combines coastal living with urban amenities, offering seniors beautiful beaches and a vibrant downtown. The city's mild climate, walkable waterfront, and diverse neighborhoods provide both relaxation and activity. With access to excellent healthcare and a strong senior community, Long Beach offers the best of Southern California living at a more reasonable cost than nearby Los Angeles.",
        
        "Bakersfield": "Bakersfield provides seniors with affordable living in California's Central Valley, surrounded by agricultural beauty and mountain views. The city offers a slower pace of life with access to quality healthcare facilities and a growing senior community. With its central location and lower cost of living, Bakersfield is an excellent choice for seniors seeking value and tranquility.",
        
        "Anaheim": "Anaheim offers seniors the magic of Disneyland's hometown with year-round entertainment and excellent healthcare access. The city's family-friendly atmosphere, diverse dining options, and proximity to Orange County's amenities provide both fun and convenience. With its central location and growing senior community, Anaheim appeals to active seniors who want to stay engaged and connected.",
        
        "Santa Ana": "Santa Ana provides seniors with a rich cultural heritage and affordable living in Orange County's heart. The city's historic downtown, diverse neighborhoods, and strong community spirit create a welcoming environment. With access to quality healthcare and a growing arts scene, Santa Ana offers both traditional charm and modern amenities for active seniors."
    }
    
    return sample_descriptions

def main():
    # Read all California cities
    cities_file = "california_cities.txt"
    output_file = "california_city_descriptions_preview.csv"
    
    try:
        with open(cities_file, 'r') as f:
            all_cities = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: {cities_file} not found. Please run the city extraction command first.")
        return
    
    sample_descriptions = create_sample_descriptions()
    
    print(f"Creating preview for {len(all_cities)} California cities")
    print(f"Sample descriptions available for: {list(sample_descriptions.keys())}")
    
    # Write descriptions to CSV
    with open(output_file, "w", newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["City", "State", "Description"])
        
        for city in all_cities:
            if city in sample_descriptions:
                desc = sample_descriptions[city]
                print(f"✅ Using sample description for {city}")
            else:
                desc = f"[AI Description needed for {city}, California - to be generated with OpenAI API]"
                print(f"⏳ Placeholder for {city}")
            
            writer.writerow([city, "CA", desc])
    
    print(f"\n✅ Preview CSV created with {len(all_cities)} cities")
    print(f"📁 Output saved to: {output_file}")
    print(f"\nNext steps:")
    print(f"1. Set OPENAI_API_KEY environment variable")
    print(f"2. Run: python3 generate_california_city_descriptions.py")
    print(f"3. Or test first with: python3 test_california_descriptions.py")

if __name__ == "__main__":
    main()
