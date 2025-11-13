#!/usr/bin/env python3
"""
Test script to verify that the 27 updated listings now have content
Uses WordPress REST API to check the imported content
"""

import requests
import pandas as pd
import json

def test_content_import():
    """Test if the 27 updated listings now have content"""
    
    # Read the list of updated records
    updated_df = pd.read_csv('organized_csvs/UPDATE_ONLY_MERGED_RECORDS.csv')
    
    print(f"Testing content import for {len(updated_df)} updated listings...")
    print("Checking WordPress REST API for content...")
    
    # WordPress site URL - you'll need to update this
    wp_site_url = "https://aplaceforseniorscms.kinsta.cloud"  # Update this to your actual site URL
    api_endpoint = f"{wp_site_url}/wp-json/wp/v2/listing"  # Assuming 'listing' is your post type
    
    results = []
    
    for _, row in updated_df.iterrows():
        post_id = int(row['ID'])
        title = row['Title']
        expected_content = str(row['Content']) if pd.notna(row['Content']) else ""
        
        try:
            # Make API request to get the specific post
            response = requests.get(f"{api_endpoint}/{post_id}")
            
            if response.status_code == 200:
                post_data = response.json()
                actual_content = post_data.get('content', {}).get('rendered', '')
                
                # Clean up content for comparison (remove HTML tags for length check)
                import re
                clean_content = re.sub(r'<[^>]+>', '', actual_content).strip()
                
                has_content = len(clean_content) > 50  # Consider "has content" if more than 50 chars
                content_length = len(clean_content)
                
                results.append({
                    'ID': post_id,
                    'Title': title[:50] + '...' if len(title) > 50 else title,
                    'Has_Content': 'Yes' if has_content else 'No',
                    'Content_Length': content_length,
                    'Status': 'Updated' if has_content else 'No Content'
                })
                
                print(f"✓ ID {post_id}: {title[:30]}... | Content: {content_length} chars")
                
            else:
                results.append({
                    'ID': post_id,
                    'Title': title[:50] + '...' if len(title) > 50 else title,
                    'Has_Content': 'Unknown',
                    'Content_Length': 0,
                    'Status': f'API Error {response.status_code}'
                })
                print(f"✗ ID {post_id}: API Error {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            results.append({
                'ID': post_id,
                'Title': title[:50] + '...' if len(title) > 50 else title,
                'Has_Content': 'Unknown',
                'Content_Length': 0,
                'Status': f'Connection Error'
            })
            print(f"✗ ID {post_id}: Connection Error - {str(e)[:50]}...")
    
    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv('organized_csvs/CONTENT_IMPORT_TEST_RESULTS.csv', index=False)
    
    # Summary
    successful_updates = len(results_df[results_df['Has_Content'] == 'Yes'])
    no_content = len(results_df[results_df['Has_Content'] == 'No'])
    errors = len(results_df[results_df['Has_Content'] == 'Unknown'])
    
    print(f"\\n=== CONTENT IMPORT TEST RESULTS ===")
    print(f"Total listings tested: {len(results_df)}")
    print(f"✅ Successfully have content: {successful_updates}")
    print(f"❌ No content detected: {no_content}")
    print(f"🔌 API/Connection errors: {errors}")
    print(f"\\nDetailed results saved to: CONTENT_IMPORT_TEST_RESULTS.csv")
    
    if successful_updates > 0:
        print(f"\\n🎉 SUCCESS! {successful_updates} listings now have content from the import!")
    
    return results_df

def test_content_without_api():
    """Alternative test without API - just show what should have been imported"""
    
    updated_df = pd.read_csv('organized_csvs/UPDATE_ONLY_MERGED_RECORDS.csv')
    
    print(f"\\n=== CONTENT IMPORT EXPECTATION TEST ===")
    print(f"These {len(updated_df)} listings should now have enhanced content:")
    
    content_count = 0
    for _, row in updated_df.iterrows():
        post_id = int(row['ID'])
        title = row['Title']
        has_content = pd.notna(row['Content']) and str(row['Content']).strip()
        content_preview = str(row['Content'])[:100] + '...' if has_content else 'No content'
        
        if has_content:
            content_count += 1
            
        status = "📝 Content" if has_content else "📋 Basic"
        print(f"{status} ID {post_id}: {title[:40]}...")
        if has_content:
            print(f"   Preview: {content_preview}")
    
    print(f"\\nExpected results:")
    print(f"📝 {content_count} listings should have rich content")
    print(f"📋 {len(updated_df) - content_count} listings had basic info only")
    
    print(f"\\n💡 To verify the import worked:")
    print(f"1. Check a few listings in WordPress admin")
    print(f"2. Look for content in the post content field")
    print(f"3. Example IDs to check: {', '.join(map(str, updated_df['ID'].head(5).tolist()))}")

if __name__ == "__main__":
    print("Choose test method:")
    print("1. API Test (requires WordPress REST API access)")
    print("2. Expectation Test (shows what should have been imported)")
    
    choice = input("Enter 1 or 2 (or press Enter for option 2): ").strip()
    
    if choice == "1":
        test_content_import()
    else:
        test_content_without_api()
