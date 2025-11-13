#!/usr/bin/env python3
"""
Test specific listings from the WordPress admin list to find mismatches.
Focus on ones currently showing as "Assisted Living Community" that might be "Assisted Living Home".
"""

import csv
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

# Canonical mapping from memory.md
CANONICAL_MAPPING = {
    'assisted living facility': 'Assisted Living Community',
    'assisted living home': 'Assisted Living Home', 
    'independent living': 'Independent Living',
    'memory care': 'Memory Care',
    'skilled nursing': 'Nursing Home',
    'continuing care retirement community': 'Assisted Living Community',
    'in-home care': 'Home Care',
    'home health': 'Home Care',
    'hospice': 'Home Care',
    'respite care': 'Assisted Living Community',
}

CANONICAL_TO_ID = {
    'Assisted Living Community': 5,
    'Assisted Living Home': 162,
    'Independent Living': 6,
    'Memory Care': 3,
    'Nursing Home': 7,
    'Home Care': 488,
}

def generate_wp_type_field(canonical_types):
    """Generate WordPress serialized type field for multiple types"""
    if not canonical_types:
        return 'a:1:{i:0;i:1;}'  # Uncategorized
    
    type_ids = [CANONICAL_TO_ID[t] for t in canonical_types if t in CANONICAL_TO_ID]
    
    if len(type_ids) == 1:
        return f'a:1:{{i:0;i:{type_ids[0]};}}'
    else:
        # Multiple types: a:N:{i:0;i:ID1;i:1;i:ID2;...}
        items = ''.join(f'i:{i};i:{type_ids[i]};' for i in range(len(type_ids)))
        return f'a:{len(type_ids)}:{{{items}}}'

# Test targets from WordPress admin list - focus on potential mismatches
TEST_LISTINGS = [
    {
        'name': 'Acacia Health Center',
        'current_wp': 'Assisted Living Community, Nursing Home',
        'url': 'https://app.seniorplace.com/communities/show/52fd1227-cc7c-4778-b852-187223b33c53',
        'wp_id': '6780'
    },
    {
        'name': 'Alta Mesa Health And Rehabilitation',
        'current_wp': 'Assisted Living Community, Nursing Home',
        'url': 'https://app.seniorplace.com/communities/show/46885dc2-46fc-45c4-9c19-e1f3efed2a5d',
        'wp_id': None
    },
    {
        'name': 'American Orchards Senior Living',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/e1d9eb3c-138e-4cdd-bd95-a434cda4f9ae',
        'wp_id': None
    },
    {
        'name': 'Arbor Ridge',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/cd2fd2cb-9036-4d42-8b43-13728047d570',
        'wp_id': None
    },
    {
        'name': 'Arbor Rose Senior Care',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/6bd1d1e6-1ddf-4a8f-8cb3-549fd20ef4a3',
        'wp_id': None
    },
    {
        'name': 'Avista Senior Living',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/37f61f7b-d278-43f1-8e69-5908b30eae0d',
        'wp_id': None
    },
    {
        'name': 'Avista Senior Living Lake Havasu',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/df741e72-7ad0-4ab8-b225-cb7dbf8f6bdc',
        'wp_id': None
    },
    {
        'name': 'Beatitudes Campus',
        'current_wp': 'Assisted Living Community, Independent Living, Memory Care, Nursing Home, Home Care',
        'url': 'https://app.seniorplace.com/communities/show/bf36039b-5db3-4d71-91bb-97419ad3b2b5',
        'wp_id': None
    },
    {
        'name': 'Belmont Village Scottsdale',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/df08aab7-bc16-4f3b-ae0b-17292fee1cbe',
        'wp_id': None
    },
    {
        'name': 'Bridgewater Assisted Living',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/5bba8892-3a6f-4135-8bf7-e64d6846f364',
        'wp_id': None
    },
    {
        'name': 'Cave Creek Assisted Living And Memory Care',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/a061bec0-a07e-4af5-bed0-a89106d329a0',
        'wp_id': None
    },
    {
        'name': 'Clearwater Agritopia',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/21d45472-7144-4a48-9c59-3f78fa123ae3',
        'wp_id': None
    },
    {
        'name': 'Desert Palm At The Park',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/62dd26b7-0b3e-4499-aa72-caa6f0404105',
        'wp_id': None
    },
    {
        'name': 'Granite Gate Senior Living',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/98bac21b-dc2a-4226-89bf-874f7da40487',
        'wp_id': None
    },
    {
        'name': 'Hacienda Del Rey',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/87592fb1-dac5-416e-8135-e8fc885dce0d',
        'wp_id': None
    },
    {
        'name': 'Morningstar At Arcadia',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/1ad6edea-7e30-40d4-9687-2619748c8472',
        'wp_id': None
    },
    {
        'name': 'Orchard Pointe At Surprise',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/41514c81-2963-48d7-bfff-0bc1a151a944',
        'wp_id': None
    },
    {
        'name': 'Parkland Memory Care',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/fecda177-944e-4675-962f-99fc3709331a',
        'wp_id': None
    },
    {
        'name': 'Savanna House Assisted Living Memory Care',
        'current_wp': 'Assisted Living Community, Memory Care',
        'url': 'https://app.seniorplace.com/communities/show/b48eecb2-991c-439e-9982-8f9d4cb3c317',
        'wp_id': None
    }
]

