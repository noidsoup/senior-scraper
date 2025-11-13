# 📊 Monthly Update System - Overview

## What This System Does

Your senior living listings website now has a **fully automated update system** that runs every 30 days to keep your data fresh and comprehensive.

## 🎯 Core Capabilities

### 1. Automatic New Listing Discovery

- Scrapes Senior Place for all configured states
- Compares with your WordPress database
- Identifies listings that don't exist on your site yet
- Generates WordPress import file with all details

### 2. Existing Listing Updates

- Checks pricing changes for all listings
- Monitors care type changes
- Detects description updates
- Identifies image quality improvements
- Generates update-only CSV files

### 3. Multi-Source Data Enrichment

- **Primary Source**: Senior Place (pricing, care types, addresses)
- **Secondary Source**: Seniorly (enhanced descriptions, better images)
- **Data Normalization**: Converts all care types to your CMS taxonomy

### 4. Smart Automation

- **Scheduled Execution**: Runs 1st of each month at 2am (configurable)
- **Error Handling**: Continues processing even if some listings fail
- **Checkpoint Logging**: Tracks progress for debugging
- **Email Notifications**: Sends HTML reports with action items

## 📋 Complete File Structure

```
senior-scrapr/
├── 🚀 QUICK_START_MONTHLY_UPDATES.md  ← START HERE (5-minute setup)
├── 📖 MONTHLY_UPDATE_README.md         ← Detailed documentation
├── 📊 SYSTEM_OVERVIEW.md               ← This file
│
├── Core Scripts:
│   ├── monthly_update_orchestrator.py  ← Main orchestration logic
│   ├── send_monthly_report.py          ← Email reporting
│   ├── test_monthly_update.py          ← System validation
│   ├── setup_monthly_scheduler.sh      ← One-time setup
│   └── run_monthly_update.sh           ← Auto-generated cron wrapper
│
├── Active Scrapers:
│   ├── scrapers_active/
│   │   ├── scrape_live_senior_place_data.py     ← Senior Place scraper
│   │   ├── enhanced_seniorly_scraper.py         ← Seniorly scraper
│   │   ├── update_prices_from_seniorplace_export.py
│   │   └── scrape_seniorly_community_types.py
│
├── Configuration:
│   ├── monthly_update_config.example.env  ← Template (copy to .env)
│   └── .env                               ← Your credentials (git-ignored)
│
└── Output (auto-generated):
    └── monthly_updates/
        └── YYYYMMDD_HHMMSS/
            ├── new_listings_*.csv       ← Import to add new listings
            ├── updated_listings_*.csv   ← Import to update existing
            ├── update_summary_*.json    ← Statistics report
            └── logs/
                └── update_*.log         ← Detailed execution log
```

## 🔄 How It Works (Step by Step)

### Automated Process (Every 30 Days)

```
1. TRIGGER
   ↓
   Cron job activates at 2am on 1st of month

2. FETCH CURRENT DATA
   ↓
   WordPress REST API → Get all existing listings
   Store in memory for comparison

3. SCRAPE SENIOR PLACE
   ↓
   For each state (AZ, CA, CO, UT, ID, NM, WY, CT, AR):
   - Login to Senior Place
   - Navigate to state search results
   - Extract all listing cards (title, URL, image)
   - Go to each listing's /attributes page
   - Scrape pricing, care types, amenities

4. COMPARE DATA
   ↓
   For each scraped listing:
   - Check if URL exists in WordPress
   - If NO → Add to NEW LISTINGS
   - If YES → Compare fields:
     - Price changed? → Mark for update
     - Care types changed? → Mark for update

5. GENERATE CSVS
   ↓
   Create two files:
   - new_listings_[timestamp].csv  (ready for import)
   - updated_listings_[timestamp].csv  (ready for update)

6. SEND EMAIL REPORT
   ↓
   HTML email with:
   - Statistics (how many new, how many updated)
   - Action items (what to import)
   - File locations

7. YOU REVIEW & IMPORT
   ↓
   Check email → Import CSVs to WordPress
```

