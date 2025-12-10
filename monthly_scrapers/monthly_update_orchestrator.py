#!/usr/bin/env python3
"""
Monthly Update Orchestrator
Runs every 30 days to:
1. Discover NEW listings from Senior Place and Seniorly
2. Update EXISTING listings with latest pricing, care types, descriptions
3. Generate WordPress-ready import files
4. Send summary report

Usage:
    python3 monthly_update_orchestrator.py --full-update
    python3 monthly_update_orchestrator.py --new-only
    python3 monthly_update_orchestrator.py --updates-only
"""

import asyncio
import csv
import json
import argparse
import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import requests
from collections import defaultdict
import re

# Import core module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core import (
    map_care_types_to_canonical,
    SUPPORTED_STATES,
    SeniorScraperError,
    AuthenticationError,
    RateLimitError,
    get_settings,
)

# Import parallel enricher
from scrapers.parallel_enricher import ParallelEnricher

# Import existing scrapers
import sys
sys.path.append(str(Path(__file__).parent / "scrapers_active"))


class MonthlyUpdateOrchestrator:
    def __init__(self, wp_url: str, wp_username: str, wp_password: str, 
                 sp_username: str, sp_password: str):
        self.wp_url = wp_url.rstrip('/')
        self.wp_username = wp_username
        self.wp_password = wp_password
        self.sp_username = sp_username
        self.sp_password = sp_password
        # Optional per-state pagination cap for quick tests (0 = no cap)
        try:
            self.max_pages_per_state = int(os.getenv("MAX_PAGES_PER_STATE", "0"))
        except Exception:
            self.max_pages_per_state = 0
        
        # Stats tracking
        self.stats = {
            'new_listings_found': 0,
            'listings_updated': 0,
            'pricing_updates': 0,
            'care_type_updates': 0,
            'description_updates': 0,
            'failed_scrapes': 0,
            'total_processed': 0
        }
        
        # Storage
        self.current_wp_listings = {}  # URL -> listing data
        self.new_listings = []
        self.updated_listings = []
        
        # Timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.cache_dir = Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.wp_cache_file = self.cache_dir / "wp_listings_cache.json"
        self.wp_cache_ttl = int(os.getenv("WP_CACHE_TTL_SECONDS", "3600"))
        self.disable_wp_cache = os.getenv("WP_CACHE_DISABLE", "0") == "1"

    # ---------- Checkpoint helpers ----------
    def _checkpoint_default_path(self) -> Path:
        return Path("monthly_updates") / self.timestamp / "resume_checkpoint.json"

    def _load_checkpoint(self, checkpoint_path: Path) -> Optional[Dict]:
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.log(f"Checkpoint not found: {checkpoint_path}", "WARNING")
            return None
        except Exception as e:
            self.log(f"Failed to load checkpoint {checkpoint_path}: {e}", "ERROR")
            return None

    def _save_checkpoint(self, checkpoint_path: Path, data: Dict):
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.log(f"Checkpoint saved to {checkpoint_path}", "INFO")
        
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "PROGRESS": "🔄"
        }.get(level, "•")
        print(f"[{timestamp}] {prefix} {message}")

    def _normalize_care_types(self, care_types):
        """Normalize care types for comparison using core module"""
        if not care_types:
            return []

        # Handle both string and list inputs
        if isinstance(care_types, str):
            care_types = [ct.strip() for ct in care_types.split(',') if ct.strip()]

        # Use core module for mapping
        return map_care_types_to_canonical(care_types)

    def _normalize_address_components(
        self,
        address: str,
        city: str = "",
        state: str = "",
        zip_code: str = ""
    ) -> Tuple[str, str, str, str, str]:
        """
        Normalize/parse address fields that often arrive as newline-delimited
        blobs from Senior Place. Returns (street, city, state, zip, rebuilt_full).
        """
        street = (address or "").replace("\r", "\n").strip()
        city = (city or "").strip()
        state = (state or "").strip()
        zip_code = (zip_code or "").strip()

        # Handle malformed data where city field contains state/zip + junk
        if city and not state and not zip_code:
            city_lower = city.lower()
            if "directions" in city_lower:
                # Extract state/zip from city field like "AZ 85710\nDirections"
                city_clean = city.replace("\nDirections", "").replace("Directions", "").strip()
                parts = city_clean.split()
                if len(parts) >= 2 and re.match(r"^[A-Z]{2}$", parts[0]) and re.match(r"^\d{5}$", parts[1]):
                    state = parts[0]
                    zip_code = parts[1]
                    city = ""  # Clear malformed city
            else:
                # Handle case where city field contains just "STATE ZIP" like "CA 90210"
                parts = city.split()
                if len(parts) >= 2 and re.match(r"^[A-Z]{2}$", parts[0]) and re.match(r"^\d{5}$", parts[1]):
                    state = parts[0]
                    zip_code = parts[1]
                    city = ""  # Clear malformed city

        # Split on newlines and filter out junk like "Directions" or phone numbers
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", street) if ln.strip()]
        cleaned_lines = []
        for ln in lines:
            lower = ln.lower()
            if "directions" in lower:
                continue
            if re.match(r"^\(\d{3}\)", ln):  # phone numbers
                continue
            if "updated" in lower:
                continue
            cleaned_lines.append(ln)
        lines = cleaned_lines

        if lines:
            street = lines[0]
        if len(lines) >= 2 and not city:
            # Only use line 2 as city when it is not a state line
            if not re.match(r"^[A-Z]{2}\b", lines[1]):
                city = lines[1]
        if len(lines) >= 3 and not state:
            state_line = lines[2].replace("Directions", "").strip()
            m = re.match(r"([A-Z]{2})\s*(\d{5})?", state_line)
            if m:
                state = state or m.group(1)
                if not zip_code and m.group(2):
                    zip_code = m.group(2)

        # Fallback: try comma-separated parsing if still missing parts
        if (not city or not state) and "," in address:
            parts = [p.strip() for p in address.split(",") if p.strip()]
            if len(parts) >= 2 and not city:
                city = parts[1]
            if len(parts) >= 3 and not state:
                state_zip_parts = parts[2].split()
                if state_zip_parts:
                    state = state or state_zip_parts[0]
                    if not zip_code and len(state_zip_parts) > 1:
                        zip_code = state_zip_parts[-1]

        state_zip = " ".join([p for p in [state, zip_code] if p]).strip()
        rebuilt_full = ", ".join([p for p in [street, city, state_zip] if p])

        return street, city, state, zip_code, rebuilt_full
        
    def fetch_current_wordpress_listings(self) -> Dict[str, Dict]:
        """
        Fetch all current listings from WordPress via REST API
        Returns dict of {source_url: listing_data}
        """
        # Serve from cache when fresh
        if not self.disable_wp_cache and self.wp_cache_file.exists():
            try:
                with open(self.wp_cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                ts = cached.get("timestamp", 0)
                age = time.time() - ts
                if age <= self.wp_cache_ttl and cached.get("wp_url") == self.wp_url:
                    listings_by_url = cached.get("data", {})
                    self.log(f"Using cached WordPress listings (age {int(age)}s, {len(listings_by_url)} URLs)", "SUCCESS")
                    return listings_by_url
                else:
                    self.log("Cache expired or WP URL changed; fetching fresh", "INFO")
            except Exception as e:
                self.log(f"Cache read failed, fetching fresh: {e}", "WARNING")

        self.log("Fetching current WordPress listings via REST API...")
        
        try:
            # WordPress REST API for custom post type 'listing'
            api_url = f"{self.wp_url}/wp-json/wp/v2/listing"
            
            all_listings = []
            page = 1
            per_page = 100
            
            while True:
                params = {
                    'per_page': per_page,
                    'page': page,
                    '_fields': 'id,title,acf,meta'  # Get ACF fields and meta
                }
                
                response = requests.get(
                    api_url,
                    params=params,
                    auth=(self.wp_username, self.wp_password),
                    timeout=30
                )
                
                if response.status_code == 400:
                    # No more pages
                    break
                    
                response.raise_for_status()
                listings_batch = response.json()
                
                if not listings_batch:
                    break
                    
                all_listings.extend(listings_batch)
                
                self.log(f"Fetched page {page}: {len(listings_batch)} listings", "PROGRESS")
                page += 1
                
            # Build lookup dict by source URL
            listings_by_url = {}
            for listing in all_listings:
                # Get Senior Place URL from ACF or meta
                sp_url = None
                seniorly_url = None
                
                if 'acf' in listing:
                    sp_url = listing['acf'].get('senior_place_url') or listing['acf'].get('url')
                    seniorly_url = listing['acf'].get('seniorly_url')
                    
                if 'meta' in listing:
                    sp_url = sp_url or listing['meta'].get('_senior_place_url', [''])[0]
                    seniorly_url = seniorly_url or listing['meta'].get('_seniorly_url', [''])[0]
                
                # Store by both URLs
                if sp_url and 'seniorplace.com' in sp_url:
                    listings_by_url[sp_url] = listing
                if seniorly_url and 'seniorly.com' in seniorly_url:
                    listings_by_url[seniorly_url] = listing
            
            self.log(f"Loaded {len(all_listings)} listings from WordPress", "SUCCESS")

            # Write cache
            try:
                with open(self.wp_cache_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "timestamp": time.time(),
                        "wp_url": self.wp_url,
                        "data": listings_by_url
                    }, f)
            except Exception as e:
                self.log(f"Failed to write cache: {e}", "WARNING")

            return listings_by_url
            
        except Exception as e:
            self.log(f"Error fetching WordPress listings: {e}", "ERROR")
            return {}
    
    async def scrape_seniorplace_state(self, state_code: str, state_name: str) -> List[Dict]:
        """
        Scrape all listings for a specific state from Senior Place
        Returns list of listing dicts with: title, address, url, care_types, featured_image
        """
        from playwright.async_api import async_playwright
        
        self.log(f"Scraping Senior Place for {state_name} ({state_code})...")
        
        all_listings = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Login
                self.log("Logging into Senior Place...", "PROGRESS")
                await page.goto(LOGIN_URL)
                await page.fill('input[name="email"]', self.sp_username)
                await page.fill('input[name="password"]', self.sp_password)
                await page.click('button[type="submit"]')
                await page.wait_for_selector('text=Communities', timeout=15000)
                self.log("Successfully logged in", "SUCCESS")
                
                # Navigate to communities page (they're all there, we filter by state)
                await page.goto("https://app.seniorplace.com/communities", wait_until="networkidle")
                
                # Wait for results to load
                await page.wait_for_timeout(3000)
                
                # Senior Place shows ALL listings paginated, we filter by state
                # Detect pagination from "Next" button
                total_pages = 1
                try:
                    # Check if there's a Next button (it's a button, not a link!)
                    next_button = await page.query_selector('button:has-text("Next")')
                    if next_button:
                        # There are multiple pages, we'll paginate until no Next button
                        total_pages = 999  # Will break when no more Next button
                except:
                    total_pages = 1
                
                self.log(f"Starting pagination (will process until no more pages)", "INFO")
                
                # Scrape each page
                page_num = 1
                while True:
                    # Extract listings from current page using WORKING selectors
                    # Wait for cards to load
                    try:
                        await page.wait_for_selector('div.flex.space-x-6', timeout=10000)
                    except:
                        self.log(f"No listings found on page {page_num}", "WARNING")
                        continue
                    
                    cards = await page.query_selector_all('div.flex.space-x-6')
                    listings = []
                    
                    for card in cards:
                        try:
                            # Extract title and URL
                            name_el = await card.query_selector("h3 a")
                            if not name_el:
                                continue
                            
                            title = (await name_el.inner_text()).strip()
                            href = await name_el.get_attribute("href")
                            url = f"https://app.seniorplace.com{href}"
                            
                            # Extract image
                            img_el = await card.query_selector("img")
                            featured_image = ""
                            if img_el:
                                img_src = await img_el.get_attribute("src")
                                if img_src and img_src.startswith("/api/files/"):
                                    featured_image = f"https://placement-crm-cdn.s3.us-west-2.amazonaws.com{img_src}"
                                elif img_src:
                                    featured_image = img_src
                            
                            # Extract address/location from card with proper parsing
                            address_el = await card.query_selector("div.text-sm.text-gray-500")
                            address = ""
                            city = ""
                            state = ""
                            zip_code = ""

                            if address_el:
                                raw_address = (await address_el.inner_text()).strip()

                                # Senior Place cards typically show: "Street Address\nCity, ST ZIP\nDirections"
                                lines = [ln.strip() for ln in raw_address.split('\n') if ln.strip() and ln != 'Directions']

                                if len(lines) >= 2:
                                    address = lines[0]  # Street address
                                    location_line = lines[1]  # "City, ST ZIP"

                                    # Parse location line: "City, ST ZIP"
                                    if ',' in location_line:
                                        parts = [p.strip() for p in location_line.split(',')]
                                        if len(parts) >= 2:
                                            city = parts[0]
                                            state_zip_part = parts[1]

                                            # Split state and zip
                                            state_zip_parts = state_zip_part.split()
                                            if len(state_zip_parts) >= 1:
                                                state = state_zip_parts[0]
                                            if len(state_zip_parts) >= 2:
                                                zip_code = state_zip_parts[1]
                                    else:
                                        # Fallback for different format
                                        parts = location_line.split()
                                        if len(parts) >= 3:
                                            city = ' '.join(parts[:-2])
                                            state = parts[-2]
                                            zip_code = parts[-1]
                            
                            # Filter to only include listings from this state
                            # Check individual fields to avoid substring collisions (e.g., "Blazer Ave" contains "AZ")
                            location_text = f"{address} {city} {state}".lower()
                            if state_code.lower() in location_text or state_name.lower() in location_text:
                                listings.append({
                                    'title': title,
                                    'url': url,
                                    'featured_image': featured_image,
                                    'address': address,
                                    'city': city,
                                    'state': state,
                                    'zip': zip_code
                                })
                        except Exception as e:
                            continue
                    
                    all_listings.extend(listings)
                    self.log(f"Page {page_num}: Found {len(listings)} {state_code} listings on this page", "PROGRESS")
                    
                    # Check for Next button (it's a button, not a link!)
                    next_button = await page.query_selector('button:has-text("Next")')
                    if not next_button:
                        self.log(f"No more pages, stopping at page {page_num}", "INFO")
                        break
                    
                    # Click Next
                    await next_button.click()
                    await page.wait_for_timeout(2000)
                    page_num += 1
                    
                    # Per-state cap for quick tests
                    if self.max_pages_per_state and page_num > self.max_pages_per_state:
                        self.log(f"Reached per-state page cap ({self.max_pages_per_state}) for {state_code}", "WARNING")
                        break
                    
                    # Safety limit
                    if page_num > 500:
                        self.log("Reached safety limit of 500 pages", "WARNING")
                        break
                
            finally:
                await browser.close()
        
        self.log(f"Scraped {len(all_listings)} total listings from {state_name}", "SUCCESS")
        return all_listings
    
    async def enrich_listing_details(self, listings: List[Dict]) -> List[Dict]:
        """
        Enrich basic listings with detailed info: pricing, care types, description
        """
        from playwright.async_api import async_playwright
        
        self.log(f"Enriching {len(listings)} listings with detailed data...")
        
        enriched = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # Re-use login session
            page = await context.new_page()
            await page.goto("https://app.seniorplace.com/login")
            await page.fill('input[name="email"]', self.sp_username)
            await page.fill('input[name="password"]', self.sp_password)
            await page.click('button[type="submit"]')
            await page.wait_for_selector('text=Communities', timeout=15000)
            await page.close()
            
            # Process each listing
            for i, listing in enumerate(listings, 1):
                try:
                    page = await context.new_page()
                    
                    # Normalize base URL (strip /details or /attributes)
                    base_url = listing['url'].split('?')[0]
                    for suffix in ['/details', '/attributes']:
                        if base_url.endswith(suffix):
                            base_url = base_url[:-len(suffix)]

                    # --- Address from Details tab (form fields) ---
                    detail_data = {}
                    try:
                        details_url = f"{base_url.rstrip('/')}/details"
                        await page.goto(details_url, wait_until="networkidle", timeout=20000)
                        await page.wait_for_timeout(1200)
                        detail_data = await page.evaluate("""
                            () => {
                                const getField = (needle) => {
                                    const labels = Array.from(document.querySelectorAll('label'));
                                    for (const label of labels) {
                                        const text = (label.textContent || '').toLowerCase();
                                        if (text.includes(needle)) {
                                            const input = label.querySelector('input');
                                            const textarea = label.querySelector('textarea');
                                            const select = label.querySelector('select');
                                            if (input && input.value) return input.value.trim();
                                            if (textarea && textarea.value) return textarea.value.trim();
                                            if (select) {
                                                const opt = select.options[select.selectedIndex];
                                                if (opt && opt.value) return opt.value.trim();
                                                if (opt && opt.textContent) return opt.textContent.trim();
                                            }
                                        }
                                    }
                                    return '';
                                };
                                return {
                                    address: getField('address'),
                                    city: getField('city'),
                                    state: getField('state'),
                                    zip: getField('zip')
                                };
                            }
                        """)
                    except Exception:
                        detail_data = {}

                    # Fallback visible address (cards/blocks)
                    address = detail_data.get('address', '').strip()
                    city = detail_data.get('city', '').strip()
                    state = detail_data.get('state', '').strip()
                    zip_code = detail_data.get('zip', '').strip()

                    if not address:
                        try:
                            addr_data = await page.evaluate("""
                                () => {
                                    const addressEl = document.querySelector('address');
                                    if (addressEl) {
                                        const ps = Array.from(addressEl.querySelectorAll('p'));
                                        if (ps.length >= 2) {
                                            return { address: ps[0].textContent.trim(), location: ps[1].textContent.trim() };
                                        }
                                        if (ps.length === 1) {
                                            const text = ps[0].textContent.trim();
                                            const lines = text.split('\\n').filter(l => l.trim() && !l.includes('Directions'));
                                            if (lines.length >= 2) {
                                                return { address: lines[0].trim(), location: lines[1].trim() };
                                            }
                                        }
                                    }
                                    const addrDiv = document.querySelector('div.text-sm.text-gray-500');
                                    if (addrDiv) {
                                        const text = addrDiv.textContent.trim();
                                        const lines = text.split('\\n').filter(l => {
                                            const trimmed = l.trim();
                                            return trimmed &&
                                                   !trimmed.includes('Directions') &&
                                                   !trimmed.includes('Last updated') &&
                                                   !trimmed.includes('updated on') &&
                                                   !trimmed.match(/^\\(\\d{3}\\)/) &&
                                                   trimmed.length > 5;
                                        });
                                        if (lines.length >= 2 && /\\d+/.test(lines[0])) {
                                            return { address: lines[0].trim(), location: lines[1].trim() };
                                        }
                                        if (lines.length === 1 && text.includes(',')) {
                                            const parts = text.split(',').map(p => p.trim());
                                            if (parts.length >= 2 && /\\d+/.test(parts[0])) {
                                                return { address: parts[0], location: parts.slice(1).join(', ') };
                                            }
                                        }
                                    }
                                    const candidates = document.querySelectorAll('[class*="address"], [class*="location"], .address, .location');
                                    for (const el of candidates) {
                                        const text = el.textContent.trim();
                                        if (text && (/\\d+/.test(text) || text.includes(','))) {
                                            const lines = text.split('\\n').filter(l => l.trim());
                                            if (lines.length >= 2) {
                                                return { address: lines[0].trim(), location: lines[1].trim() };
                                            }
                                        }
                                    }
                                    return { address: '', location: '' };
                                }
                            """)
                            address = addr_data.get('address', '').strip() if addr_data else ''
                            location = addr_data.get('location', '').strip() if addr_data else ''
                            if location and (not city or not state):
                                parts = location.split(',')
                                if len(parts) >= 2:
                                    city = city or parts[0].strip()
                                    state_zip = parts[1].strip().split()
                                    if len(state_zip) > 0 and not state:
                                        state = state_zip[0]
                                    if len(state_zip) > 1 and not zip_code:
                                        zip_code = state_zip[1]
                        except Exception:
                            pass

                    # Normalize/parse address pieces and store on listing
                    street, city, state, zip_code, rebuilt_full = self._normalize_address_components(
                        address or listing.get('address', ''),
                        city,
                        state,
                        zip_code
                    )
                    listing['address'] = rebuilt_full or street or listing.get('address', '')
                    listing['city'] = city
                    listing['state'] = state
                    listing['zip'] = zip_code

                    # --- Attributes page for care types / pricing / description ---
                    attrs_url = f"{base_url.rstrip('/')}/attributes"
                    await page.goto(attrs_url, wait_until="networkidle", timeout=20000)
                    await page.wait_for_timeout(1000)
                    
                    # Extract care types from Community Types section only (per HTML structure)
                    care_types = await page.evaluate("""
                        () => {
                            const types = [];

                            // Find the "Community Type(s)" section specifically
                            const sections = Array.from(document.querySelectorAll('div'));
                            let communityTypesSection = null;

                            for (const section of sections) {
                                const header = section.querySelector('.font-bold');
                                if (header && header.textContent.trim() === 'Community Type(s)') {
                                    communityTypesSection = section;
                                    break;
                                }
                            }

                            if (communityTypesSection) {
                                // Extract only from Community Types checkboxes (label.inline-flex)
                                const labels = Array.from(communityTypesSection.querySelectorAll("label.inline-flex"));
                                for (const label of labels) {
                                    const textEl = label.querySelector("div.ml-2");
                                    const input = label.querySelector('input[type="checkbox"]');

                                    if (!textEl || !input) continue;
                                    if (!input.checked) continue;

                                    const name = (textEl.textContent || "").trim();
                                    if (name) types.push(name);
                                }
                            }

                            // Fallback: if no community types section found, use original method but skip non-care sections
                            if (types.length === 0) {
                                const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                                for (const label of labels) {
                                    const textEl = label.querySelector("div.ml-2");
                                    const input = label.querySelector('input[type="checkbox"]');

                                    if (!textEl || !input) continue;
                                    if (!input.checked) continue;

                                    const name = (textEl.textContent || "").trim();
                                    // Skip non-care-type sections like Bathrooms (Shared, Private)
                                    if (name === 'Shared' || name === 'Private') continue;
                                    if (name) types.push(name);
                                }
                            }

                            return types;
                        }
                    """)
                    
                    # Extract last updated date
                    last_updated = await page.evaluate("""
                        () => {
                            // Look for "Last updated on" text
                            const elements = document.querySelectorAll('*');
                            for (const el of elements) {
                                const text = (el.textContent || '').trim();
                                if (text.includes('Last updated on')) {
                                    // Extract date from "Last updated on Jul 27, 2024"
                                    const match = text.match(/Last updated on ([A-Za-z]+ \\d{1,2}, \\d{4})/);
                                    if (match) {
                                        return match[1];
                                    }
                                }
                            }
                            return null;
                        }
                    """)

                    # Parse last_updated date if found
                    if last_updated:
                        try:
                            from datetime import datetime
                            parsed_date = datetime.strptime(last_updated, '%b %d, %Y')
                            listing['last_updated'] = parsed_date.isoformat()
                        except:
                            listing['last_updated'] = None
                    else:
                        listing['last_updated'] = None

                    # Extract pricing + description
                    pricing = await page.evaluate("""
                        () => {
                            const result = {};
                            
                            // Find form groups by label text
                            const groups = document.querySelectorAll('.form-group');
                            for (const group of groups) {
                                const labelText = group.textContent || '';
                                const input = group.querySelector('input');
                                const textarea = group.querySelector('textarea');
                                
                                if (labelText.includes('Monthly Base Price') && input) {
                                    result.monthly_base_price = input.value;
                                }
                                if (labelText.includes('High End') && input) {
                                    result.price_high_end = input.value;
                                }
                                if (labelText.includes('Second Person Fee') && input) {
                                    result.second_person_fee = input.value;
                                }
                                if (labelText.includes('Description') && (textarea || input)) {
                                    const source = textarea || input;
                                    result.description = (source.value || source.textContent || '').trim();
                                }
                            }
                            
                            return result;
                        }
                    """)
                    
                    # Merge data
                    listing['care_types'] = care_types
                    listing.update(pricing)
                    
                    enriched.append(listing)
                    
                    if i % 10 == 0:
                        self.log(f"Enriched {i}/{len(listings)} listings", "PROGRESS")
                    
                    await page.close()
                    await asyncio.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    self.log(f"Failed to enrich {listing.get('title', 'Unknown')}: {e}", "WARNING")
                    self.stats['failed_scrapes'] += 1
                    enriched.append(listing)  # Add without enrichment
                    if 'page' in locals():
                        await page.close()
            
            await browser.close()
        
        self.log(f"Enrichment complete: {len(enriched)} listings processed", "SUCCESS")
        return enriched
    
    def identify_new_and_updated(self, scraped_listings: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Compare scraped listings with current WordPress data
        Returns: (new_listings, updated_listings)
        """
        self.log("Comparing scraped data with WordPress database...")
        
        new_listings = []
        updated_listings = []
        
        for listing in scraped_listings:
            url = listing.get('url', '')
            
            if url not in self.current_wp_listings:
                # NEW listing not in WordPress
                new_listings.append(listing)
                self.stats['new_listings_found'] += 1
            else:
                # Existing listing - check for updates
                wp_listing = self.current_wp_listings[url]
                updates_needed = {}
                
                # Check pricing updates
                if listing.get('monthly_base_price'):
                    wp_price = wp_listing.get('acf', {}).get('price', '')
                    new_price = listing['monthly_base_price'].replace('$', '').replace(',', '')
                    if wp_price != new_price:
                        updates_needed['price'] = new_price
                        self.stats['pricing_updates'] += 1
                
                # Check if listing needs update based on Senior Place "Last updated" date
                # Extract last_updated from the scraped listing data
                sp_last_updated_str = listing.get('last_updated')
                if sp_last_updated_str:
                    try:
                        from datetime import datetime
                        sp_last_updated = datetime.fromisoformat(sp_last_updated_str)

                        # Compare with WordPress modified date
                        wp_modified_str = wp_listing.get('modified')
                        if wp_modified_str:
                            # Parse WordPress date (typically ISO format)
                            wp_modified = datetime.fromisoformat(wp_modified_str.replace('Z', '+00:00'))

                            # If Senior Place has newer data, mark for update
                            if sp_last_updated > wp_modified:
                                updates_needed['care_types'] = listing.get('care_types', [])
                                self.stats['care_type_updates'] += 1
                        else:
                            # No WordPress date available, assume update needed
                            updates_needed['care_types'] = listing.get('care_types', [])
                            self.stats['care_type_updates'] += 1
                    except Exception as e:
                        # Date parsing failed, fall back to care type comparison
                        self.log(f"Failed to parse last_updated date for {listing.get('title', 'Unknown')}: {e}", "DEBUG")
                        # Fall back to care type comparison below

                # Fallback: Check care type changes if no date available or date parsing failed
                if not updates_needed.get('care_types') and listing.get('care_types'):
                    # Get current care types from WordPress
                    wp_care_types = []
                    if 'acf' in wp_listing and 'care_types' in wp_listing['acf']:
                        wp_care_types = wp_listing['acf']['care_types']
                    elif 'meta' in wp_listing and '_care_types' in wp_listing['meta']:
                        wp_care_types = wp_listing['meta']['_care_types']

                    # Normalize both sets for comparison
                    current_normalized = self._normalize_care_types(wp_care_types)
                    new_normalized = self._normalize_care_types(listing['care_types'])

                    # Only update if care types actually changed
                    if set(current_normalized) != set(new_normalized):
                        updates_needed['care_types'] = listing['care_types']
                        self.stats['care_type_updates'] += 1
                
                if updates_needed:
                    listing['wp_id'] = wp_listing['id']
                    listing['updates'] = updates_needed
                    updated_listings.append(listing)
                    self.stats['listings_updated'] += 1
        
        self.log(f"Found {len(new_listings)} new listings", "SUCCESS")
        self.log(f"Found {len(updated_listings)} listings needing updates", "SUCCESS")
        
        return new_listings, updated_listings
    
    def generate_wordpress_import_files(self, new_listings: List[Dict], updated_listings: List[Dict]):
        """
        Generate CSV files ready for WordPress All Import
        """
        self.log("Generating WordPress import files...")
        
        output_dir = Path("monthly_updates") / self.timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Map care types to canonical WordPress taxonomy
        # Use core module for care type mapping
        def map_care_types(care_types_list):
            """Map care types using core module, return comma-separated string for CSV"""
            canonical_list = map_care_types_to_canonical(care_types_list)
            return ', '.join(canonical_list)
        
        # NEW LISTINGS CSV
        if new_listings:
            new_file = output_dir / f"new_listings_{self.timestamp}.csv"
            
            fieldnames = [
                'title', 'address', 'city', 'state', 'zip',
                'senior_place_url', 'featured_image', 'description',
                'price', 'normalized_types', 'care_types_raw',
                'price_high_end', 'second_person_fee', 'last_updated'
            ]
            
            with open(new_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for listing in new_listings:
                    # Use already-parsed address components from scraping
                    writer.writerow({
                        'title': listing.get('title', ''),
                        'address': listing.get('address', ''),
                        'city': listing.get('city', ''),
                        'state': listing.get('state', ''),
                        'zip': listing.get('zip', ''),
                        'senior_place_url': listing.get('url', ''),
                        'featured_image': listing.get('featured_image', ''),
                        'description': listing.get('description', ''),
                        'price': listing.get('monthly_base_price', '').replace('$', '').replace(',', ''),
                        'normalized_types': map_care_types(listing.get('care_types', [])),
                        'care_types_raw': ', '.join(listing.get('care_types', [])),
                        'price_high_end': listing.get('price_high_end', ''),
                        'second_person_fee': listing.get('second_person_fee', ''),
                        'last_updated': listing.get('last_updated', '')
                    })
            
            self.log(f"✅ New listings saved: {new_file}", "SUCCESS")
        
        # UPDATED LISTINGS CSV
        if updated_listings:
            update_file = output_dir / f"updated_listings_{self.timestamp}.csv"
            
            fieldnames = [
                'ID', 'title', 'senior_place_url',
                'price', 'normalized_types', 'care_types_raw',
                'update_reason', 'last_updated'
            ]
            
            with open(update_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for listing in updated_listings:
                    normalized_types = map_care_types(listing.get('care_types', []))
                    update_reasons = list(listing.get('updates', {}).keys())
                    
                    if not normalized_types:
                        # Care types didn't map - remove care_types from update reasons
                        # but still write the listing for other updates (e.g., price)
                        self.log(
                            f"No canonical care types for {listing.get('title', 'Unknown')} (raw: {listing.get('care_types')})",
                            "WARNING"
                        )
                        if 'care_types' in update_reasons:
                            update_reasons.remove('care_types')
                        
                        # Skip only if there are no other updates
                        if not update_reasons:
                            self.log(f"Skipping {listing.get('title', 'Unknown')} - no valid updates remain", "DEBUG")
                            continue

                    writer.writerow({
                        'ID': listing.get('wp_id', ''),
                        'title': listing.get('title', ''),
                        'senior_place_url': listing.get('url', ''),
                        'price': listing.get('monthly_base_price', '').replace('$', '').replace(',', ''),
                        'normalized_types': normalized_types,
                        'care_types_raw': ', '.join(listing.get('care_types', [])),
                        'update_reason': ', '.join(update_reasons),
                        'last_updated': listing.get('last_updated', '')
                    })
            
            self.log(f"✅ Updated listings saved: {update_file}", "SUCCESS")
        
        # SUMMARY REPORT
        summary_file = output_dir / f"update_summary_{self.timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'timestamp': self.timestamp,
                'stats': self.stats,
                'files_generated': {
                    'new_listings': str(new_file) if new_listings else None,
                    'updated_listings': str(update_file) if updated_listings else None
                }
            }, f, indent=2)
        
        self.log(f"✅ Summary report saved: {summary_file}", "SUCCESS")
        
        return output_dir
    
    async def run_full_update(self, states: List[Tuple[str, str]], resume_data: Optional[Dict] = None,
                              checkpoint_file: Optional[Path] = None):
        """
        Run complete monthly update process with optional resume support.
        states: List of (state_code, state_name) tuples, e.g., [('AZ', 'Arizona'), ('CA', 'California')]
        resume_data: Data loaded from a previous checkpoint (dict)
        checkpoint_file: Optional path to the checkpoint file (useful for tests)
        """
        self.log("=" * 80)
        self.log("MONTHLY UPDATE ORCHESTRATOR - FULL UPDATE", "SUCCESS")
        self.log("=" * 80)

        # Prepare checkpoint bookkeeping
        checkpoint_path = checkpoint_file or self._checkpoint_default_path()
        checkpoint_dir = checkpoint_path.parent
        raw_dir = checkpoint_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        # Determine states_remaining and states_completed
        states_map = {code: name for code, name in states}
        if resume_data:
            self.timestamp = resume_data.get("timestamp", self.timestamp)
            states_completed_codes: List[str] = resume_data.get("states_completed", [])
            states_remaining_codes: List[str] = resume_data.get("states_remaining", list(states_map.keys()))
            scraped_files: Dict[str, str] = resume_data.get("scraped_files", {})
            self.log(f"Resuming from checkpoint {checkpoint_path}", "INFO")
        else:
            states_completed_codes = []
            states_remaining_codes = list(states_map.keys())
            scraped_files = {}

        # Load already-scraped states from checkpoint to avoid re-scraping
        all_scraped_listings: List[Dict] = []
        for code in states_completed_codes:
            path_str = scraped_files.get(code)
            if not path_str:
                continue
            path = Path(path_str)
            if not path.exists():
                self.log(f"Checkpoint missing raw file for {code}, will re-scrape", "WARNING")
                states_remaining_codes.append(code)
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    state_listings = json.load(f)
                all_scraped_listings.extend(state_listings)
                self.stats['total_processed'] += len(state_listings)
                self.log(f"Loaded {len(state_listings)} cached listings for {code}", "INFO")
            except Exception as e:
                self.log(f"Failed to load cached {code} listings, will re-scrape: {e}", "WARNING")
                states_remaining_codes.append(code)

        # Deduplicate any codes if we had to re-add
        states_remaining_codes = list(dict.fromkeys(states_remaining_codes))
        
        # Step 1: Fetch current WordPress data
        self.current_wp_listings = self.fetch_current_wordpress_listings()
        
        # Step 2: Scrape all states
        for state_code in states_remaining_codes:
            state_name = states_map.get(state_code, state_code)
            state_listings = await self.scrape_seniorplace_state(state_code, state_name)
            all_scraped_listings.extend(state_listings)
            self.stats['total_processed'] += len(state_listings)

            # Persist raw listings for resume
            raw_file = raw_dir / f"{state_code}.json"
            with open(raw_file, "w", encoding="utf-8") as f:
                json.dump(state_listings, f, indent=2, ensure_ascii=False)

            # Update checkpoint after each state
            states_completed_codes.append(state_code)
            scraped_files[state_code] = str(raw_file)
            remaining = [c for c in states_map.keys() if c not in states_completed_codes]
            checkpoint_payload = {
                "timestamp": self.timestamp,
                "states_completed": states_completed_codes,
                "states_remaining": remaining,
                "scraped_files": scraped_files,
            }
            self._save_checkpoint(checkpoint_path, checkpoint_payload)
        
        # Step 3: Enrich with detailed data
        enriched_listings = await self.enrich_listing_details(all_scraped_listings)
        
        # Step 4: Identify new and updated
        new_listings, updated_listings = self.identify_new_and_updated(enriched_listings)
        self.new_listings = new_listings
        self.updated_listings = updated_listings
        
        # Step 5: Generate import files
        output_dir = self.generate_wordpress_import_files(new_listings, updated_listings)
        
        # Final summary
        self.log("=" * 80)
        self.log("UPDATE COMPLETE", "SUCCESS")
        self.log("=" * 80)
        self.log(f"📊 Total listings processed: {self.stats['total_processed']}")
        self.log(f"🆕 New listings found: {self.stats['new_listings_found']}")
        self.log(f"🔄 Listings updated: {self.stats['listings_updated']}")
        self.log(f"💰 Pricing updates: {self.stats['pricing_updates']}")
        self.log(f"🏥 Care type updates: {self.stats['care_type_updates']}")
        self.log(f"❌ Failed scrapes: {self.stats['failed_scrapes']}")
        self.log(f"📁 Output directory: {output_dir}")
        self.log("=" * 80)
        
        # Mark checkpoint as complete
        if checkpoint_path:
            final_payload = {
                "timestamp": self.timestamp,
                "states_completed": list(states_map.keys()),
                "states_remaining": [],
                "scraped_files": scraped_files,
                "status": "complete",
                "output_dir": str(output_dir),
            }
            self._save_checkpoint(checkpoint_path, final_payload)

        return output_dir


LOGIN_URL = "https://app.seniorplace.com/login"


async def main():
    # Set UTF-8 encoding for Windows console
    if os.name == 'nt':
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    parser = argparse.ArgumentParser(description="Monthly update orchestrator for senior living listings")
    parser.add_argument('--full-update', action='store_true', help='Run complete update (new + existing)')
    parser.add_argument('--new-only', action='store_true', help='Only find new listings')
    parser.add_argument('--updates-only', action='store_true', help='Only update existing listings')
    parser.add_argument('--states', nargs='+', default=['AZ', 'CA', 'CO', 'ID', 'NM', 'UT'],
                        help='State codes to process (default: all active states)')
    parser.add_argument('--wp-url', default='https://aplaceforseniorscms.kinsta.cloud',
                        help='WordPress site URL')
    parser.add_argument('--wp-username', default='nicholas_editor',
                        help='WordPress username')
    parser.add_argument('--wp-password', required=True,
                        help='WordPress application password')
    parser.add_argument('--sp-username', default='allison@aplaceforseniors.org',
                        help='Senior Place username')
    parser.add_argument('--sp-password', default=None,
                        help='Senior Place password (or set SP_PASSWORD env)')
    parser.add_argument('--resume-checkpoint', default=None,
                        help='Path to resume_checkpoint.json from a prior run')
    
    args = parser.parse_args()
    
    # Map state codes to names
    STATE_NAMES = {
        'AZ': 'Arizona', 'CA': 'California', 'CO': 'Colorado',
        'UT': 'Utah', 'ID': 'Idaho', 'NM': 'New Mexico',
        'WY': 'Wyoming', 'CT': 'Connecticut', 'AR': 'Arkansas'
    }
    
    states = [(code, STATE_NAMES.get(code, code)) for code in args.states]
    
    # Resolve SP password from args or environment
    sp_password = args.sp_password or os.getenv('SP_PASSWORD')
    if not sp_password:
        raise SystemExit("❌ Missing Senior Place password. Provide --sp-password or set SP_PASSWORD in environment.")

    resume_data = None
    checkpoint_path = None
    if args.resume_checkpoint:
        checkpoint_path = Path(args.resume_checkpoint)
        tmp_orch = MonthlyUpdateOrchestrator(
            wp_url=args.wp_url,
            wp_username=args.wp_username,
            wp_password=args.wp_password,
            sp_username=args.sp_username,
            sp_password=sp_password
        )
        resume_data = tmp_orch._load_checkpoint(checkpoint_path)
        if not resume_data:
            raise SystemExit(f"❌ Could not load checkpoint: {checkpoint_path}")

    orchestrator = MonthlyUpdateOrchestrator(
        wp_url=args.wp_url,
        wp_username=args.wp_username,
        wp_password=args.wp_password,
        sp_username=args.sp_username,
        sp_password=sp_password
    )
    
    if resume_data:
        orchestrator.timestamp = resume_data.get("timestamp", orchestrator.timestamp)
    
    if args.full_update or (not args.new_only and not args.updates_only):
        await orchestrator.run_full_update(states, resume_data=resume_data, checkpoint_file=checkpoint_path)
    elif args.new_only:
        # TODO: Implement new-only mode
        print("New-only mode not yet implemented")
    elif args.updates_only:
        # TODO: Implement updates-only mode
        print("Updates-only mode not yet implemented")


if __name__ == "__main__":
    asyncio.run(main())

