#!/usr/bin/env python3
"""
Check WordPress REST API to verify content was imported into the 27 updated listings
"""

import requests
import pandas as pd
import re
from urllib.parse import urljoin

def check_wp_content():
    """Check WordPress API for content in the updated listings"""
    
    # WordPress site configuration
    wp_site_url = "https://aplaceforseniorscms.kinsta.cloud"
    
    # Read the updated records
    updated_df = pd.read_csv('organized_csvs/UPDATE_ONLY_MERGED_RECORDS.csv')
    
    print(f"🔍 Checking {len(updated_df)} updated listings for content...")
    print(f"WordPress Site: {wp_site_url}")
    print("=" * 60)
    
    results = []
    success_count = 0
    error_count = 0
    
    for i, row in updated_df.iterrows():
        post_id = int(row['ID'])
        title = row['Title']
        expected_content = str(row['Content']) if pd.notna(row['Content']) else ""
        has_expected_content = len(expected_content.strip()) > 50
        
        print(f"\\n[{i+1}/{len(updated_df)}] Checking ID {post_id}: {title[:40]}...")
        
        try:
            # Try different API endpoints
            endpoints_to_try = [
                f"{wp_site_url}/wp-json/wp/v2/listing/{post_id}",  # Custom post type
                f"{wp_site_url}/wp-json/wp/v2/posts/{post_id}",    # Regular posts
            ]
            
            post_data = None
            used_endpoint = None
            
            for endpoint in endpoints_to_try:
                try:
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        post_data = response.json()
                        used_endpoint = endpoint
                        break
                    elif response.status_code == 404:
                        continue  # Try next endpoint
                    else:
                        print(f"   ❌ HTTP {response.status_code} from {endpoint}")
                except requests.exceptions.RequestException as e:
                    print(f"   ⚠️  Connection error: {str(e)[:50]}...")
                    continue
            
            if post_data:
                # Extract content
                content_obj = post_data.get('content', {})
                if isinstance(content_obj, dict):
                    actual_content = content_obj.get('rendered', '')
                else:
                    actual_content = str(content_obj) if content_obj else ''
                
                # Clean HTML for analysis
                clean_content = re.sub(r'<[^>]+>', '', actual_content).strip()
                content_length = len(clean_content)
                
                # Check if content exists
                has_content = content_length > 50
                
                # Determine status
                if has_content:
                    if has_expected_content:
                        status = "✅ Content Updated"
                        success_count += 1
                    else:
                        status = "✅ Has Content (Unexpected)"
                        success_count += 1
                else:
                    if has_expected_content:
                        status = "❌ Missing Expected Content"
                        error_count += 1
                    else:
                        status = "⚪ No Content (Expected)"
                
                print(f"   {status}")
                print(f"   📊 Content length: {content_length} characters")
                if content_length > 0:
                    preview = clean_content[:100] + '...' if len(clean_content) > 100 else clean_content
                    print(f"   📝 Preview: {preview}")
                
                results.append({
                    'ID': post_id,
                    'Title': title,
                    'Status': status,
                    'Content_Length': content_length,
                    'Has_Content': 'Yes' if has_content else 'No',
                    'Expected_Content': 'Yes' if has_expected_content else 'No',
                    'API_Endpoint': used_endpoint,
                    'Content_Preview': clean_content[:200] if clean_content else ''
                })
                
            else:
                print(f"   ❌ Could not access post via API")
                error_count += 1
                results.append({
                    'ID': post_id,
                    'Title': title,
                    'Status': '❌ API Access Failed',
                    'Content_Length': 0,
                    'Has_Content': 'Unknown',
                    'Expected_Content': 'Yes' if has_expected_content else 'No',
                    'API_Endpoint': 'None',
                    'Content_Preview': ''
                })
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
            error_count += 1
            results.append({
                'ID': post_id,
                'Title': title,
                'Status': f'❌ Error: {str(e)[:30]}...',
                'Content_Length': 0,
                'Has_Content': 'Unknown',
                'Expected_Content': 'Yes' if has_expected_content else 'No',
                'API_Endpoint': 'Error',
                'Content_Preview': ''
            })
    
    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv('organized_csvs/WP_CONTENT_CHECK_RESULTS.csv', index=False)
    
    # Summary
    print(f"\\n" + "=" * 60)
    print(f"📊 CONTENT CHECK SUMMARY")
    print(f"=" * 60)
    print(f"Total listings checked: {len(results_df)}")
    print(f"✅ Successfully have content: {success_count}")
    print(f"❌ Errors or missing content: {error_count}")
    
    success_rate = (success_count / len(results_df)) * 100 if len(results_df) > 0 else 0
    print(f"📈 Success rate: {success_rate:.1f}%")
    
    print(f"\\n📁 Detailed results saved to: WP_CONTENT_CHECK_RESULTS.csv")
    
    # Show top successes
    successful = results_df[results_df['Has_Content'] == 'Yes']
    if len(successful) > 0:
        print(f"\\n🎉 SUCCESS EXAMPLES:")
        for _, row in successful.head(3).iterrows():
            print(f"   ID {row['ID']}: {row['Title'][:40]}... ({row['Content_Length']} chars)")
    
    # Show any failures
    failed = results_df[results_df['Has_Content'] == 'No']
    if len(failed) > 0:
        print(f"\\n⚠️  NEED ATTENTION:")
        for _, row in failed.head(3).iterrows():
            print(f"   ID {row['ID']}: {row['Title'][:40]}... - {row['Status']}")
    
    return results_df

if __name__ == "__main__":
    check_wp_content()
