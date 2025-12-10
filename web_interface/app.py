#!/usr/bin/env python3
"""
Senior Scraper Web Interface
A visual dashboard for managing scraping, comparison, and import operations
"""

from flask import Flask, render_template, jsonify, request, send_file
from pathlib import Path
import subprocess
import json
import os
import sys
from datetime import datetime
import threading
import glob

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from wp_config.env
def load_env_file():
    """Load environment variables from wp_config.env"""
    env_file = Path(__file__).parent.parent / 'wp_config.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Remove inline comments
                    if '#' in value:
                        value = value.split('#')[0].strip().strip('"').strip("'")
                    os.environ[key] = value
        print("Loaded environment from wp_config.env")
    else:
        print("wp_config.env not found - using system environment")

load_env_file()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'senior-scraper-dashboard-2024'

# Track running processes
running_processes = {}

# File to persist process state across reloads
PROCESS_STATE_FILE = Path(__file__).parent / 'logs' / 'process_state.json'

# CANONICAL CARE TYPE MAPPING - must match orchestrator exactly
CARE_TYPE_MAPPING = {
    # Senior Place type (lowercase) -> WordPress canonical type
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
    'directed care': 'Assisted Living Home',  # Arizona-specific
    'personal care': 'Assisted Living Home',  # Care service type
    'supervisory care': 'Assisted Living Home',  # Care service type
}

def map_care_types_to_canonical(care_types_list):
    """
    Map raw Senior Place care types to WordPress canonical types.
    Filters out non-care-types (room types, bathroom types, etc.)
    """
    NOISE_PATTERNS = [
        'private pay',
        'medicaid',
        'contract',
        'cane',
        'walker',
        'wheelchair',
        'some memory loss',
        'private'
    ]
    canonical = []
    for ct in care_types_list or []:
        ct_lower = ct.lower().strip()
        if not ct_lower:
            continue
        if any(noise in ct_lower for noise in NOISE_PATTERNS):
            continue

        mapped = CARE_TYPE_MAPPING.get(ct_lower)

        # Fallback substring matching for partial labels like "independent"
        if not mapped:
            if 'assisted living' in ct_lower:
                mapped = 'Assisted Living Community'
            elif 'independent' in ct_lower:
                mapped = 'Independent Living'
            elif 'memory care' in ct_lower:
                mapped = 'Memory Care'
            elif 'nursing' in ct_lower:
                mapped = 'Nursing Home'
            elif 'home care' in ct_lower or 'home health' in ct_lower or 'in-home care' in ct_lower:
                mapped = 'Home Care'

        if mapped and mapped not in canonical:
            canonical.append(mapped)
    return canonical

