#!/usr/bin/env python3
"""
Update WordPress location taxonomy descriptions via REST API.
Uses application password authentication for secure updates.
"""

import requests
import csv
import time
import argparse
import logging
from typing import List, Dict
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/wp_location_updates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WordPressLocationUpdater:
    """Updates WordPress location taxonomy via REST API"""
    
    def __init__(self, base_url: str, username: str, app_password: str):
        """
        Initialize the WordPress updater.
        
        Args:
            base_url: WordPress site URL (e.g., https://example.com)
            username: WordPress username
            app_password: Application password from WordPress
        """
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        self.auth = (username, app_password)
        
    def get_location_terms(self) -> List[Dict]:
        """Fetch all location taxonomy terms"""
        logger.info("📥 Fetching location terms from WordPress...")
        
        all_terms = []
        page = 1
        per_page = 100
        
        while True:
            url = f"{self.api_url}/location"
            params = {
                'page': page,
                'per_page': per_page,
                'hide_empty': False
            }
            
            response = requests.get(url, params=params, auth=self.auth)
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to fetch terms: {response.status_code}")
                break
                
            terms = response.json()
            if not terms:
                break
                
            all_terms.extend(terms)
            
            # Check if there are more pages
            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            if page >= total_pages:
                break
                
            page += 1
        
        logger.info(f"✅ Fetched {len(all_terms)} location terms")
        return all_terms
    
    def update_term_description(self, term_id: int, description: str, state_id: int = None) -> bool:
        """
        Update a single term's description and optionally state association.
        
        Args:
            term_id: WordPress term ID
            description: New description text
            state_id: Optional state taxonomy term ID for ACF field association
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.api_url}/location/{term_id}"
        data = {'description': description}
        
        # Add ACF state field if state_id provided
        if state_id:
            data['acf'] = {
                'State': [state_id]  # ACF State field (field name, not key)
            }
        
        response = requests.post(url, json=data, auth=self.auth)
        
        if response.status_code == 200:
            return True
        else:
            logger.error(f"❌ Failed to update term {term_id}: {response.status_code}")
            return False
    
    def load_california_descriptions(self, csv_file: str) -> Dict[str, Dict]:
        """
        Load city descriptions from CSV.
        
        Args:
            csv_file: Path to CSV file with city, state, description columns
            
        Returns:
            Dictionary mapping city names to {'description': str, 'state': str}
        """
        descriptions = {}
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Support both formats: "City" or "city", "State" or "state", etc.
                city = row.get('City') or row.get('city')
                state = row.get('State') or row.get('state')
                description = row.get('Description') or row.get('description')
                
                descriptions[city] = {
                    'description': description,
                    'state': state
                }
        
        logger.info(f"📊 Loaded {len(descriptions)} descriptions from {csv_file}")
        return descriptions
    
    def get_state_id(self, state_name: str) -> int:
        """
        Get WordPress state taxonomy term ID by name.
        
        Args:
            state_name: State name (e.g., "California", "Colorado")
            
        Returns:
            State term ID or None if not found
        """
        # State ID mapping (from WordPress)
        # Note: "CA" (953) is a duplicate and should NOT be used - always use "California" (490)
        state_map = {
            'Arizona': 207,
            'Arkansas': 483,
            'CA': 490,  # Map CA to California ID (490), not the duplicate CA term (953)
            'California': 490,
            'Colorado': 211,
            'Connecticut': 468,
            'Idaho': 209,
            'New Mexico': 215,
            'Utah': 224,
            'Wyoming': 374
        }
        
        return state_map.get(state_name)
    
    def update_california_cities(self, csv_file: str, force_update: bool = False) -> int:
        """
        Update California city descriptions.
        
        Args:
            csv_file: Path to CSV with improved descriptions
            force_update: If True, update all terms. If False, only update empty descriptions.
            
        Returns:
            Number of terms updated
        """
        logger.info("🔄 Starting California location updates via REST API")
        logger.info("-" * 60)
        
        # Load descriptions
        descriptions = self.load_california_descriptions(csv_file)
        
        # Get current terms
        terms = self.get_location_terms()
        
        # Find California cities that need updates
        updated_count = 0
        skipped_count = 0
        
        for term in terms:
            term_name = term['name']
            term_slug = term['slug']
            current_description = term.get('description', '').strip()
            
            # Check if this city is in our list
            if term_name in descriptions:
                city_data = descriptions[term_name]
                new_description = city_data['description']
                state_name = city_data['state']
                state_id = self.get_state_id(state_name)
                
                # Skip if description hasn't changed
                if current_description == new_description:
                    logger.info(f"⏭️  Skipping {term_name} (unchanged)")
                    skipped_count += 1
                    continue
                
                # Update if empty or force_update is True
                if not current_description or force_update:
                    logger.info(f"📍 Updating {term_name} ({term_slug}) - State: {state_name}...")
                    
                    if self.update_term_description(term['id'], new_description, state_id):
                        updated_count += 1
                    
                    # Small delay to be respectful
                    time.sleep(0.5)
                else:
                    logger.info(f"⏭️  Skipping {term_name} (has existing description)")
                    skipped_count += 1
        
        logger.info("-" * 60)
        logger.info(f"✅ Updated {updated_count} California city descriptions")
        logger.info(f"⏭️  Skipped {skipped_count} cities (unchanged or has content)")
        return updated_count


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Update WordPress location taxonomy descriptions via REST API'
    )
    parser.add_argument('--url', required=True, help='WordPress site URL')
    parser.add_argument('--username', required=True, help='WordPress username')
    parser.add_argument('--password', required=True, help='WordPress application password')
    parser.add_argument('--csv', required=True, help='CSV file with descriptions')
    parser.add_argument('--force', action='store_true', help='Force update all terms')
    
    args = parser.parse_args()
    
    # Ensure log directory exists
    Path('data/logs').mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("WordPress Location Taxonomy Updater")
    logger.info("=" * 60)
    
    try:
        updater = WordPressLocationUpdater(
            base_url=args.url,
            username=args.username,
            app_password=args.password
        )
        
        updated = updater.update_california_cities(args.csv, force_update=args.force)
        
        logger.info("🎉 Update process complete!")
        logger.info(f"📊 Total updates: {updated}")
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()