## 📊 Example Monthly Report

```
From: updates@yoursite.com
To: admin@yoursite.com
Subject: 📊 Monthly Update: 127 New, 43 Updated

Monthly Update Report
October 28, 2025

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UPDATE STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆕 New Listings Found:        127
🔄 Listings Updated:           43
💰 Pricing Updates:            38
🏥 Care Type Updates:          12
📋 Total Processed:         4,892
❌ Failed Scrapes:              3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  ACTION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

New data ready for import:

• 127 new listings - Import via WordPress All Import
• 43 existing listings need updates

Import files available in:
monthly_updates/20251028_020000/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 🎛️ Configuration Options

### States to Process

Default: `AZ, CA, CO, UT, ID, NM, WY, CT, AR`

Change in `.env`:

```bash
STATES=AZ,CA,CO,UT,ID,NM,WY,CT,AR
```

Or override via command line:

```bash
python3 monthly_update_orchestrator.py --states AZ CA CO
```

### Schedule Options

**Monthly (recommended):**

```bash
0 2 1 * * /path/to/run_monthly_update.sh
```

**Every 30 days:**

```bash
0 2 */30 * * /path/to/run_monthly_update.sh
```

**Every Sunday (weekly):**

```bash
0 3 * * 0 /path/to/run_monthly_update.sh
```

**15th of month:**

```bash
0 2 15 * * /path/to/run_monthly_update.sh
```

### Email Notifications

Configure in `.env`:

```bash
NOTIFICATION_EMAIL=your-email@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your_gmail_app_password
```

## 📈 Data Quality & Coverage

### Current Coverage

| State       | Listings | Source       | Status    |
| ----------- | -------- | ------------ | --------- |
| Arizona     | ~4,800   | Senior Place | ✅ Active |
| California  | ~26,000  | Senior Place | ✅ Active |
| Colorado    | ~2,000   | Senior Place | ✅ Active |
| Utah        | ~1,500   | Senior Place | ✅ Active |
| Idaho       | ~800     | Senior Place | ✅ Active |
| New Mexico  | ~600     | Senior Place | ✅ Active |
| Wyoming     | ~400     | Senior Place | ✅ Active |
| Connecticut | ~1,200   | Senior Place | ✅ Active |
| Arkansas    | ~1,000   | Senior Place | ✅ Active |

**Total Coverage**: ~38,300 listings across 9 states

### Data Fields Captured

For each listing:

- ✅ Title
- ✅ Full address (street, city, state, zip)
- ✅ Senior Place URL (source attribution)
- ✅ Featured image (high quality)
- ✅ Care types (normalized to CMS taxonomy)
- ✅ Base monthly pricing
- ✅ High-end pricing range
- ✅ Second person fees
- ✅ Care level pricing ranges
- ✅ Medicaid/ALTCS acceptance flags
- ✅ Bedroom pricing (studio, 1BR, 2BR)

## 🔐 Security & Privacy

### Credentials Storage

**DO NOT commit to git:**

- `.env` file (contains passwords)
- `monthly_updates/` directory (contains data)
- `run_monthly_update.sh` (contains paths)

**Git-ignored automatically:**

```
.env
*.env (except *.example.env)
monthly_updates/
run_monthly_update.sh
```

### WordPress Application Passwords

Use application passwords (NOT your real WordPress password):

1. WordPress Admin → Users → Your Profile
2. Scroll to "Application Passwords"
3. Generate password for "Monthly Update System"
4. Copy and save in `.env`

### Senior Place Credentials

Stored in `.env`:

```bash
SP_USERNAME=allison@aplaceforseniors.org
SP_PASSWORD=Hugomax2025!
```

## 🚨 Monitoring & Alerts

### Automatic Monitoring

The system tracks:

- ✅ Successful scrapes
- ❌ Failed scrapes
- 🔄 Listings processed
- 🆕 New listings found
- 💰 Pricing changes detected

### Email Alerts

You receive an email:

- **✅ Success**: When update completes with statistics
- **❌ Failure**: When critical errors occur
- **⚠️ Warning**: When some listings fail but process continues

### Manual Monitoring

Check logs:

```bash
# View latest log
tail -f monthly_updates/logs/update_*.log