def save_process_state():
    """Save running process info to disk for reload recovery"""
    state = {}
    for name, info in running_processes.items():
        state[name] = {
            'pid': info['process'].pid if info.get('process') else None,
            'log_file': info.get('log_file'),
            'started': info.get('started')
        }
    PROCESS_STATE_FILE.parent.mkdir(exist_ok=True)
    with open(PROCESS_STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_process_state():
    """Load and verify running processes from disk"""
    if not PROCESS_STATE_FILE.exists():
        return {}
    
    try:
        with open(PROCESS_STATE_FILE, 'r') as f:
            state = json.load(f)
        
        # Check which processes are still alive
        import psutil
        active = {}
        for name, info in state.items():
            pid = info.get('pid')
            if pid:
                try:
                    proc = psutil.Process(pid)
                    if proc.is_running() and 'python' in proc.name().lower():
                        active[name] = {
                            'pid': pid,
                            'log_file': info.get('log_file'),
                            'started': info.get('started'),
                            'recovered': True
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        # Update state file with only active processes
        with open(PROCESS_STATE_FILE, 'w') as f:
            json.dump(active, f)
        
        return active
    except Exception as e:
        print(f"Error loading process state: {e}")
        return {}

def get_project_root():
    """Get the project root directory"""
    return Path(__file__).parent.parent

def get_recent_runs():
    """Get list of recent scraper runs"""
    project_root = get_project_root()
    updates_dir = project_root / "monthly_updates"
    
    if not updates_dir.exists():
        return []
    
    runs = []
    for run_dir in sorted(updates_dir.iterdir(), reverse=True):
        if run_dir.is_dir():
            summary_file = run_dir / f"update_summary_{run_dir.name}.json"
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    data = json.load(f)
                    data['directory'] = run_dir.name
                    runs.append(data)
    
    return runs[:10]  # Return last 10 runs

def get_wordpress_stats():
    """Get current WordPress statistics"""
    try:
        # Check if credentials are set
        wp_user = os.getenv('WP_USER') or os.getenv('WP_USERNAME')
        wp_pass = os.getenv('WP_PASSWORD') or os.getenv('WP_PASS')
        
        if not wp_user or not wp_pass:
            return {"error": "WordPress credentials not set"}
        
        import requests
        wp_url = os.getenv('WP_URL', 'https://aplaceforseniorscms.kinsta.cloud')
        
        # Get total listings count
        response = requests.get(
            f"{wp_url}/wp-json/wp/v2/listing",
            auth=(wp_user, wp_pass),
            params={'per_page': 1},
            timeout=10
        )
        
        if response.status_code == 200:
            total_pages = int(response.headers.get('X-WP-TotalPages', 0))
            total_listings = int(response.headers.get('X-WP-Total', 0))
            
            return {
                "total_listings": total_listings,
                "total_pages": total_pages,
                "status": "connected"
            }
        else:
            return {"error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"error": str(e)}

def get_available_csv_files():
    """Get list of available CSV files for import"""
    project_root = get_project_root()
    csv_files = []
    
    # Check for state CSV files
    for pattern in ['*_seniorplace_data_*.csv', 'monthly_updates/*/new_listings_*.csv', 
                    'monthly_updates/*/updated_listings_*.csv']:
        for csv_file in project_root.glob(pattern):
            csv_files.append({
                'name': csv_file.name,
                'path': str(csv_file.relative_to(project_root)),
                'size': csv_file.stat().st_size,
                'modified': datetime.fromtimestamp(csv_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            })
    
    return sorted(csv_files, key=lambda x: x['modified'], reverse=True)[:20]

# App version helper
def get_app_version():
    """Return app version from APP_VERSION env or git short hash."""
    if hasattr(app, "_app_version"):
        return app._app_version
    
    env_version = os.getenv("APP_VERSION")
    if env_version:
        app._app_version = env_version.strip()
        return app._app_version
    
    try:
        git_ver = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=get_project_root()
        )
        app._app_version = git_ver.decode().strip()
    except Exception:
        app._app_version = "unknown"
    return app._app_version

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """Get current system status"""
    recent_runs = get_recent_runs()
    wp_stats = get_wordpress_stats()
    csv_files = get_available_csv_files()
    
    # Check environment variables
    env_status = {
        'wp_credentials': bool(os.getenv('WP_USER') or os.getenv('WP_USERNAME')) and bool(os.getenv('WP_PASSWORD')),
        'sp_credentials': bool(os.getenv('SP_USERNAME')) and bool(os.getenv('SP_PASSWORD')),
    }
    
    # Check for recovered processes from disk (survives page reload)
    recovered = load_process_state()
    active_processes = list(running_processes.keys()) + list(recovered.keys())
    
    return jsonify({
        'recent_runs': recent_runs,
        'wordpress': wp_stats,
        'csv_files': csv_files,
        'environment': env_status,
        'app_version': get_app_version(),
        'running_processes': list(set(active_processes)),
        'recovered_processes': recovered
    })

@app.route('/api/fetch-single-listing', methods=['POST'])
def api_fetch_single_listing():
    """Fetch details for a single Senior Place listing"""
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # Import here to avoid issues if playwright not needed for other routes
        from playwright.async_api import async_playwright
        import asyncio
        
        sp_user = os.getenv('SP_USERNAME')
        sp_pass = os.getenv('SP_PASSWORD')
        if not sp_user or not sp_pass:
            return jsonify({'error': 'Senior Place credentials not set on server'}), 400
        
        async def get_listing_details():
            """Fetch listing details from Senior Place"""
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                try:
                    # Login to Senior Place to access attributes
                    await page.goto("https://app.seniorplace.com/login", timeout=30000)
                    await page.wait_for_timeout(500)  # Wait for page to load
                    await page.fill('input[name="email"]', sp_user)
                    await page.fill('input[name="password"]', sp_pass)
                    await page.click('button[type="submit"]')
                    # Wait for login to complete and verify we're logged in
                    await page.wait_for_selector('text=Communities', timeout=15000)
                    await page.wait_for_timeout(1000)  # Ensure session is established
                    
                    # Normalize to base URL (strip /details or /attributes suffixes)
                    base_url = url.split('?')[0]
                    for suffix in ['/details', '/attributes']:
                        if base_url.endswith(suffix):
                            base_url = base_url[:-len(suffix)]
                    # Navigate to listing page (session/cookies will be maintained)
                    await page.goto(base_url, timeout=30000, wait_until="networkidle")
                    await page.wait_for_timeout(2000)  # Give page more time to render
                    
                    # Extract title - match actual Senior Place detail page structure
                    # Title is in h2 with classes like "text-base md:text-xl lg:text-2xl"
                    # OR in the Name input field
                    title_data = await page.evaluate("""
                        () => {
                            // Try h2 with text-xl or text-2xl classes (actual detail page structure)
                            const h2 = document.querySelector('h2.text-base, h2.text-xl, h2.text-2xl');
                            if (h2 && h2.textContent.trim()) {
                                return h2.textContent.trim();
                            }
                            
                            // Try Name input field (form field)
                            const nameInput = Array.from(document.querySelectorAll('input')).find(input => {
                                const label = input.closest('label');
                                if (label) {
                                    const labelText = label.textContent || '';
                                    return labelText.includes('Name') && input.value;
                                }
                                return false;
                            });
                            if (nameInput && nameInput.value.trim()) {
                                return nameInput.value.trim();
                            }
                            
                            // Fallback to any h2
                            const anyH2 = document.querySelector('h2');
                            if (anyH2 && anyH2.textContent.trim()) {
                                return anyH2.textContent.trim();
                            }
                            
                            return '';
                        }
                    """)
                    title = title_data.strip() if title_data else 'Unknown'
                    
                    # Extract address using Details tab form fields first, then fallbacks
                    detail_data = {}
                    def extract_details_js():
                        return """
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
                        """

                    detail_data = {}
                    try:
                        await page.wait_for_selector('a[data-subpage="details"]', timeout=5000)
                        await page.click('a[data-subpage="details"]')
                        await page.wait_for_timeout(1200)
                        detail_data = await page.evaluate(extract_details_js())
                    except Exception:
                        detail_data = {}

                    # If still empty, try navigating directly to /details and retry
                    if not any(detail_data.values()):
                        try:
                            details_url = base_url.rstrip('/') + '/details'
                            await page.goto(details_url, wait_until="networkidle", timeout=20000)
                            await page.wait_for_timeout(1200)
                            detail_data = await page.evaluate(extract_details_js())
                        except Exception:
                            pass
                    
                    # Fallback extraction from visible address blocks
                    addr_data = await page.evaluate("""
                        () => {
                            // Try address tag first (standard HTML5)
                            const addressEl = document.querySelector('address');
                            if (addressEl) {
                                const ps = addressEl.querySelectorAll('p');
                                if (ps.length >= 2) {
                                    return {
                                        address: ps[0].textContent.trim(),
                                        location: ps[1].textContent.trim()
                                    };
                                }
                                // Single p in address
                                if (ps.length === 1) {
                                    const text = ps[0].textContent.trim();
                                    const lines = text.split('\\n').filter(l => l.trim() && !l.includes('Directions'));
                                    if (lines.length >= 2) {
                                        return { address: lines[0].trim(), location: lines[1].trim() };
                                    }
                                }
                            }
                            
                            // Try div.text-sm.text-gray-500 (like card view uses)
                            const addrDiv = document.querySelector('div.text-sm.text-gray-500');
                            if (addrDiv) {
                                const text = addrDiv.textContent.trim();
                                // Filter out metadata like "Last updated", "Directions", phone numbers
                                const lines = text.split('\\n').filter(l => {
                                    const trimmed = l.trim();
                                    return trimmed && 
                                           !trimmed.includes('Directions') && 
                                           !trimmed.includes('Last updated') &&
                                           !trimmed.includes('updated on') &&
                                           !trimmed.match(/^\\(\\d{3}\\)/) && // Phone numbers
                                           trimmed.length > 5; // Must be substantial text
                                });
                                if (lines.length >= 2) {
                                    // First line should look like an address (has numbers)
                                    if (/\\d+/.test(lines[0])) {
                                        return { address: lines[0].trim(), location: lines[1].trim() };
                                    }
                                }
                                if (lines.length === 1 && text.includes(',')) {
                                    // Single line with comma
                                    const parts = text.split(',').map(p => p.trim());
                                    if (parts.length >= 2 && /\\d+/.test(parts[0])) {
                                        return { address: parts[0], location: parts.slice(1).join(', ') };
                                    }
                                }
                            }
                            
                            // Try any element with address-like classes or content
                            const candidates = document.querySelectorAll('[class*="address"], [class*="location"], .address, .location');
                            for (const el of candidates) {
                                const text = el.textContent.trim();
                                if (text && (/\d+/.test(text) || text.includes(','))) {
                                    const lines = text.split('\\n').filter(l => l.trim());
                                    if (lines.length >= 2) {
                                        return { address: lines[0].trim(), location: lines[1].trim() };
                                    }
                                }
                            }
                            
                            return { address: '', location: '' };
                        }
                    """)
                    
                    address = (detail_data.get('address') or addr_data.get('address') or '').strip()
                    location = addr_data.get('location', '').strip() if addr_data else ''
                    city = (detail_data.get('city') or '').strip()
                    state = (detail_data.get('state') or '').strip()
                    zip_code = (detail_data.get('zip') or '').strip()
                    
                    # Parse location into city, state, zip if not already populated
                    if location and (not city or not state):
                        parts = location.split(',')
                        if len(parts) >= 2:
                            city = city or parts[0].strip()
                            state_zip = parts[1].strip().split()
                            if len(state_zip) > 0 and not state:
                                state = state_zip[0]
                            if len(state_zip) > 1 and not zip_code:
                                zip_code = state_zip[1]
                    
                    # Extract care types and pricing from attributes tab
                    # Click on the Attributes tab to access full data
                    try:
                        # Wait for the tab navigation to be available
                        await page.wait_for_selector('a[data-subpage="attributes"]', timeout=5000)
                        await page.click('a[data-subpage="attributes"]')
                        await page.wait_for_timeout(2000)  # Wait for attributes tab to load
                    except Exception as e:
                        # If clicking doesn't work, try navigating directly
                        try:
                            attrs_url = url.rstrip('/') + '/attributes'
                            await page.goto(attrs_url, wait_until="networkidle", timeout=20000)
                            await page.wait_for_timeout(1000)
                        except:
                            pass
                    
                    care_types = []
                    pricing_and_desc = {}
                    
                    try:
                        # Extract care types from "Community Type(s)" section
                        # Based on the HTML structure provided
                        care_types = await page.evaluate("""
                            () => {
                                const types = [];
                                // Find the "Community Type(s)" section
                                const sections = Array.from(document.querySelectorAll('div'));
                                let communityTypesSection = null;
                                
                                for (const section of sections) {
                                    const text = section.textContent || '';
                                    if (text.includes('Community Type(s)')) {
                                        communityTypesSection = section;
                                        break;
                                    }
                                }
                                
                                if (communityTypesSection) {
                                    // Find all checked checkboxes in this section
                                    const checkboxes = communityTypesSection.querySelectorAll('input[type="checkbox"]:checked');
                                    for (const checkbox of checkboxes) {
                                        const label = checkbox.closest('label');
                                        if (label) {
                                            const textEl = label.querySelector('div.ml-2');
                                            if (textEl) {
                                                const name = (textEl.textContent || "").trim();
                                                if (name && !name.includes('Room') && !name.includes('Bedroom') && !name.includes('Studio')) {
                                                    types.push(name);
                                                }
                                            }
                                        }
                                    }
                                }
                                
                                // Fallback: get all checked checkboxes with care type labels
                                if (types.length === 0) {
                                    const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                                    for (const label of labels) {
                                        const textEl = label.querySelector("div.ml-2");
                                        const input = label.querySelector('input[type="checkbox"]');
                                        
                                        if (!textEl || !input) continue;
                                        if (!input.checked) continue;
                                        
                                        const name = (textEl.textContent || "").trim();
                                        // Filter out room types
                                        if (name && !name.includes('Room') && !name.includes('Bedroom') && !name.includes('Studio') && !name.includes('Private') && !name.includes('Shared')) {
                                            types.push(name);
                                        }
                                    }
                                }
                                
                                return types;
                            }
                        """)
                    except Exception:
                        care_types = []
                    
                    try:
                        # Extract pricing from Finances section
                        pricing_and_desc = await page.evaluate("""
                            () => {
                                const result = {};
                                
                                // Find all input fields and match by label text
                                const inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="number"], input[inputmode="decimal"]'));
                                
                                for (const input of inputs) {
                                    // Look for label associated with this input
                                    const label = input.closest('label') || input.closest('.form-group')?.querySelector('label');
                                    const labelText = label ? (label.textContent || '').toLowerCase() : '';
                                    
                                    // Check parent containers for label text
                                    let parent = input.parentElement;
                                    for (let i = 0; i < 5 && parent; i++) {
                                        const parentText = (parent.textContent || '').toLowerCase();
                                        if (parentText.includes('monthly base price')) {
                                            result.monthly_base_price = input.value || '';
                                            break;
                                        }
                                        if (parentText.includes('price (high end)') || parentText.includes('high end')) {
                                            result.price_high_end = input.value || '';
                                            break;
                                        }
                                        if (parentText.includes('second person fee')) {
                                            result.second_person_fee = input.value || '';
                                            break;
                                        }
                                        parent = parent.parentElement;
                                    }
                                }
                                
                                // Try to find description - might be in Details tab or a textarea
                                const textareas = Array.from(document.querySelectorAll('textarea'));
                                for (const textarea of textareas) {
                                    const label = textarea.closest('label');
                                    const labelText = label ? (label.textContent || '').toLowerCase() : '';
                                    if (labelText.includes('description') || labelText.includes('notes')) {
                                        const desc = (textarea.value || textarea.textContent || '').trim();
                                        if (desc && desc.length > 20) {
                                            result.description = desc;
                                            break;
                                        }
                                    }
                                }
                                
                                return result;
                            }
                        """)
                    except Exception:
                        pricing_and_desc = {}
                    
                    # Extract featured image from main listing page - exclude logo, get community image
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    await page.wait_for_timeout(1000)
                    
                    featured_image = ""
                    # Get all images and find the community image (not the logo)
                    img_data = await page.evaluate("""
                        () => {
                            const images = Array.from(document.querySelectorAll('img'));
                            // Look for community image - exclude logos
                            for (const img of images) {
                                const src = img.src || img.getAttribute('src') || '';
                                // Skip logo images
                                if (src.includes('/logo') || src.includes('/api/tenants/')) {
                                    continue;
                                }
                                // Look for community images
                                if (src.includes('/api/files/') || src.includes('/_entities/communities/')) {
                                    return src;
                                }
                                // If it's a relative path that looks like a file
                                if (src.startsWith('/api/') || src.startsWith('/_entities/')) {
                                    return src;
                                }
                            }
                            // If no community image found, get first non-logo image
                            for (const img of images) {
                                const src = img.src || img.getAttribute('src') || '';
                                if (!src.includes('/logo') && !src.includes('/api/tenants/')) {
                                    return src;
                                }
                            }
                            return '';
                        }
                    """)
                    
                    if img_data:
                        img_src = img_data
                        # Match orchestrator's logic exactly
                        if img_src.startswith("/api/files/"):
                            featured_image = f"https://placement-crm-cdn.s3.us-west-2.amazonaws.com{img_src}"
                        elif img_src.startswith("/_entities/communities/"):
                            # Direct community image path
                            featured_image = f"https://placement-crm-cdn.s3.us-west-2.amazonaws.com{img_src}"
                        elif img_src.startswith("http"):
                            featured_image = img_src
                        elif img_src.startswith("/"):
                            # Relative path - try CDN conversion
                            if "/api/" in img_src or "/_entities/" in img_src:
                                featured_image = f"https://placement-crm-cdn.s3.us-west-2.amazonaws.com{img_src}"
                            else:
                                featured_image = f"https://app.seniorplace.com{img_src}"
                        else:
                            featured_image = img_src
                    
                    await browser.close()
                    
                    # Map to canonical care types (filters out room types, etc.)
                    canonical_types = map_care_types_to_canonical(care_types)
                    
                    return {
                        'title': title.strip(),
                        'address': address.strip(),
                        'city': city.strip(),
                        'state': state.strip(),
                        'zip': zip_code.strip(),
                        'care_types': ', '.join(canonical_types) if canonical_types else '',
                        'care_types_raw': ', '.join(care_types) if care_types else '',
                        'monthly_base_price': pricing_and_desc.get('monthly_base_price', ''),
                        'price_high_end': pricing_and_desc.get('price_high_end', ''),
                        'second_person_fee': pricing_and_desc.get('second_person_fee', ''),
                        'description': pricing_and_desc.get('description', ''),
                        'url': url,
                        'featured_image': featured_image
                    }
                    
                except Exception as e:
                    await browser.close()
                    raise e
        
        # Run async function
        listing = asyncio.run(get_listing_details())
        
        return jsonify({'listing': listing})
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch listing: {str(e)}'}), 500

@app.route('/api/compare-single-listing', methods=['POST'])
def api_compare_single_listing():
    """Compare a single Senior Place listing with WordPress listings"""
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # First, fetch the listing from Senior Place
        from playwright.async_api import async_playwright
        import asyncio
        import requests
        from pathlib import Path
        
        sp_user = os.getenv('SP_USERNAME')
        sp_pass = os.getenv('SP_PASSWORD')
        wp_user = os.getenv('WP_USERNAME')
        wp_pass = os.getenv('WP_PASSWORD')
        wp_url = os.getenv('WP_URL', 'https://aplaceforseniorscms.kinsta.cloud')
        
        if not sp_user or not sp_pass:
            return jsonify({'error': 'Senior Place credentials not set on server'}), 400
        
        # Reuse the fetch function
        async def get_listing():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                try:
                    await page.goto("https://app.seniorplace.com/login", timeout=30000)
                    await page.wait_for_timeout(500)
                    await page.fill('input[name="email"]', sp_user)
                    await page.fill('input[name="password"]', sp_pass)
                    await page.click('button[type="submit"]')
                    await page.wait_for_selector('text=Communities', timeout=15000)
                    await page.wait_for_timeout(1000)
                    
                    # Normalize to base URL (strip /details or /attributes suffixes)
                    base_url = url.split('?')[0]
                    for suffix in ['/details', '/attributes']:
                        if base_url.endswith(suffix):
                            base_url = base_url[:-len(suffix)]

                    await page.goto(base_url, timeout=30000, wait_until="networkidle")
                    await page.wait_for_timeout(2000)
                    
                    # Extract title
                    title_data = await page.evaluate("""
                        () => {
                            const h2 = document.querySelector('h2.text-base, h2.text-xl, h2.text-2xl');
                            if (h2 && h2.textContent.trim()) return h2.textContent.trim();
                            const nameInput = Array.from(document.querySelectorAll('input')).find(input => {
                                const label = input.closest('label');
                                return label && label.textContent.includes('Name') && input.value;
                            });
                            if (nameInput && nameInput.value.trim()) return nameInput.value.trim();
                            const anyH2 = document.querySelector('h2');
                            return anyH2 ? anyH2.textContent.trim() : '';
                        }
                    """)
                    title = title_data.strip() if title_data else 'Unknown'
                    
                    # Details extractor JS
                    def extract_details_js():
                        return """
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
                        """

                    detail_data = {}
                    try:
                        await page.wait_for_selector('a[data-subpage="details"]', timeout=5000)
                        await page.click('a[data-subpage="details"]')
                        await page.wait_for_timeout(1200)
                        detail_data = await page.evaluate(extract_details_js())
                    except Exception:
                        detail_data = {}

                    if not any(detail_data.values()):
                        try:
                            details_url = base_url.rstrip('/') + '/details'
                            await page.goto(details_url, wait_until="networkidle", timeout=20000)
                            await page.wait_for_timeout(1200)
                            detail_data = await page.evaluate(extract_details_js())
                        except Exception:
                            pass

                    # Fallback address extraction from visible blocks
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

                    address = (detail_data.get('address') or addr_data.get('address') or '').strip()
                    location = addr_data.get('location', '').strip() if addr_data else ''
                    city = (detail_data.get('city') or '').strip()
                    state = (detail_data.get('state') or '').strip()
                    zip_code = (detail_data.get('zip') or '').strip()

                    if location and (not city or not state):
                        parts = location.split(',')
                        if len(parts) >= 2:
                            city = city or parts[0].strip()
                            state_zip = parts[1].strip().split()
                            if len(state_zip) > 0 and not state:
                                state = state_zip[0]
                            if len(state_zip) > 1 and not zip_code:
                                zip_code = state_zip[1]
                    
                    # Click attributes tab
                    try:
                        await page.wait_for_selector('a[data-subpage="attributes"]', timeout=5000)
                        await page.click('a[data-subpage="attributes"]')
                        await page.wait_for_timeout(2000)
                    except:
                        pass
                    
                    # Extract care types
                    care_types = await page.evaluate("""
                        () => {
                            const types = [];
                            const sections = Array.from(document.querySelectorAll('div'));
                            let communityTypesSection = null;
                            for (const section of sections) {
                                if (section.textContent.includes('Community Type(s)')) {
                                    communityTypesSection = section;
                                    break;
                                }
                            }
                            if (communityTypesSection) {
                                const checkboxes = communityTypesSection.querySelectorAll('input[type="checkbox"]:checked');
                                for (const checkbox of checkboxes) {
                                    const label = checkbox.closest('label');
                                    if (label) {
                                        const textEl = label.querySelector('div.ml-2');
                                        if (textEl) {
                                            const name = textEl.textContent.trim();
                                            if (name && !name.includes('Room') && !name.includes('Bedroom') && !name.includes('Studio')) {
                                                types.push(name);
                                            }
                                        }
                                    }
                                }
                            }
                            return types;
                        }
                    """)
                    
                    # Extract pricing
                    pricing = await page.evaluate("""
                        () => {
                            const result = {};
                            const inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="number"], input[inputmode="decimal"]'));
                            for (const input of inputs) {
                                let parent = input.parentElement;
                                for (let i = 0; i < 5 && parent; i++) {
                                    const parentText = (parent.textContent || '').toLowerCase();
                                    if (parentText.includes('monthly base price')) {
                                        result.monthly_base_price = input.value || '';
                                        break;
                                    }
                                    if (parentText.includes('price (high end)') || parentText.includes('high end')) {
                                        result.price_high_end = input.value || '';
                                        break;
                                    }
                                    if (parentText.includes('second person fee')) {
                                        result.second_person_fee = input.value || '';
                                        break;
                                    }
                                    parent = parent.parentElement;
                                }
                            }
                            return result;
                        }
                    """)
                    
                    await browser.close()
                    
                    # Map to canonical care types (filters out room types, etc.)
                    canonical_types = map_care_types_to_canonical(care_types)
                    
                    return {
                        'title': title.strip(),
                        'address': address.strip(),
                        'city': city.strip(),
                        'state': state.strip(),
                        'zip': zip_code.strip(),
                        'care_types': ', '.join(canonical_types) if canonical_types else '',
                        'care_types_raw': ', '.join(care_types) if care_types else '',
                        'monthly_base_price': pricing.get('monthly_base_price', ''),
                        'price_high_end': pricing.get('price_high_end', ''),
                        'second_person_fee': pricing.get('second_person_fee', ''),
                        'url': url
                    }
                except Exception as e:
                    await browser.close()
                    raise e
        
        sp_listing = asyncio.run(get_listing())
        
        # Load cached WordPress listings or fetch a small subset
        wp_listings = {}
        cache_file = Path(".cache/wp_listings_cache.json")
        
        if cache_file.exists():
            try:
                import json
                import time
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    if time.time() - cache_data.get('timestamp', 0) < 3600:  # 1 hour TTL
                        wp_listings = cache_data.get('data', {})
            except:
                pass
        
        # If no cache, fetch a small subset by searching for similar titles
        if not wp_listings and wp_user and wp_pass:
            try:
                # Search WordPress by title (normalized)
                def normalize_title(t):
                    return t.lower().strip().replace("'", "").replace("-", " ").replace(".", "")
                
                search_title = normalize_title(sp_listing['title'])
                page = 1
                found_match = False
                
                while page <= 5 and not found_match:  # Search first 5 pages
                    response = requests.get(
                        f"{wp_url}/wp-json/wp/v2/listing",
                        params={'per_page': 100, 'page': page, 'search': sp_listing['title'][:50]},
                        auth=(wp_user, wp_pass),
                        timeout=30
                    )
                    if response.status_code != 200:
                        break
                    
                    listings = response.json()
                    if not listings:
                        break
                    
                    for listing in listings:
                        wp_title = listing.get('title', {}).get('rendered', '')
                        if normalize_title(wp_title) == search_title:
                            # Found match by title
                            sp_url = listing.get('acf', {}).get('senior_place_url') or listing.get('acf', {}).get('url', '')
                            wp_listings[sp_listing['url']] = listing
                            found_match = True
                            break
                    
                    page += 1
            except Exception as e:
                pass
        
        # Compare
        match_type = 'new'
        wp_match = None
        
        # First check by URL
        if sp_listing['url'] in wp_listings:
            match_type = 'exists'
            wp_match = wp_listings[sp_listing['url']]
        else:
            # Check by title
            def normalize_title(t):
                return t.lower().strip().replace("'", "").replace("-", " ").replace(".", "")
            
            sp_title_norm = normalize_title(sp_listing['title'])
            for wp_url_key, wp_listing in wp_listings.items():
                wp_title = wp_listing.get('title', {}).get('rendered', '')
                if normalize_title(wp_title) == sp_title_norm:
                    match_type = 'exists_by_title'
                    wp_match = wp_listing
                    break
        
        return jsonify({
            'sp_listing': sp_listing,
            'match_type': match_type,  # 'new', 'exists', 'exists_by_title'
            'wp_listing': wp_match,
            'message': {
                'new': 'This is a NEW listing not found in WordPress',
                'exists': 'This listing already exists in WordPress (matched by URL)',
                'exists_by_title': 'A listing with the same title exists in WordPress (different URL)'
            }.get(match_type, 'Unknown status')
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to compare listing: {str(e)}'}), 500

@app.route('/api/run-scraper', methods=['POST'])
def api_run_scraper():
    """Start scraper process"""
    data = request.json
    states = data.get('states', ['AZ', 'CA', 'CO', 'ID', 'NM', 'UT'])
    
    # Check if already running
    if 'scraper' in running_processes:
        proc_info = running_processes['scraper']
        # Check if process is actually still alive
        if proc_info['process'].poll() is None:
            return jsonify({'error': 'Scraper is already running from a previous request. Please wait or restart the dashboard.'}), 400
        else:
            # Process died but wasn't cleaned up, remove it
            del running_processes['scraper']
        # Fall through to start new one
    
    try:
        project_root = get_project_root()
        
        # Start scraper in background (use -u for unbuffered output)
        cmd = [
            sys.executable, '-u',
            str(project_root / 'monthly_scrapers' / 'monthly_update_orchestrator.py'),
            '--full-update',
            '--states'] + states + [
            '--wp-password', os.getenv('WP_PASSWORD', ''),
            '--sp-password', os.getenv('SP_PASSWORD', '')
        ]
        
        # Create log file
        log_dir = project_root / 'web_interface' / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Open file handle that stays open for the subprocess
        log_handle = open(log_file, 'w', encoding='utf-8')
        
        # Pass environment variables to subprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=project_root,
            env=env,
            bufsize=1  # Line buffered
        )
        
        running_processes['scraper'] = {
            'process': process,
            'log_file': str(log_file),
            'log_handle': log_handle,  # Keep handle open
            'started': datetime.now().isoformat()
        }
        
        # Persist to disk for reload recovery
        save_process_state()
        
        return jsonify({
            'status': 'started',
            'log_file': str(log_file.relative_to(project_root))
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-csv', methods=['POST'])
def api_upload_csv():
    """Upload a CSV file for import"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    try:
        project_root = get_project_root()
        upload_dir = project_root / 'web_interface' / 'uploads'
        upload_dir.mkdir(exist_ok=True)
        
        # Save with timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"upload_{timestamp}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        file.save(str(file_path))
        
        # Count rows
        import csv
        with open(file_path, 'r', encoding='utf-8') as f:
            row_count = sum(1 for _ in csv.DictReader(f))
        
        return jsonify({
            'status': 'uploaded',
            'filename': safe_filename,
            'path': str(file_path.relative_to(project_root)),
            'row_count': row_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/run-import', methods=['POST'])
def api_run_import():
    """Start import process"""
    data = request.json
    csv_file = data.get('csv_file')
    batch_size = data.get('batch_size', 25)
    limit = data.get('limit')
    
    if not csv_file:
        return jsonify({'error': 'No CSV file specified'}), 400
    
    if 'import' in running_processes:
        proc_info = running_processes['import']
        # Check if process is actually still alive
        if proc_info['process'].poll() is None:
            return jsonify({'error': 'Import is already running from a previous request. Please wait or restart the dashboard.'}), 400
        else:
            # Process died but wasn't cleaned up, remove it
            del running_processes['import']
        # Fall through to start new one
    
    try:
        project_root = get_project_root()
        csv_path = project_root / csv_file
        
        if not csv_path.exists():
            return jsonify({'error': 'CSV file not found'}), 404
        
        # Build command (use -u for unbuffered output)
        cmd = [
            sys.executable, '-u',
            str(project_root / 'import_to_wordpress_api_safe.py'),
            str(csv_path),
            '--batch-size', str(batch_size)
        ]
        
        if limit:
            cmd.extend(['--limit', str(limit)])
        
        # Create log file
        log_dir = project_root / 'web_interface' / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Open file handle that stays open for the subprocess
        log_handle = open(log_file, 'w', encoding='utf-8')
        
        # Pass environment variables to subprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            cwd=project_root,
            env=env,
            bufsize=1  # Line buffered
        )
        # Auto-confirm with 'yes'
        process.stdin.write(b'yes\n')
        process.stdin.flush()
        
        running_processes['import'] = {
            'process': process,
            'log_file': str(log_file),
            'log_handle': log_handle,  # Keep handle open
            'started': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'started',
            'log_file': str(log_file.relative_to(project_root))
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-status/<process_name>')
def api_process_status(process_name):
    """Check status of running process"""
    # First check in-memory processes
    if process_name in running_processes:
        proc_info = running_processes[process_name]
        process = proc_info['process']
        
        # Check if still running
        if process.poll() is None:
            status = 'running'
        else:
            status = 'completed' if process.returncode == 0 else 'failed'
            # Close log file handle if present
            if 'log_handle' in proc_info and proc_info['log_handle']:
                try:
                    proc_info['log_handle'].close()
                except:
                    pass
            # Clean up
            del running_processes[process_name]
            save_process_state()
        
        return jsonify({
            'status': status,
            'log_file': proc_info['log_file'],
            'started': proc_info['started']
        })
    
    # Check recovered processes from disk (survives page reload)
    recovered = load_process_state()
    if process_name in recovered:
        proc_info = recovered[process_name]
        return jsonify({
            'status': 'running',
            'log_file': proc_info['log_file'],
            'started': proc_info['started'],
            'recovered': True
        })
    
    return jsonify({'status': 'not_running'})

@app.route('/api/stop-process/<process_name>', methods=['POST'])
def api_stop_process(process_name):
    """Stop a running process"""
    if process_name not in running_processes:
        return jsonify({'error': 'Process not running'}), 400
    
    proc_info = running_processes[process_name]
    process = proc_info['process']
    
    try:
        # Terminate the process
        if os.name == 'nt':
            # Windows
            os.system(f'taskkill /PID {process.pid} /F /T')
        else:
            # Unix/Linux/Mac
            process.terminate()
            process.wait(timeout=5)
        
        # Close log file handle if present
        if 'log_handle' in proc_info and proc_info['log_handle']:
            try:
                proc_info['log_handle'].close()
            except:
                pass
        
        # Clean up
        del running_processes[process_name]
        
        return jsonify({'status': 'stopped', 'message': f'{process_name} process stopped'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/<path:log_file>')
def api_get_log(log_file):
    """Get log file contents"""
    try:
        project_root = get_project_root()
        log_path = project_root / log_file
        
        if not log_path.exists():
            return jsonify({'error': 'Log file not found'}), 404
        
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return jsonify({'content': content})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-connection')
def api_test_connection():
    """Test WordPress connection"""
    try:
        project_root = get_project_root()
        
        # Run the test script
        result = subprocess.run(
            [sys.executable, str(project_root / 'monthly_scrapers' / 'test_monthly_update.py')],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=project_root,
            env={**os.environ, 'WP_PASSWORD': os.getenv('WP_PASSWORD', ''), 'SP_PASSWORD': os.getenv('SP_PASSWORD', '')}
        )
        
        return jsonify({
            'exit_code': result.returncode,
            'output': result.stdout,
            'errors': result.stderr
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 80)
    print("Senior Scraper Web Interface")
    print("=" * 80)
    print(f"Starting server at http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

