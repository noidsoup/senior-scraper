#!/usr/bin/env python3
"""
Generate comprehensive AI-style descriptions for all California cities.
Uses template-based approach to create professional descriptions.
"""

import csv
import random

def generate_city_description(city):
    """Generate a senior living description for a California city."""
    
    # Template components for different types of cities
    coastal_templates = [
        f"{city} offers seniors stunning coastal living with year-round mild weather and beautiful ocean views. The city provides excellent healthcare access and a relaxed lifestyle perfect for retirement. With its walkable neighborhoods and strong sense of community, {city} is ideal for seniors seeking both tranquility and active living.",
        f"Seniors in {city} enjoy the perfect blend of coastal beauty and urban convenience. The city's temperate climate, excellent healthcare facilities, and vibrant senior community create an ideal retirement destination. {city} offers both peaceful beachside living and easy access to cultural attractions and amenities.",
        f"{city} provides seniors with exceptional coastal living, featuring mild weather, beautiful scenery, and top-quality healthcare. The city's walkable neighborhoods and strong community spirit make it perfect for active seniors. With its combination of natural beauty and modern amenities, {city} offers an ideal retirement lifestyle."
    ]
    
    inland_templates = [
        f"{city} offers seniors affordable living in California's diverse landscape with access to excellent healthcare and community services. The city provides a slower pace of life with modern amenities and a growing senior population. With its central location and lower cost of living, {city} is an attractive option for budget-conscious retirees.",
        f"Seniors in {city} enjoy a peaceful lifestyle with access to quality healthcare and community resources. The city's affordable housing options and strong sense of community make it ideal for retirement. {city} offers both urban convenience and natural beauty, perfect for seniors seeking value and tranquility.",
        f"{city} provides seniors with comfortable living in California's heartland, featuring affordable housing and quality healthcare access. The city's friendly community and growing senior services create an ideal retirement environment. With its central location and reasonable costs, {city} offers excellent value for active seniors."
    ]
    
    major_city_templates = [
        f"{city} offers seniors world-class healthcare, diverse cultural attractions, and endless entertainment options. The city provides excellent public transportation and walkable neighborhoods perfect for active seniors. With its vibrant senior community and top medical facilities, {city} is ideal for those seeking an engaging urban retirement.",
        f"Seniors in {city} enjoy access to premier healthcare systems, cultural diversity, and abundant recreational opportunities. The city's excellent public services and strong senior community create an ideal retirement destination. {city} offers both urban excitement and peaceful retreats, perfect for active retirees.",
        f"{city} provides seniors with exceptional healthcare access, cultural richness, and modern amenities in California's vibrant landscape. The city's diverse neighborhoods and strong community support make it perfect for retirement. With its combination of urban convenience and natural beauty, {city} offers an ideal senior living environment."
    ]
    
    # Special cases for major cities
    major_cities = {
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
    
    # Check if it's a major city first
    if city in major_cities:
        return major_cities[city]
    
    # Determine city type based on name patterns
    coastal_indicators = ["beach", "coast", "bay", "ocean", "marina", "laguna", "carmel", "malibu", "manhattan beach", "redondo beach", "hermosa beach", "venice", "santa monica", "newport beach", "huntington beach", "dana point", "san clemente", "carlsbad", "encinitas", "del mar", "solana beach", "la jolla", "coronado", "imperial beach", "chula vista", "national city", "san diego", "long beach", "manhattan beach", "hermosa beach", "redondo beach", "venice", "santa monica", "malibu", "manhattan beach", "hermosa beach", "redondo beach", "venice", "santa monica", "malibu"]
    
    major_city_indicators = ["los angeles", "san francisco", "san diego", "sacramento", "fresno", "oakland", "long beach", "bakersfield", "anaheim", "santa ana", "san jose", "fremont", "san bernardino", "modesto", "stockton", "fontana", "santa clarita", "huntington beach", "glendale", "santa rosa", "fremont", "san mateo", "hacienda heights", "east los angeles", "concord", "roseville", "thousand oaks", "visalia", "simi valley", "santa clara", "vallejo", "victorville", "pasadena", "el monte", "berkeley", "downey", "west covina", "inglewood", "carlsbad", "fairfield", "richmond", "antioch", "temecula", "elk grove", "santa maria", "palmdale", "westminster", "santa barbara", "hanford", "citrus heights", "redding", "santa monica", "chico", "newport beach", "hawthorne", "buena park", "lakewood", "hemet", "chula vista", "san leandro", "beverly hills", "menifee", "indio", "westminster", "santa clara", "redwood city", "alhambra", "livermore", "buena park", "lakewood", "hemet", "chula vista", "san leandro", "beverly hills", "menifee", "indio", "westminster", "santa clara", "redwood city", "alhambra", "livermore"]
    
    city_lower = city.lower()
    
    if any(indicator in city_lower for indicator in coastal_indicators):
        return random.choice(coastal_templates)
    elif any(indicator in city_lower for indicator in major_city_indicators):
        return random.choice(major_city_templates)
    else:
        return random.choice(inland_templates)

def main():
    # Read all California cities
    cities_file = "california_cities.txt"
    output_file = "california_city_descriptions_final.csv"
    
    try:
        with open(cities_file, 'r') as f:
            all_cities = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: {cities_file} not found. Please run the city extraction command first.")
        return
    
    print(f"Generating descriptions for {len(all_cities)} California cities")
    
    # Write descriptions to CSV
    with open(output_file, "w", newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["City", "State", "Description"])
        
        for i, city in enumerate(all_cities, 1):
            print(f"Processing {i}/{len(all_cities)}: {city}")
            desc = generate_city_description(city)
            writer.writerow([city, "CA", desc])
            
            # Progress update every 50 cities
            if i % 50 == 0:
                print(f"Progress: {i}/{len(all_cities)} cities processed")
    
    print(f"\n✅ Generated descriptions for {len(all_cities)} California cities")
    print(f"📁 Output saved to: {output_file}")

if __name__ == "__main__":
    main()
