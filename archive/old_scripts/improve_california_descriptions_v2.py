#!/usr/bin/env python3
"""
Improve California city descriptions with location-specific content.
Uses AI to generate accurate, engaging descriptions for senior living locations.
"""

import csv
import time
import logging
from pathlib import Path
from anthropic import Anthropic
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/improve_descriptions_v2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def generate_city_description(client: Anthropic, city: str, state: str) -> str:
    """
    Generate an improved, location-specific description for a California city.
    
    Args:
        client: Anthropic API client
        city: City name
        state: State abbreviation (CA)
    
    Returns:
        Improved description string
    """
    prompt = f"""Generate a 2-3 sentence description for {city}, California as a senior living location.

Requirements:
- Be specific to {city}'s actual characteristics (climate, location, amenities)
- Mention relevant features for seniors (healthcare, community, lifestyle)
- Keep it factual and informative, not generic
- Around 150-200 characters
- Natural, engaging tone
- NO repetitive phrases like "offers seniors" or "provides seniors"
- Focus on what makes THIS city unique

Example good descriptions:
- "Palm Springs is a renowned desert retirement destination with year-round sunshine, world-class golf courses, and a thriving senior community. The city offers excellent healthcare facilities and a relaxed, resort-style lifestyle."
- "San Francisco provides seniors with walkable neighborhoods, mild coastal climate, and access to world-renowned medical centers like UCSF. The city's cultural richness and public transit make it ideal for active retirees."

Now write a unique description for {city}, California:"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        description = message.content[0].text.strip()
        # Remove quotes if AI added them
        description = description.strip('"').strip("'")
        
        logger.info(f"✅ Generated description for {city}")
        return description
        
    except Exception as e:
        logger.error(f"❌ Error generating description for {city}: {e}")
        return f"{city} offers seniors a comfortable California lifestyle with access to quality healthcare and community amenities."


def improve_descriptions(input_file: str, output_file: str):
    """
    Read existing descriptions and generate improved versions.
    
    Args:
        input_file: Path to input CSV with current descriptions
        output_file: Path to output CSV with improved descriptions
    """
    # Initialize Anthropic client
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = Anthropic(api_key=api_key)
    
    # Read input file
    cities = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cities = list(reader)
    
    logger.info(f"📊 Loaded {len(cities)} cities from {input_file}")
    logger.info("🚀 Starting description improvement process...")
    logger.info("-" * 60)
    
    # Generate improved descriptions
    improved_cities = []
    for i, city_data in enumerate(cities, 1):
        city = city_data['City']
        state = city_data['State']
        
        logger.info(f"[{i}/{len(cities)}] Processing {city}, {state}...")
        
        # Generate new description
        new_description = generate_city_description(client, city, state)
        
        improved_cities.append({
            'City': city,
            'State': state,
            'Description': new_description
        })
        
        # Rate limiting - be respectful to API
        if i < len(cities):  # Don't sleep after last one
            time.sleep(1)  # 1 second between requests
    
    # Write output file
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['City', 'State', 'Description'])
        writer.writeheader()
        writer.writerows(improved_cities)
    
    logger.info("-" * 60)
    logger.info(f"✅ Improved descriptions written to {output_file}")
    logger.info(f"📈 Total cities processed: {len(improved_cities)}")


def main():
    """Main execution function"""
    input_file = 'california_city_descriptions_final.csv'
    output_file = 'california_city_descriptions_improved_v2.csv'
    
    # Ensure directories exist
    Path('data/logs').mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("California City Descriptions Improvement v2")
    logger.info("=" * 60)
    
    try:
        improve_descriptions(input_file, output_file)
        logger.info("🎉 Description improvement complete!")
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()

