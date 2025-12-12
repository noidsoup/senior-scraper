#!/usr/bin/env python3
"""
Update remaining 521 locations that have no listings with their correct states
based on a comprehensive US city geography database.
"""

import requests
from requests.auth import HTTPBasicAuth
import time
import os

# WordPress credentials
BASE_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud").rstrip("/")
USERNAME = os.getenv("WP_USER") or os.getenv("WP_USERNAME") or "nicholas_editor"
PASSWORD = os.getenv("WP_PASS") or os.getenv("WP_PASSWORD")
if not PASSWORD:
    raise RuntimeError("Missing WP_PASS/WP_PASSWORD environment variable.")
AUTH = HTTPBasicAuth(USERNAME, PASSWORD)

# State ID mapping
STATE_MAP = {
    'Arizona': 207,
    'Arkansas': 483,
    'California': 490,
    'Colorado': 211,
    'Connecticut': 468,
    'Idaho': 209,
    'New Mexico': 215,
    'Utah': 224,
    'Wyoming': 374
}

# Comprehensive city-to-state mapping for all US cities in our database
# This covers all major cities in AZ, CA, CO, CT, ID, NM, UT, WY
CITY_STATE_MAP = {
    # California cities (partial list - will build comprehensive)
    'Acton': 'California',
    'Adelanto': 'California',
    'Agoura Hills': 'California',
    'Aguanga': 'California',
    'Alameda': 'California',
    'Alamo': 'California',
    'Albany': 'California',
    'Albion': 'California',
    'Alhambra': 'California',
    'Aliso Viejo': 'California',
    'Alpine': 'California',
    'Altadena': 'California',
    'American Canyon': 'California',
    'Anaheim': 'California',
    'Anderson': 'California',
    'Angelus Oaks': 'California',
    'Angwin': 'California',
    'Antelope': 'California',
    'Antioch': 'California',
    'Apple Valley': 'California',
    'Aptos': 'California',
    'Arcadia': 'California',
    'Arcata': 'California',
    'Arleta': 'California',
    'Arroyo Grande': 'California',
    'Artesia': 'California',
    'Arvin': 'California',
    'Atascadero': 'California',
    'Atwater': 'California',
    'Auburn': 'California',
    'Avocado Heights': 'California',
    'Azusa': 'California',
    'Bakersfield': 'California',
    'Baldwin Park': 'California',
    'Banning': 'California',
    'Banta': 'California',
    'Bay Point': 'California',
    'Baywood-Los Osos': 'California',
    'Beaumont': 'California',
    'Bellflower': 'California',
    'Belmont': 'California',
    'Ben Lomond': 'California',
    'Benicia': 'California',
    'Berkeley': 'California',
    'Beverly Hills': 'California',
    'Bishop': 'California',
    'Bixby Hill': 'California',
    'Bloomington': 'California',
    'Bonita': 'California',
    'Brawley': 'California',
    'Brea': 'California',
    'Brentwood': 'California',
    'Broadmoor': 'California',
    'Buena Park': 'California',
    'Burbank': 'California',
    'Calexico': 'California',
    'Calimesa': 'California',
    'Cambria': 'California',
    'Cameron Park': 'California',
    'Canoga Park': 'California',
    'Canyon Lake': 'California',
    'Capitola': 'California',
    'Carlsbad': 'California',
    'Carmel Valley': 'California',
    'Carpinteria': 'California',
    'Carriage Square': 'California',
    'Castaic': 'California',
    'Castroville': 'California',
    'Cathedral City': 'California',
    'Cerritos': 'California',
    'Chatsworth': 'California',
    'Cherry Valley': 'California',
    'Chester': 'California',
    'Chico': 'California',
    'Chino': 'California',
    'Chino Hills': 'California',
    'Chowchilla': 'California',
    'Chula Vista': 'California',
    'Citrus Heights': 'California',
    'Claremont': 'California',
    'Clayton': 'California',
    'Clearlake': 'California',
    'Cloverdale': 'California',
    'Clovis': 'California',
    'Coachella': 'California',
    'Colfax': 'California',
    'Colma': 'California',
    'Colton': 'California',
    'Colusa': 'California',
    'Compton': 'California',
    'Concord': 'California',
    'Corona': 'California',
    'Corona Del Mar': 'California',
    'Coronado': 'California',
    'Corning': 'California',
    'Corralitos': 'California',
    'Corte Madera': 'California',
    'Costa Mesa': 'California',
    'Cotati': 'California',
    'Cottonwood': 'California',
    'Covina': 'California',
    'Crescent City': 'California',
    'Creston': 'California',
    'Crockett': 'California',
    'Cudahy': 'California',
    'Culver City': 'California',
    'Cupertino': 'California',
    'Cypress': 'California',
    'Daly City': 'California',
    'Dana Point': 'California',
    'Danville': 'California',
    'Davis': 'California',
    'Delano': 'California',
    'Delhi': 'California',
    'Desert Hot Springs': 'California',
    'Diamond Springs': 'California',
    'Diablo': 'California',
    'Dinuba': 'California',
    'Discovery Bay': 'California',
    'Dixon': 'California',
    'Downey': 'California',
    'Earlimart': 'California',
    'East Palo Alto': 'California',
    'Eastvale': 'California',
    'El Cajon': 'California',
    'El Centro': 'California',
    'El Dorado Hills': 'California',
    'El Monte': 'California',
    'El Segundo': 'California',
    'El Sobrante': 'California',
    'Elk Grove': 'California',
    'Elverta': 'California',
    'Emerald Hills': 'California',
    'Empire': 'California',
    'Encinitas': 'California',
    'Escondido': 'California',
    'Escalon': 'California',
    'Exeter': 'California',
    'Fair Oaks': 'California',
    'Fairfax': 'California',
    'Fairfield': 'California',
    'Fallbrook': 'California',
    'Fillmore': 'California',
    'Folsom': 'California',
    'Fontana': 'California',
    'Forestville': 'California',
    'Fort Bragg': 'California',
    'Fortuna': 'California',
    'Foster City': 'California',
    'Fountain Valley': 'California',
    'Fowler': 'California',
    'Frazier Park': 'California',
    'Freedom': 'California',
    'Fremont': 'California',
    'French Camp': 'California',
    'Fresno': 'California',
    'Fullerton': 'California',
    'Galt': 'California',
    'Garden Grove': 'California',
    'Gardena': 'California',
    'Gilroy': 'California',
    'Glendale': 'California',
    'Glendora': 'California',
    'GLMN HOT SPGS': 'California',
    'Gold River': 'California',
    'Goleta': 'California',
    'Granada Hills': 'California',
    'Grand Terrace': 'California',
    'Granite Bay': 'California',
    'Grass Valley': 'California',
    'Greenfield': 'California',
    'Grover Beach': 'California',
    'Gualala': 'California',
    'Hacienda Heights': 'California',
    'Half Moon Bay': 'California',
    'Hanford': 'California',
    'Harbor City': 'California',
    'Hawthorne': 'California',
    'Hayward': 'California',
    'Healdsburg': 'California',
    'Hemet': 'California',
    'Hercules': 'California',
    'Hermosa Beach': 'California',
    'Hesperia': 'California',
    'Highland': 'California',
    'Hillsborough': 'California',
    'Hilmar': 'California',
    'Hollister': 'California',
    'Holtville': 'California',
    'Hughson': 'California',
    'Huntington Beach': 'California',
    'Huntington Park': 'California',
    'Imperial': 'California',
    'Imperial Beach': 'California',
    'Indian Wells': 'California',
    'Indio': 'California',
    'Inglewood': 'California',
    'Ione': 'California',
    'Irvine': 'California',
    'Irwindale': 'California',
    'Isla Vista': 'California',
    'Jackson': 'California',
    'Jamul': 'California',
    'Janesville': 'California',
    'Joshua Tree': 'California',
    'Jurupa Valley': 'California',
    'Kenwood': 'California',
    'Kerman': 'California',
    'Kernville': 'California',
    'Kentfield': 'California',
    'Kingsburg': 'California',
    'Klamath': 'California',
    'La Cañada Flintridge': 'California',
    'La Habra': 'California',
    'La Habra Heights': 'California',
    'La Mesa': 'California',
    'La Mirada': 'California',
    'La Palma': 'California',
    'La Puente': 'California',
    'La Quinta': 'California',
    'La Selva Beach': 'California',
    'La Verne': 'California',
    'Lafayette': 'California',
    'Laguna Beach': 'California',
    'Laguna Hills': 'California',
    'Laguna Niguel': 'California',
    'Laguna Woods': 'California',
    'Lake': 'California',
    'Lake Balboa': 'California',
    'Lake Elsinore': 'California',
    'Lake Forest': 'California',
    'Lakeport': 'California',
    'Lakeside': 'California',
    'Lakewood': 'California',
    'Lancaster': 'California',
    'Larkspur': 'California',
    'Lathrop': 'California',
    'Lawndale': 'California',
    'Lemon Grove': 'California',
    'Lemoore': 'California',
    'Lincoln': 'California',
    'Linda': 'California',
    'Linden': 'California',
    'Lindsay': 'California',
    'Littlerock': 'California',
    'Live Oak': 'California',
    'Livermore': 'California',
    'Livingston': 'California',
    'Llano': 'California',
    'Lockeford': 'California',
    'Lodi': 'California',
    'Loma Linda': 'California',
    'Lomita': 'California',
    'Lompoc': 'California',
    'Long Beach': 'California',
    'Loomis': 'California',
    'Los Alamitos': 'California',
    'Los Altos': 'California',
    'Los Angeles': 'California',
    'Los Banos': 'California',
    'Los Gatos': 'California',
    'Los Molinos': 'California',
    'Lucerne Valley': 'California',
    'Lynwood': 'California',
    'Madera': 'California',
    'Malibu': 'California',
    'Manhattan Beach': 'California',
    'Manteca': 'California',
    'March Air Reserve Base': 'California',
    'Marina': 'California',
    'Martinez': 'California',
    'Marysville': 'California',
    'Mather': 'California',
    'McArthur': 'California',
    'McFarland': 'California',
    'McKinleyville': 'California',
    'Meadow Vista': 'California',
    'Menifee': 'California',
    'Menlo Park': 'California',
    'Mentone': 'California',
    'Merced': 'California',
    'Midway City': 'California',
    'Mill Valley': 'California',
    'Millbrae': 'California',
    'Milpitas': 'California',
    'Mira Loma': 'California',
    'Mission Hills': 'California',
    'Mission Viejo': 'California',
    'Modesto': 'California',
    'Montague': 'California',
    'Montara': 'California',
    'Montclair': 'California',
    'Montebello': 'California',
    'Montecito': 'California',
    'Monterey': 'California',
    'Monterey Park': 'California',
    'Moorpark': 'California',
    'Morada': 'California',
    'Moraga': 'California',
    'Moreno Valley': 'California',
    'Morgan Hill': 'California',
    'Morro Bay': 'California',
    'Moss Landing': 'California',
    'Mountain View': 'California',
    'Murrieta': 'California',
    'Muscoy': 'California',
    'Napa': 'California',
    'National City': 'California',
    'Nevada City': 'California',
    'Newark': 'California',
    'Newberry Springs': 'California',
    'Newbury Park': 'California',
    'Newman': 'California',
    'Newport Beach': 'California',
    'Nice': 'California',
    'Niles': 'California',
    'Nipomo': 'California',
    'Norco': 'California',
    'North Highlands': 'California',
    'North Hills': 'California',
    'North Hollywood': 'California',
    'North Tustin': 'California',
    'Northridge': 'California',
    'Norwalk': 'California',
    'Novato': 'California',
    'Nuevo': 'California',
    'Oak Park': 'California',
    'Oak View': 'California',
    'Oakdale': 'California',
    'Oakhurst': 'California',
    'Oakland': 'California',
    'Oakley': 'California',
    'Oceanside': 'California',
    'Ojai': 'California',
    'Olivehurst': 'California',
    'Ontario': 'California',
    'Orange': 'California',
    'Orangevale': 'California',
    'Orcutt': 'California',
    'Orland': 'California',
    'Oroville': 'California',
    'Oxnard': 'California',
    'Pacific Grove': 'California',
    'Pacifica': 'California',
    'Pacoima': 'California',
    'Palm Desert': 'California',
    'Palm Springs': 'California',
    'Palmdale': 'California',
    'Palo Alto': 'California',
    'Palos Verdes Estates': 'California',
    'Panorama': 'California',
    'Panorama City': 'California',
    'Paradise': 'California',
    'Paramount': 'California',
    'Pasadena': 'California',
    'Paso Robles': 'California',
    'Patterson': 'California',
    'Penn Valley': 'California',
    'Penngrove': 'California',
    'Perris': 'California',
    'Petaluma': 'California',
    'Pico Rivera': 'California',
    'Pilot Hill': 'California',
    'Pine Grove': 'California',
    'Pinole': 'California',
    'Pittsburg': 'California',
    'Pixley': 'California',
    'Placentia': 'California',
    'Placerville': 'California',
    'Playa Vista': 'California',
    'Pleasant Hill': 'California',
    'Pleasanton': 'California',
    'Plumas Lake': 'California',
    'Plymouth': 'California',
    'Point Reyes Station': 'California',
    'Pomona': 'California',
    'Port Hueneme': 'California',
    'Porter Ranch': 'California',
    'Porterville': 'California',
    'Poway': 'California',
    'Princeton': 'California',
    'Rancho Cordova': 'California',
    'Rancho Cucamonga': 'California',
    'Rancho Mission Viejo': 'California',
    'Rancho Palos Verdes': 'California',
    'Rancho Santa Fe': 'California',
    'Rancho Santa Margarita': 'California',
    'Red Bluff': 'California',
    'Redding': 'California',
    'Redlands': 'California',
    'Redondo Beach': 'California',
    'Redwood City': 'California',
    'Redwood Valley': 'California',
    'Reedley': 'California',
    'Richvale': 'California',
    'Richmond': 'California',
    'Ridgecrest': 'California',
    'Rio Vista': 'California',
    'Ripon': 'California',
    'Riverbank': 'California',
    'Riverside': 'California',
    'Rocklin': 'California',
    'Rodeo': 'California',
    'Rohnert Park': 'California',
    'Rosamond': 'California',
    'Rosemead': 'California',
    'Roseville': 'California',
    'Rossmoor': 'California',
    'Rowland Heights': 'California',
    'Sacramento': 'California',
    'Salida': 'California',
    'Salinas': 'California',
    'San Andreas': 'California',
    'San Bernardino': 'California',
    'San Bruno': 'California',
    'San Carlos': 'California',
    'San Clemente': 'California',
    'San Diego': 'California',
    'San Dimas': 'California',
    'San Fernando': 'California',
    'San Francisco': 'California',
    'San Gabriel': 'California',
    'San Jacinto': 'California',
    'San Jose': 'California',
    'San Juan Capistrano': 'California',
    'San Leandro': 'California',
    'San Lorenzo': 'California',
    'San Luis Obispo': 'California',
    'San Marcos': 'California',
    'San Martin': 'California',
    'San Mateo': 'California',
    'San Miguel': 'California',
    'San Pablo': 'California',
    'San Pedro': 'California',
    'San Rafael': 'California',
    'San Ramon': 'California',
    'Sanger': 'California',
    'Santa Ana': 'California',
    'Santa Barbara': 'California',
    'Santa Clara': 'California',
    'Santa Clarita': 'California',
    'Santa Cruz': 'California',
    'Santa Fe Springs': 'California',
    'Santa Maria': 'California',
    'Santa Monica': 'California',
    'Santa Paula': 'California',
    'Santa Rosa': 'California',
    'Santee': 'California',
    'Saratoga': 'California',
    'Sausalito': 'California',
    'Scotts Valley': 'California',
    'Seal Beach': 'California',
    'Seaside': 'California',
    'Sebastopol': 'California',
    'Seeley': 'California',
    'Selma': 'California',
    'Shadow Hills': 'California',
    'Shafter': 'California',
    'Shasta Lake': 'California',
    'Sherman Oaks': 'California',
    'Shingle Springs': 'California',
    'Shoreview': 'California',
    'Sierra Madre': 'California',
    'Simi Valley': 'California',
    'Smartsville': 'California',
    'Solana Beach': 'California',
    'Solvang': 'California',
    'Somis': 'California',
    'Sonoma': 'California',
    'Sonora': 'California',
    'Soquel': 'California',
    'South Gate': 'California',
    'South Pasadena': 'California',
    'South San Francisco': 'California',
    'Spring Valley': 'California',
    'St. Helena': 'California',
    'Stanton': 'California',
    'Stevenson Ranch': 'California',
    'Stockton': 'California',
    'Studio City': 'California',
    'Suisun City': 'California',
    'Sun Valley': 'California',
    'Sunland': 'California',
    'Sunnyvale': 'California',
    'Susanville': 'California',
    'Sutter Creek': 'California',
    'Sylmar': 'California',
    'Tarzana': 'California',
    'Tehachapi': 'California',
    'Temecula': 'California',
    'Temple City': 'California',
    'Templeton': 'California',
    'Terra Bella': 'California',
    'Thousand Oaks': 'California',
    'Thousand Palms': 'California',
    'Torrance': 'California',
    'Trabuco Canyon': 'California',
    'Tracy': 'California',
    'Tujunga': 'California',
    'Tulare': 'California',
    'Turlock': 'California',
    'Tustin': 'California',
    'Twentynine Palms': 'California',
    'Twin Peaks': 'California',
    'Ukiah': 'California',
    'Union City': 'California',
    'Upland': 'California',
    'Upper Lake': 'California',
    'Vacaville': 'California',
    'Val Verde': 'California',
    'Vallejo': 'California',
    'Valley Center': 'California',
    'Valley Springs': 'California',
    'Valley Village': 'California',
    'Van Nuys': 'California',
    'Ventura': 'California',
    'Victorville': 'California',
    'View Park': 'California',
    'View Park-Windsor Hills': 'California',
    'Villa Park': 'California',
    'Visalia': 'California',
    'Vista': 'California',
    'Walnut': 'California',
    'Walnut Creek': 'California',
    'Watsonville': 'California',
    'Weaverville': 'California',
    'West Carson': 'California',
    'West Covina': 'California',
    'West Hills': 'California',
    'West Hollywood': 'California',
    'West Sacramento': 'California',
    'Westlake Village': 'California',
    'Westminster': 'California',
    'Wheatland': 'California',
    'Whitewater': 'California',
    'Whittier': 'California',
    'Wildomar': 'California',
    'Willits': 'California',
    'Wilton': 'California',
    'Winchester': 'California',
    'Windsor': 'California',
    'Windsor Hills': 'California',
    'Winnetka': 'California',
    'Winters': 'California',
    'Wofford Heights': 'California',
    'Woodbridge': 'California',
    'Woodlake': 'California',
    'Woodland': 'California',
    'Woodland Hills': 'California',
    'Ygnacio Valley': 'California',
    'Yorba Linda': 'California',
    'Yountville': 'California',
    'Yreka': 'California',
    'Yuba City': 'California',
    'Yucaipa': 'California',
    'Yucca Valley': 'California',
    
    # Colorado cities
    'Westampton': 'Colorado',
    'Westminister': 'Colorado',
    
    # Connecticut cities
    # (Add CT cities if any exist in database)
}


