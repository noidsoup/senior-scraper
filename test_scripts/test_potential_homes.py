#!/usr/bin/env python3
"""
Test specific listings that might be small homes misclassified as communities.
Focus on ones that sound like they could be smaller facilities.
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

# Test listings that sound like they could be small homes but are currently marked as "Community"
POTENTIAL_HOMES = [
    {
        'name': 'Cerbat Guest Home',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/b3aac00b-2f40-4799-9dc7-560f1b139636',
        'reason': 'Name contains "Guest Home"'
    },
    {
        'name': 'Bee Hive Homes',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/2f41c0b4-77aa-4f36-aa53-9dc83c752b70',
        'reason': 'Bee Hive is known for small homes'
    },
    {
        'name': 'Bee Hive Homes Of Arrowhead',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/baf127b9-cd1d-4ef4-b585-e259004a9189',
        'reason': 'Bee Hive is known for small homes'
    },
    {
        'name': 'Beehive Homes Of Page Elk Rd',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/062921c8-ce81-4748-85c8-c1c83f7fc3f5',
        'reason': 'Bee Hive is known for small homes'
    },
    {
        'name': 'Beehive Homes Of Sierra Vista',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/a04d19e6-b5c9-457c-97a4-f37b533cf0cf',
        'reason': 'Bee Hive is known for small homes'
    },
    {
        'name': 'Carriage House On West Garden Lane',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/aa22d800-7e20-438d-9bfb-30e7c3e67527',
        'reason': 'Name contains "House"'
    },
    {
        'name': 'Rainbow Acres',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/7331686b-9e7d-4373-82a9-e3da5ca75563',
        'reason': 'Sounds like a smaller facility'
    },
    {
        'name': 'Mayfair Edem Homes',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/a49fb95e-5743-41b9-be5c-b2ddb3ebaf96',
        'reason': 'Name contains "Homes"'
    },
    {
        'name': 'Obsidian Homes Ral',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/76b5268d-0db6-4dfd-8a81-5bb54aa3097a',
        'reason': 'Name contains "Homes"'
    },
    {
        'name': 'Rose Court Senior Living',
        'current_wp': 'Assisted Living Community',
        'url': 'https://app.seniorplace.com/communities/show/24084fc1-9dcf-42a7-90a8-429e495ec5ca',
        'reason': 'Could be a smaller facility'
    }
]

async def scrape_community_types_from_attributes(context, url, title):
    """Scrape community types from Senior Place attributes page"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="networkidle", timeout=20000)
        
        # Wait for the specific Community Type section
        await page.wait_for_selector('div:has-text("Community Type(s)")', timeout=10000)
        
        # Extract community types using the exact HTML structure
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

async def test_potential_homes():
    """Test listings that might be homes misclassified as communities"""
    
    print("🏠 TESTING POTENTIAL HOMES MISCLASSIFIED AS COMMUNITIES")
    print("=" * 65)
    print("Checking listings that might be small homes but are marked as communities")
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
        
        # Test each potential home
        corrections_needed = []
        
        for i, listing in enumerate(POTENTIAL_HOMES):
            print(f"🏠 {i+1}/{len(POTENTIAL_HOMES)}: {listing['name']}")
            print(f"    Current WP: {listing['current_wp']}")
            print(f"    Test reason: {listing['reason']}")
            
            # Scrape current community types from Senior Place
            community_types = await scrape_community_types_from_attributes(context, listing['url'], listing['name'])
            
            if community_types:
                print(f"    🔍 Senior Place shows: {community_types}")
                
                # Map to canonical types
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
                    
                    # Check for mismatch - especially looking for Assisted Living Home
                    if 'Assisted Living Home' in canonical_types and listing['current_wp'] == 'Assisted Living Community':
                        print(f"    🚨 FOUND MISMATCH! This should be 'Assisted Living Home'!")
                        
                        # Generate correct WordPress type field
                        correct_type_field = generate_wp_type_field(canonical_types)
                        
                        corrections_needed.append({
                            'Name': listing['name'],
                            'type': correct_type_field,
                            'normalized_types': should_be_types,
                            'senior_place_types': ', '.join(community_types),
                            'current_wp_types': listing['current_wp'],
                            'test_reason': listing['reason'],
                            'url': listing['url']
                        })
                    elif should_be_types != listing['current_wp']:
                        print(f"    🚨 OTHER MISMATCH!")
                        print(f"      Current: {listing['current_wp']}")
                        print(f"      Should be: {should_be_types}")
                        
                        correct_type_field = generate_wp_type_field(canonical_types)
                        
                        corrections_needed.append({
                            'Name': listing['name'],
                            'type': correct_type_field,
                            'normalized_types': should_be_types,
                            'senior_place_types': ', '.join(community_types),
                            'current_wp_types': listing['current_wp'],
                            'test_reason': listing['reason'],
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
        print(f"\n🎯 POTENTIAL HOMES TEST RESULTS:")
        print(f"  Total tested: {len(POTENTIAL_HOMES)}")
        print(f"  Mismatches found: {len(corrections_needed)}")
        print()
        
        if corrections_needed:
            print(f"🏠 HOMES MISCLASSIFIED AS COMMUNITIES:")
            for i, corr in enumerate(corrections_needed):
                print(f"  {i+1}. {corr['Name']}")
                print(f"     Senior Place: {corr['senior_place_types']}")
                print(f"     Current WP: {corr['current_wp_types']}")
                print(f"     Should be: {corr['normalized_types']}")
                print(f"     Test reason: {corr['test_reason']}")
                print()
            
            # Save corrections
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            corrections_file = f"organized_csvs/HOMES_VS_COMMUNITIES_CORRECTIONS_{timestamp}.csv"
            with open(corrections_file, 'w', newline='', encoding='utf-8') as f:
                if corrections_needed:
                    writer = csv.DictWriter(f, fieldnames=corrections_needed[0].keys())
                    writer.writeheader()
                    writer.writerows(corrections_needed)
            
            print(f"💾 Corrections saved: {corrections_file}")
            print(f"🚀 Import this file to fix homes misclassified as communities!")
        else:
            print(f"✅ NO MISMATCHES FOUND - All tested listings are correctly mapped!")
            print(f"   Either they're actually large facilities, or the mapping is working correctly.")

def main():
    print("🚀 Testing potential homes that might be misclassified as communities...")
    print()
    
    asyncio.run(test_potential_homes())

if __name__ == "__main__":
    main()
