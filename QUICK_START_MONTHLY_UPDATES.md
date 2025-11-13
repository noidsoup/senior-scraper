# 🚀 Quick Start - Monthly Updates

Get your monthly update system running in 5 minutes!

## Step 1: Install Dependencies (2 min)

```bash
cd /Users/nicholas/Repos/senior-scrapr

# Install Python packages
pip3 install playwright requests aiohttp

# Install browser for Playwright
python3 -m playwright install chromium
```

## Step 2: Setup Environment (1 min)

Copy the example config and edit with your credentials:

```bash
cp monthly_update_config.example.env .env
nano .env  # or use your favorite editor
```

**Required variables:**
- `WP_PASSWORD` - Your WordPress application password
- `SP_PASSWORD` - Senior Place password (set in your .env)

**Optional but recommended:**
- `NOTIFICATION_EMAIL` - For email reports
- `SMTP_PASSWORD` - Gmail app password for sending emails

## Step 3: Test the System (1 min)

Run the validation script:

```bash
python3 test_monthly_update.py
```

This checks:
- ✅ All dependencies installed
- ✅ Environment variables set
- ✅ WordPress API working
- ✅ Senior Place login working

## Step 4: Test Run (Manual)

Test with a single state (Arizona) first:

```bash
source .env  # Load environment variables

python3 monthly_update_orchestrator.py \
    --full-update \
    --states AZ \
    --wp-password "$WP_PASSWORD" \
    --sp-password "$SP_PASSWORD"
```

This will:
1. Fetch current WordPress listings
2. Scrape Arizona from Senior Place
3. Compare and find new/updated listings
4. Generate CSVs in `monthly_updates/[timestamp]/`

Expected time: ~5-10 minutes for Arizona

## Step 5: Setup Automation (1 min)

Install the cron job to run automatically:

```bash
./setup_monthly_scheduler.sh
```

This creates:
- `run_monthly_update.sh` - Wrapper script with logging
- Cron job suggestion (you need to install it)

Install cron job:

```bash
(crontab -l 2>/dev/null; echo "0 2 1 * * /Users/nicholas/Repos/senior-scrapr/run_monthly_update.sh") | crontab -
```

Verify it's installed:

```bash
crontab -l
```

## What Happens Next?

### Automatic Monthly Updates

On the 1st of each month at 2am, the system will:

1. 🔍 **Scrape active states** from Senior Place (AZ, CA, CO, ID, NM, UT)
2. 🆕 **Find new listings** not in WordPress
3. 🔄 **Find updated data** for existing listings
4. 💾 **Generate CSVs** ready for import
5. 📧 **Email you a report** (if configured)

### When You Get the Email

1. Open the email - it shows:
   - How many new listings found
   - How many listings need updates
   - Where the CSV files are

2. Go to WordPress Admin → All Import

3. **For new listings:**
   - Upload `new_listings_[timestamp].csv`
   - Map fields as described in email
   - Run import

4. **For updated listings:**
   - Upload `updated_listings_[timestamp].csv`
   - Set unique ID to `ID`
   - Enable "Update existing records"
   - Run import

## Quick Commands Reference

```bash
# Manual test run (single state)
python3 monthly_update_orchestrator.py --full-update --states AZ --wp-password "$WP_PASSWORD"

# Full production run (all states)
./run_monthly_update.sh

# Check recent logs
ls -lt monthly_updates/logs/ | head -5

# View latest log
tail -f monthly_updates/logs/update_*.log

# Send test email report
python3 send_monthly_report.py \
    --to "your-email@example.com" \
    --from "your-email@example.com" \
    --smtp-password "$SMTP_PASSWORD"

# Test system health
python3 test_monthly_update.py

# Check cron status
crontab -l
```

## Troubleshooting

### "WP_PASSWORD not set"

```bash
source .env  # Load variables from .env
# OR
export WP_PASSWORD="your_password"
```

### "WordPress API returns 401"

Your application password is wrong. Get a new one:
1. WordPress Admin → Users → Your Profile
2. Scroll to "Application Passwords"
3. Generate new password
4. Update `.env` file

### "Senior Place login failed"

Check if password changed. Update in `.env`:
```bash
SP_PASSWORD=Hugomax2025!  # or new password
```

### "Cron job not running"

macOS users: Grant Full Disk Access to cron
1. System Preferences → Security & Privacy
2. Privacy → Full Disk Access
3. Add `/usr/sbin/cron`

### "No module named 'playwright'"

```bash
pip3 install playwright requests aiohttp
python3 -m playwright install chromium
```

## States Covered

By default, these states are updated:
- Arizona (AZ)
- California (CA)
- Colorado (CO)
- Idaho (ID)
- New Mexico (NM)
- Utah (UT)

## Performance

Approximate processing times:
- **Arizona**: ~10 minutes (~4,800 listings)
- **California**: ~60 minutes (~26,000 listings)
- **Other states**: ~5-15 minutes each
- **Full run (all states)**: ~2-3 hours

The system uses rate limiting to be respectful to Senior Place servers.

## Support

If something's not working:

1. ✅ Run `python3 test_monthly_update.py` to diagnose
2. 📋 Check logs in `monthly_updates/logs/`
3. 🧪 Test individual components:
   ```bash
   # Test WordPress API
   curl -u "$WP_USERNAME:$WP_PASSWORD" \
     "https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2/listing?per_page=1"
   
   # Test Senior Place scraper
   python3 scrapers_active/scrape_live_senior_place_data.py --limit 5
   ```

## Success! 🎉

You're all set! Your system will now:
- ✅ Automatically find new listings every month
- ✅ Update pricing and care types for existing listings
- ✅ Generate WordPress-ready import files
- ✅ Email you detailed reports

Just remember to import the CSVs when you get the monthly notification email!