# List recent updates
ls -lt monthly_updates/

# View summary JSON
cat monthly_updates/*/update_summary_*.json | jq
```

## 🛠️ Maintenance

### Monthly Tasks (You)

1. **Check email** for update notification
2. **Review CSVs** before importing
3. **Import new listings** via WordPress All Import
4. **Import updates** for existing listings
5. **Verify imports** completed successfully

### System Maintenance (Automatic)

- ✅ Log rotation (keeps last 30 days)
- ✅ Checkpoint cleanup (removes old checkpoints)
- ✅ Error recovery (continues on failures)
- ✅ Rate limiting (respectful to servers)

### Periodic Manual Checks (Quarterly)

1. **Verify cron running**:

   ```bash
   crontab -l
   ```

2. **Check disk space**:

   ```bash
   du -sh monthly_updates/
   ```

3. **Test system health**:

   ```bash
   python3 test_monthly_update.py
   ```

4. **Update credentials** if changed

## 💡 Tips & Best Practices

### 1. Always Test Before Production

```bash
# Test with one state first
python3 monthly_update_orchestrator.py \
    --full-update \
    --states AZ \
    --wp-password "$WP_PASSWORD"
```

### 2. Review Before Importing

- Open CSVs in Excel/Numbers/Google Sheets
- Spot-check random listings
- Verify pricing looks reasonable
- Check care types are normalized

### 3. Import During Low-Traffic Hours

WordPress imports can be slow. Schedule for:

- Late night (2-4am)
- Early morning (6-8am)
- Weekends

### 4. Keep Logs

Don't delete `monthly_updates/` directory:

- Logs help debug issues
- Summaries track trends over time
- CSVs can be re-imported if needed

### 5. Monitor Trends

```bash
# Count new listings per month
grep "new_listings_found" monthly_updates/*/update_summary_*.json

# Track pricing updates
grep "pricing_updates" monthly_updates/*/update_summary_*.json
```

## 🔮 Future Enhancements (Roadmap)

### Phase 2 (Q1 2026)

- [ ] Seniorly integration for non-Senior Place listings
- [ ] AI description rewriting for better SEO
- [ ] Image quality scoring and replacement
- [ ] Automated WordPress import (skip CSV step)

### Phase 3 (Q2 2026)

- [ ] Slack/Discord notifications
- [ ] Real-time updates (webhook-based)
- [ ] Competitor pricing tracking
- [ ] Review monitoring and alerts

### Phase 4 (Q3 2026)

- [ ] Machine learning for listing quality scoring
- [ ] Automated content generation
- [ ] Multi-language support
- [ ] API for third-party integrations

## 📞 Getting Help

### Quick Diagnostics

```bash
# Test entire system
python3 test_monthly_update.py

# Test WordPress connection
curl -u "$WP_USERNAME:$WP_PASSWORD" \
  "$WP_URL/wp-json/wp/v2/listing?per_page=1"

# Test Senior Place scraper
python3 scrapers_active/scrape_live_senior_place_data.py --limit 5
```

### Common Issues

See `MONTHLY_UPDATE_README.md` → Troubleshooting section

### Support Contacts

- System Issues: Check logs first
- WordPress Issues: Check WP All Import plugin
- Senior Place Issues: Verify credentials
- Email Issues: Check Gmail app password

## ✅ You're Ready!

The system is designed to run autonomously. Your only job is:

1. **📧 Check monthly email** (5 minutes)
2. **📥 Import CSVs to WordPress** (10 minutes)
3. **✅ Verify imports** (5 minutes)

**Total time commitment**: ~20 minutes per month

Everything else is automated! 🎉
