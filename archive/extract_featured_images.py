#!/usr/bin/env python3

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag
import time
import re
from urllib.parse import urljoin, urlparse
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_seniorly_url(url):
    """Check if URL is from seniorly.com"""
    if pd.isna(url) or not isinstance(url, str):
        return False
    return 'seniorly.com' in url.lower()

def is_placeholder_image(img_src):
    """Check if image is a placeholder that should be skipped"""
    if not img_src:
        return True
    
    # Common placeholder patterns
    placeholder_patterns = [
        'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP',  # 1x1 transparent gif
        'placeholder',
        'no-image',
        'default',
        'missing',
        'blank',
        'empty'
    ]
    
    img_src_lower = img_src.lower()
    return any(pattern in img_src_lower for pattern in placeholder_patterns)

def extract_first_gallery_image(url):
    """Extract the first real image URL from a Seniorly page gallery"""
    try:
        logger.info(f"Scraping: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the gallery div
        gallery_div = soup.find('div', id='gallery')
        if not gallery_div or not isinstance(gallery_div, Tag):
            logger.warning(f"No gallery found for {url}")
            return None
        
        # Find all images in the gallery and look for the first real one
        all_imgs = gallery_div.find_all('img')
        if not all_imgs:
            logger.warning(f"No images found in gallery for {url}")
            return None
        
        for img in all_imgs:
            # Ensure img is a Tag object
            if not isinstance(img, Tag):
                continue
                
            # Get the src attribute
            img_src = img.get('src')
            if not img_src:
                continue
            
            # Handle case where src might be a list
            if isinstance(img_src, list):
                if len(img_src) > 0:
                    img_src = img_src[0]
                else:
                    continue
            
            # Ensure img_src is a string
            if not isinstance(img_src, str):
                continue
            
            # Skip data URLs and placeholders
            if img_src.startswith('data:'):
                logger.debug(f"Skipping data URL for {url}")
                continue
                
            if is_placeholder_image(img_src):
                logger.debug(f"Skipping placeholder image: {img_src}")
                continue
            
            # Handle relative URLs
            if img_src.startswith('//'):
                img_src = 'https:' + img_src
            elif img_src.startswith('/'):
                img_src = urljoin(url, img_src)
            
            # Skip street view images - prefer actual property photos
            if 'maps.googleapis.com' in img_src or 'streetview' in img_src.lower():
                logger.debug(f"Skipping street view image: {img_src}")
                continue
            
            # Check if this looks like a real image URL
            if img_src.startswith('https://') and any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                logger.info(f"Found featured image: {img_src}")
                return img_src
        
        logger.warning(f"No real images found in gallery for {url}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing {url}: {e}")
        return None

def process_csv(input_csv, output_csv):
    """Process the CSV file and extract featured images from Seniorly URLs"""
    
    # Read the CSV
    logger.info(f"Reading CSV: {input_csv}")
    df = pd.read_csv(input_csv)
    
    logger.info(f"Total rows: {len(df)}")
    
    # Check both website columns
    website_columns = []
    for col in df.columns:
        if 'website' in col.lower():
            website_columns.append(col)
    
    if not website_columns:
        logger.error("No website column found in CSV")
        return
    
    logger.info(f"Found website columns: {website_columns}")
    
    # Count Seniorly URLs for logging
    seniorly_count = 0
    for col in website_columns:
        seniorly_count += df[col].apply(is_seniorly_url).sum()
    
    logger.info(f"Found {seniorly_count} Seniorly URLs total")
    
    if seniorly_count == 0:
        logger.warning("No Seniorly URLs found")
        return
    
    # Ensure Featured column exists
    if 'Featured' not in df.columns:
        df['Featured'] = None
    
    # Process each row
    processed_count = 0
    skipped_count = 0
    for idx, row in df.iterrows():
        # Check if any website column has a Seniorly URL
        seniorly_url = None
        for col in website_columns:
            if is_seniorly_url(row[col]):
                seniorly_url = row[col]
                break
        
        if seniorly_url is not None:
            # Skip if already scraped (check if Featured contains cloudfront URL)
            current_featured = str(row.get('Featured', ''))
            if current_featured and current_featured != 'nan' and 'cloudfront.net' in current_featured:
                skipped_count += 1
                if skipped_count % 50 == 0:
                    logger.info(f"Skipped {skipped_count} already scraped Seniorly URLs")
                continue
                
            processed_count += 1
            logger.info(f"Processing Seniorly URL {processed_count}/{seniorly_count - skipped_count}: {seniorly_url}")
            
            featured_img = extract_first_gallery_image(seniorly_url)
            df.at[idx, 'Featured'] = featured_img
            
            # Add shorter delay to be respectful but faster
            time.sleep(0.5)
            
            # Save progress periodically
            if processed_count % 10 == 0:
                df.to_csv(output_csv, index=False)
                logger.info(f"Progress saved: {processed_count}/{seniorly_count} completed")
    
    # Save to new CSV
    logger.info(f"Saving results to: {output_csv}")
    df.to_csv(output_csv, index=False)
    
    # Print summary
    successful_extractions = df['Featured'].notna().sum()
    logger.info(f"Successfully extracted featured images for {successful_extractions}/{seniorly_count} Seniorly URLs")
    
    return df

if __name__ == "__main__":
    input_file = "latest.csv"
    output_file = "listings_with_featured_images.csv"
    
    logger.info("Starting featured image extraction process")
    
    try:
        result_df = process_csv(input_file, output_file)
        logger.info("Process completed successfully")
        
        if result_df is not None:
            print(f"\nSummary:")
            print(f"Total Seniorly URLs processed: {len(result_df)}")
            print(f"Featured images extracted: {result_df['Featured'].notna().sum()}")
            print(f"Failed extractions: {result_df['Featured'].isna().sum()}")
            print(f"Results saved to: {output_file}")
            
    except Exception as e:
        logger.error(f"Process failed: {e}")
        raise 