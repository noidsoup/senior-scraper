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
        print("✅ Loaded environment from wp_config.env")
    else:
        print("⚠️  wp_config.env not found - using system environment")

load_env_file()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'senior-scraper-dashboard-2024'

# Track running processes
running_processes = {}

# File to persist process state across reloads
PROCESS_STATE_FILE = Path(__file__).parent / 'logs' / 'process_state.json'

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
                    await page.fill('input[name="email"]', sp_user)
                    await page.fill('input[name="password"]', sp_pass)
                    await page.click('button[type="submit"]')
                    await page.wait_for_selector('text=Communities', timeout=15000)
                    
                    await page.goto(url, timeout=30000, wait_until="networkidle")
                    await page.wait_for_timeout(1500)
                    
                    # Extract title
                    title_el = await page.query_selector('h1')
                    title = await title_el.inner_text() if title_el else 'Unknown'
                    
                    # Extract address info
                    address = ''
                    city = ''
                    state = ''
                    zip_code = ''
                    
                    address_els = await page.query_selector_all('address p')
                    if len(address_els) >= 1:
                        address = (await address_els[0].inner_text()) or ''
                    if len(address_els) >= 2:
                        location = (await address_els[1].inner_text()) or ''
                        parts = location.split(',')
                        if len(parts) >= 2:
                            city = parts[0].strip()
                            state_zip = parts[1].strip().split()
                            if len(state_zip) > 0:
                                state = state_zip[0]
                            if len(state_zip) > 1:
                                zip_code = state_zip[1]
                    
                    # Extract care types
                    # Switch to attributes page for full detail
                    attrs_url = url.rstrip('/') + '/attributes'
                    await page.goto(attrs_url, wait_until="networkidle", timeout=20000)
                    await page.wait_for_timeout(1000)
                    
                    care_types = []
                    pricing_and_desc = {}
                    
                    try:
                        care_types = await page.evaluate("""
                            () => {
                                const types = [];
                                const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                                
                                for (const label of labels) {
                                    const textEl = label.querySelector("div.ml-2");
                                    const input = label.querySelector('input[type="checkbox"]');
                                    
                                    if (!textEl || !input) continue;
                                    if (!input.checked) continue;
                                    
                                    const name = (textEl.textContent || "").trim();
                                    if (name) types.push(name);
                                }
                                
                                return types;
                            }
                        """)
                    except Exception:
                        care_types = []
                    
                    try:
                        pricing_and_desc = await page.evaluate("""
                            () => {
                                const result = {};
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
                    except Exception:
                        pricing_and_desc = {}
                    
                    # Extract featured image (best-effort from main page)
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    await page.wait_for_timeout(500)
                    featured_image = ''
                    img_el = await page.query_selector("img")
                    if img_el:
                        src = await img_el.get_attribute('src')
                        if src:
                            if src.startswith('/api/files/'):
                                featured_image = f"https://placement-crm-cdn.s3.us-west-2.amazonaws.com{src}"
                            else:
                                featured_image = src if src.startswith('http') else f"https://app.seniorplace.com{src}"
                    
                    await browser.close()
                    
                    return {
                        'title': title.strip(),
                        'address': address.strip(),
                        'city': city.strip(),
                        'state': state.strip(),
                        'zip': zip_code.strip(),
                        'care_types': ', '.join(care_types) if care_types else '',
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

