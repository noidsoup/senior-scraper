#!/usr/bin/env python3
"""
Analyze the search results page issue provided by the user.

Looking at the search results, I can see:
- Multiple listings with names like "American Ridge Senior Living", "Brookdale Central Paradise Valley"
- These sound like LARGE FACILITIES/COMMUNITIES, not small homes
- But they're ALL showing as "Assisted Living Home" on the frontend
- This is the REVERSE of what the user initially described

The user said: "assisted-living homes are being shown as assisted living communities"
But the search page shows: FACILITIES being shown as "Assisted Living Home"

This suggests the real issue might be that LARGE FACILITIES are incorrectly 
classified as "Assisted Living Home" when they should be "Assisted Living Community".
"""

def analyze_search_results():
    """Analyze the search results the user provided"""
    
    print("🔍 ANALYZING USER'S SEARCH RESULTS PAGE")
    print("=" * 50)
    
    # Extract the listings from the search results
    search_results_listings = [
        {"name": "American Ridge Senior Living", "type_shown": "Assisted Living Home", "analysis": "Sounds like a large facility/community"},
        {"name": "Desert Vista Assisted Living", "type_shown": "Assisted Living Home", "analysis": "Could be either"},
        {"name": "Amber Hills Assisted Living", "type_shown": "Assisted Living Home", "analysis": "Could be either"},
        {"name": "Brookdale Central Paradise Valley", "type_shown": "Assisted Living Home", "analysis": "Brookdale is a major chain - definitely a large facility"},
        {"name": "Brookdale Desert Ridge", "type_shown": "Assisted Living Home", "analysis": "Brookdale is a major chain - definitely a large facility"},
        {"name": "Bridgewater Assisted Living Midtown", "type_shown": "Assisted Living Home", "analysis": "Sounds like a large facility"},
        {"name": "Arizona State Veteran Home-Phx", "type_shown": "Assisted Living Home", "analysis": "State facility - definitely large"},
    ]
    
    print("📋 SEARCH RESULTS ANALYSIS:")
    print()
    
    likely_misclassified = []
    correctly_classified = []
    
    for listing in search_results_listings:
        print(f"• {listing['name']}")
        print(f"  Shows as: {listing['type_shown']}")
        print(f"  Analysis: {listing['analysis']}")
        
        # Identify likely misclassifications
        if any(indicator in listing['analysis'].lower() for indicator in ['large facility', 'major chain', 'state facility', 'definitely']):
            likely_misclassified.append(listing)
            print(f"  ⚠️  LIKELY MISCLASSIFIED: Should probably be 'Assisted Living Community'")
        else:
            correctly_classified.append(listing)
            print(f"  ✅ Could be correct")
        print()
    
    print("🎯 KEY FINDINGS:")
    print(f"  • {len(likely_misclassified)} listings likely misclassified as 'Home' when they should be 'Community'")
    print(f"  • {len(correctly_classified)} listings appear correctly classified")
    print()
    
    print("🔍 LIKELY MISCLASSIFIED LISTINGS:")
    for listing in likely_misclassified:
        print(f"  - {listing['name']} (reason: {listing['analysis']})")
    
    print()
    print("💡 THE REAL ISSUE:")
    print("  The user's search results show LARGE FACILITIES incorrectly labeled as 'Home'")
    print("  This is the OPPOSITE of what they initially described in the conversation.")
    print("  These facilities should be classified as 'Assisted Living Community', not 'Home'.")
    
    print()
    print("🚀 SOLUTION:")
    print("  1. These large facilities are likely misclassified in Senior Place as 'Assisted Living Home'")
    print("  2. They should be 'Assisted Living Facility' on Senior Place")
    print("  3. Which would then correctly map to 'Assisted Living Community' via canonical mapping")
    print("  4. Need to check what Senior Place actually shows for these specific listings")
    
    print()
    print("📝 NEXT STEPS:")
    print("  • Check Senior Place for 'Brookdale Central Paradise Valley' and other large facilities")
    print("  • Verify if they're incorrectly classified as 'Assisted Living Home' on Senior Place")
    print("  • Create corrections to reclassify large facilities properly")

def main():
    analyze_search_results()

if __name__ == "__main__":
    main()