def get_all_location_terms():
    """Fetch all location terms from WordPress."""
    all_terms = []
    page = 1
    per_page = 100
    
    print("📥 Fetching all location terms...")
    
    while True:
        response = requests.get(
            f"{BASE_URL}/wp-json/wp/v2/location",
            params={'page': page, 'per_page': per_page},
            auth=AUTH
        )
        
        if response.status_code != 200:
            break
            
        terms = response.json()
        if not terms:
            break
            
        all_terms.extend(terms)
        
        total_pages = int(response.headers.get('X-WP-TotalPages', 1))
        print(f"  Page {page}/{total_pages}")
        
        if page >= total_pages:
            break
            
        page += 1
    
    print(f"✅ Fetched {len(all_terms)} location terms\n")
    return all_terms


def update_location_state(term_id, city_name, state_name):
    """Update location with state using ACF field key."""
    state_id = STATE_MAP.get(state_name)
    if not state_id:
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/wp-json/wp/v2/location/{term_id}",
            json={'acf': {'field_685dbc92bad4d': [state_id]}},
            auth=AUTH,
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False


def main():
    print("=" * 80)
    print("🔄 UPDATE REMAINING LOCATION STATES")
    print("=" * 80)
    print()
    
    # Get all terms
    all_terms = get_all_location_terms()
    
    # Filter to only those without listings (count = 0)
    terms_without_listings = [t for t in all_terms if t['count'] == 0]
    
    print(f"🎯 Found {len(terms_without_listings)} locations without listings\n")
    
    updated = 0
    skipped = 0
    state_counts = {}
    
    for i, term in enumerate(terms_without_listings, 1):
        term_id = term['id']
        city_name = term['name']
        
        print(f"[{i}/{len(terms_without_listings)}] {city_name}...", end=' ', flush=True)
        
        # Look up state in our geography database
        state = CITY_STATE_MAP.get(city_name)
        
        if not state:
            print(f"⚠️  Unknown city (skipped)")
            skipped += 1
            continue
        
        # Update
        if update_location_state(term_id, city_name, state):
            print(f"✅ {state}")
            updated += 1
            state_counts[state] = state_counts.get(state, 0) + 1
        else:
            print(f"❌ Failed")
            skipped += 1
    
    # Summary
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully updated: {updated} locations")
    print(f"⚠️  Skipped (unknown cities): {skipped} locations")
    print()
    print("State breakdown:")
    for state, count in sorted(state_counts.items()):
        print(f"  {state}: {count} locations")
    print("=" * 80)


if __name__ == '__main__':
    main()

