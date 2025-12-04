#!/usr/bin/env python3
"""
Test Monthly Update System
Validates all components before running full update
"""

import asyncio
import sys
import os
from pathlib import Path
import requests


class UpdateSystemTester:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.warnings = []
        
    def test(self, name: str, condition: bool, error_msg: str = ""):
        """Run a test and track results"""
        if condition:
            print(f"✅ {name}")
            self.tests_passed += 1
            return True
        else:
            print(f"❌ {name}")
            if error_msg:
                print(f"   → {error_msg}")
            self.tests_failed += 1
            return False
    
    def warn(self, message: str):
        """Add a warning"""
        print(f"⚠️  {message}")
        self.warnings.append(message)
    
    def test_python_dependencies(self):
        """Test if required Python packages are installed"""
        print("\n📦 Testing Python Dependencies...")
        
        try:
            import playwright
            self.test("Playwright installed", True)
        except ImportError:
            self.test("Playwright installed", False, 
                     "Install with: pip3 install playwright && python3 -m playwright install")
        
        try:
            import requests
            self.test("Requests installed", True)
        except ImportError:
            self.test("Requests installed", False,
                     "Install with: pip3 install requests")
        
        try:
            import aiohttp
            self.test("Aiohttp installed", True)
        except ImportError:
            self.test("Aiohttp installed", False,
                     "Install with: pip3 install aiohttp")
    
    def test_environment_variables(self):
        """Test if required environment variables are set"""
        print("\n🔐 Testing Environment Variables...")
        
        wp_pass = os.getenv('WP_PASSWORD')
        self.test("WP_PASSWORD set", bool(wp_pass),
                 "Set with: export WP_PASSWORD='your_password'")
        
        sp_pass = os.getenv('SP_PASSWORD')
        self.test("SP_PASSWORD set", bool(sp_pass),
                 "Set with: export SP_PASSWORD='your_seniorplace_password'")
        
        email = os.getenv('NOTIFICATION_EMAIL')
        if not email:
            self.warn("NOTIFICATION_EMAIL not set (email reports disabled)")
        else:
            self.test("NOTIFICATION_EMAIL set", True)
    
    def test_file_structure(self):
        """Test if required files and directories exist"""
        print("\n📁 Testing File Structure...")
        
        # Get the repo root (parent of monthly_scrapers or current dir)
        current = Path(__file__).parent
        root = current.parent if current.name == 'monthly_scrapers' else current
        
        required_files = [
            root / 'monthly_scrapers' / 'monthly_update_orchestrator.py',
            root / 'monthly_scrapers' / 'send_monthly_report.py',
            root / 'scrapers_active' / 'scrape_live_senior_place_data.py',
            root / 'scrapers_active' / 'update_prices_from_seniorplace_export.py',
        ]
        
        for file in required_files:
            file_path = Path(file)
            self.test(f"{file.name} exists", file_path.exists(),
                     f"File not found: {file}")
        
        # Check if directories can be created
        test_dir = Path("monthly_updates/test")
        try:
            test_dir.mkdir(parents=True, exist_ok=True)
            self.test("Can create output directories", True)
            test_dir.rmdir()
            test_dir.parent.rmdir() if not list(test_dir.parent.iterdir()) else None
        except Exception as e:
            self.test("Can create output directories", False, str(e))
    
    def test_wordpress_api(self):
        """Test WordPress API connectivity"""
        print("\n🌐 Testing WordPress API...")
        
        wp_url = os.getenv('WP_URL', 'https://aplaceforseniorscms.kinsta.cloud')
        wp_user = os.getenv('WP_USERNAME', 'nicholas_editor')
        wp_pass = os.getenv('WP_PASSWORD')
        
        if not wp_pass:
            self.test("WordPress API reachable", False,
                     "WP_PASSWORD not set, cannot test API")
            return
        
        try:
            # Test basic API endpoint
            response = requests.get(
                f"{wp_url}/wp-json/wp/v2",
                timeout=10
            )
            self.test("WordPress site reachable", response.status_code == 200)
            
            # Test authenticated endpoint
            response = requests.get(
                f"{wp_url}/wp-json/wp/v2/listing?per_page=1",
                auth=(wp_user, wp_pass),
                timeout=10
            )
            
            if response.status_code == 200:
                self.test("WordPress authentication works", True)
                data = response.json()
                print(f"   → Found {len(data)} listing(s)")
            elif response.status_code == 401:
                self.test("WordPress authentication works", False,
                         "Invalid credentials or app password")
            else:
                self.test("WordPress authentication works", False,
                         f"HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.test("WordPress site reachable", False,
                     "Cannot connect to WordPress site")
        except Exception as e:
            self.test("WordPress API test", False, str(e))
    
    async def test_senior_place_login(self):
        """Test Senior Place login"""
        print("\n🔑 Testing Senior Place Login...")
        
        sp_user = os.getenv('SP_USERNAME', 'allison@aplaceforseniors.org')
        sp_pass = os.getenv('SP_PASSWORD')
        if not sp_pass:
            self.test("Senior Place login successful", False,
                     "SP_PASSWORD not set, cannot test login")
            return
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                try:
                    await page.goto("https://app.seniorplace.com/login", timeout=15000)
                    await page.fill('input[name="email"]', sp_user)
                    await page.fill('input[name="password"]', sp_pass)
                    await page.click('button[type="submit"]')
                    
                    # Wait for successful login
                    await page.wait_for_selector('text=Communities', timeout=10000)
                    
                    self.test("Senior Place login successful", True)
                    
                except Exception as e:
                    self.test("Senior Place login successful", False,
                             "Invalid credentials or site changed")
                finally:
                    await browser.close()
                    
        except ImportError:
            self.test("Senior Place login", False,
                     "Playwright not installed")
        except Exception as e:
            self.test("Senior Place login", False, str(e))
    
    def test_cron_setup(self):
        """Check if cron job is configured"""
        print("\n⏰ Testing Cron Configuration...")
        
        # Check if run script is executable
        run_script = Path("run_monthly_update.sh")
        if run_script.exists():
            is_executable = os.access(run_script, os.X_OK)
            self.test("run_monthly_update.sh is executable", is_executable,
                     "Make executable with: chmod +x run_monthly_update.sh")
        
        # Try to check crontab (may fail on some systems)
        try:
            import subprocess
            result = subprocess.run(['crontab', '-l'], 
                                   capture_output=True, 
                                   text=True,
                                   timeout=5)
            
            if 'run_monthly_update.sh' in result.stdout:
                self.test("Cron job installed", True)
            else:
                self.warn("Cron job not found in crontab")
                print("   → Install with: (crontab -l; echo '0 2 1 * * /path/to/run_monthly_update.sh') | crontab -")
                
        except Exception:
            self.warn("Could not check crontab (may require manual verification)")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print("=" * 60)
        
        if self.tests_failed == 0 and len(self.warnings) == 0:
            print("\n🎉 All tests passed! System is ready to run.")
            print("\nNext steps:")
            print("  1. Run test update: python3 monthly_update_orchestrator.py --full-update --states AZ --wp-password $WP_PASSWORD")
            print("  2. Setup cron: ./setup_monthly_scheduler.sh")
            return 0
        elif self.tests_failed == 0:
            print("\n✅ All required tests passed (warnings can be ignored)")
            print("\nYou can proceed with:")
            print("  python3 monthly_update_orchestrator.py --full-update --wp-password $WP_PASSWORD")
            return 0
        else:
            print("\n❌ Some tests failed. Fix issues before running updates.")
            return 1


async def main():
    """Run all tests"""
    # Set UTF-8 encoding for Windows console
    if os.name == 'nt':
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    print("🧪 MONTHLY UPDATE SYSTEM - TESTING")
    print("=" * 60)
    
    tester = UpdateSystemTester()
    
    # Run all tests
    tester.test_python_dependencies()
    tester.test_environment_variables()
    tester.test_file_structure()
    tester.test_wordpress_api()
    await tester.test_senior_place_login()
    tester.test_cron_setup()
    
    # Print summary
    return tester.print_summary()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)