async def scrape_community_types_from_attributes(context, url, title):
    """Scrape community types from Senior Place attributes page using exact HTML structure"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="networkidle", timeout=20000)
        
        # Wait for the specific Community Type section
        await page.wait_for_selector('div:has-text("Community Type(s)")', timeout=10000)
        
        # Extract community types using the exact HTML structure provided
        community_types = await page.evaluate("""
            () => {
                const communityTypes = [];
                
                // Find the Community Type(s) section specifically  
                const communityTypeDiv = Array.from(document.querySelectorAll('div')).find(div => 
                    div.textContent && div.textContent.trim() === 'Community Type(s)' && 
                    div.classList.contains('font-bold')
                );
                
                if (!communityTypeDiv) {
                    return [];
                }
                
                // Get the options container that follows the Community Type(s) header
                let optionsContainer = communityTypeDiv.parentElement.querySelector('.options');
                
                if (!optionsContainer) {
                    return [];
                }
                
                // Get all checked checkboxes in this specific section
                const checkedInputs = optionsContainer.querySelectorAll('input[type="checkbox"]:checked');
                
                for (const input of checkedInputs) {
                    // Find the label text next to this checkbox
                    const labelDiv = input.parentElement.querySelector('div.ml-2');
                    if (labelDiv && labelDiv.textContent) {
                        const typeText = labelDiv.textContent.trim();
                        if (typeText) {
                            communityTypes.push(typeText);
                        }
                    }
                }
                
                return communityTypes;
            }
        """)
        
        await page.close()
        return community_types
            
    except Exception as e:
        print(f"    ❌ Error scraping {url}: {str(e)}")
        if 'page' in locals():
            await page.close()
        return []

async def test_specific_listings():
    """Test the specific listings to find mismatches"""
    
    print("🎯 TESTING SPECIFIC LISTINGS FOR MISMATCHES")
    print("=" * 60)
    print("Checking specific listings that might be misclassified")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Login to Senior Place
        print("🔐 Logging into Senior Place...")
        page = await context.new_page()
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', 'allison@aplaceforseniors.org')
        await page.fill('input[name="password"]', 'Hugomax2023!')
        await page.click('button[type="submit"]')
        await page.wait_for_selector('text=Communities', timeout=15000)
        await page.close()
        print("✅ Successfully logged in")
        print()
        
        # Test each listing
        corrections_needed = []
        
        for i, listing in enumerate(TEST_LISTINGS):
            print(f"📋 {i+1}/{len(TEST_LISTINGS)}: {listing['name']}")
            print(f"    Current WP: {listing['current_wp']}")
            
            # Scrape current community types from Senior Place
            community_types = await scrape_community_types_from_attributes(context, listing['url'], listing['name'])
            
            if community_types:
                print(f"    🔍 Senior Place shows: {community_types}")
                
                # Map to canonical types (ALL types, following memory rules)
                canonical_types = []
                for sp_type in community_types:
                    sp_lower = sp_type.lower()
                    if sp_lower in CANONICAL_MAPPING:
                        canonical = CANONICAL_MAPPING[sp_lower]
                        if canonical not in canonical_types:
                            canonical_types.append(canonical)
                
                if canonical_types:
                    should_be_types = ', '.join(canonical_types)
                    print(f"    🎯 Should map to: {should_be_types}")
                    
                    # Check for mismatch (simple string comparison)
                    if should_be_types != listing['current_wp']:
                        print(f"    🚨 MISMATCH FOUND!")
                        print(f"      Current: {listing['current_wp']}")
                        print(f"      Should be: {should_be_types}")
                        
                        # Generate correct WordPress type field
                        correct_type_field = generate_wp_type_field(canonical_types)
                        
                        corrections_needed.append({
                            'Name': listing['name'],
                            'WP_ID': listing.get('wp_id', 'TBD'),
                            'type': correct_type_field,
                            'normalized_types': should_be_types,
                            'senior_place_types': ', '.join(community_types),
                            'current_wp_types': listing['current_wp'],
                            'url': listing['url']
                        })
                    else:
                        print(f"    ✅ CORRECT - No change needed")
                else:
                    print(f"    ⚠️  No canonical mapping found")
            else:
                print(f"    ❌ Failed to get community types")
            
            print()
            
            # Small delay
            await asyncio.sleep(0.5)
        
        await browser.close()
        
        # Results summary
        print(f"\n🎯 TEST RESULTS:")
        print(f"  Total tested: {len(TEST_LISTINGS)}")
        print(f"  Mismatches found: {len(corrections_needed)}")
        print()
        
        if corrections_needed:
            print(f"📋 MISMATCHES FOUND:")
            for i, corr in enumerate(corrections_needed):
                print(f"  {i+1}. {corr['Name']}")
                print(f"     Senior Place: {corr['senior_place_types']}")
                print(f"     Current WP: {corr['current_wp_types']}")
                print(f"     Should be: {corr['normalized_types']}")
                print()
            
            # Save corrections
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            corrections_file = f"organized_csvs/TARGETED_CORRECTIONS_{timestamp}.csv"
            with open(corrections_file, 'w', newline='', encoding='utf-8') as f:
                if corrections_needed:
                    writer = csv.DictWriter(f, fieldnames=corrections_needed[0].keys())
                    writer.writeheader()
                    writer.writerows(corrections_needed)
            
            print(f"💾 Corrections saved: {corrections_file}")
        else:
            print(f"✅ NO MISMATCHES FOUND - All tested listings are correctly mapped!")

def main():
    print("🚀 Testing specific listings for care type mismatches...")
    print()
    
    asyncio.run(test_specific_listings())

if __name__ == "__main__":
    main()
