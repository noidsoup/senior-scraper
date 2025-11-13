#!/usr/bin/env python3
"""
Send Monthly Update Report via Email
Reads the latest update summary and sends a formatted email report
"""

import json
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime


def find_latest_summary():
    """Find the most recent update summary file"""
    updates_dir = Path("monthly_updates")
    
    if not updates_dir.exists():
        return None
    
    summary_files = list(updates_dir.glob("*/update_summary_*.json"))
    
    if not summary_files:
        return None
    
    # Sort by modification time, most recent first
    summary_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return summary_files[0]


def load_summary(summary_file):
    """Load summary JSON"""
    with open(summary_file, 'r') as f:
        return json.load(f)


def format_html_report(summary):
    """Generate HTML email report"""
    stats = summary['stats']
    timestamp = summary['timestamp']
    
    # Parse timestamp
    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
    date_str = dt.strftime("%B %d, %Y at %I:%M %p")
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .stats {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        .stat-row:last-child {{
            border-bottom: none;
        }}
        .stat-label {{
            font-weight: 500;
            color: #555;
        }}
        .stat-value {{
            font-weight: 700;
            color: #667eea;
            font-size: 18px;
        }}
        .highlight {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
        }}
        .footer {{
            text-align: center;
            color: #888;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
        .action-needed {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }}
        .action-needed h3 {{
            margin-top: 0;
            color: #856404;
        }}
        .action-needed ul {{
            margin-bottom: 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Monthly Update Report</h1>
        <p>{date_str}</p>
    </div>
    
    <div class="stats">
        <h2 style="margin-top: 0; color: #333;">Update Statistics</h2>
        
        <div class="stat-row">
            <span class="stat-label">🆕 New Listings Found</span>
            <span class="stat-value">{stats['new_listings_found']}</span>
        </div>
        
        <div class="stat-row">
            <span class="stat-label">🔄 Listings Updated</span>
            <span class="stat-value">{stats['listings_updated']}</span>
        </div>
        
        <div class="stat-row">
            <span class="stat-label">💰 Pricing Updates</span>
            <span class="stat-value">{stats['pricing_updates']}</span>
        </div>
        
        <div class="stat-row">
            <span class="stat-label">🏥 Care Type Updates</span>
            <span class="stat-value">{stats['care_type_updates']}</span>
        </div>
        
        <div class="stat-row">
            <span class="stat-label">📋 Total Processed</span>
            <span class="stat-value">{stats['total_processed']}</span>
        </div>
        
        <div class="stat-row">
            <span class="stat-label">❌ Failed Scrapes</span>
            <span class="stat-value">{stats['failed_scrapes']}</span>
        </div>
    </div>
"""
    
    # Action needed section
    if stats['new_listings_found'] > 0 or stats['listings_updated'] > 0:
        html += """
    <div class="action-needed">
        <h3>⚠️ Action Required</h3>
        <p>New data is ready for WordPress import:</p>
        <ul>
"""
        if stats['new_listings_found'] > 0:
            html += f"            <li><strong>{stats['new_listings_found']} new listings</strong> - Import via WordPress All Import</li>\n"
        
        if stats['listings_updated'] > 0:
            html += f"            <li><strong>{stats['listings_updated']} existing listings</strong> need updates</li>\n"
        
        html += """
        </ul>
        <p>Import files are available in: <code>monthly_updates/[timestamp]/</code></p>
    </div>
"""
    else:
        html += """
    <div class="highlight success">
        <p><strong>✅ All listings are up to date!</strong></p>
        <p>No new listings found and no updates needed.</p>
    </div>
"""
    
    html += """
    <div class="footer">
        <p>Automated Monthly Update System</p>
        <p>A Place For Seniors CMS</p>
    </div>
</body>
</html>
"""
    
    return html


def send_email(to_email, from_email, smtp_server, smtp_port, smtp_user, smtp_password, summary):
    """Send email report"""
    
    # Create message
    msg = MIMEMultipart('alternative')
    
    stats = summary['stats']
    if stats['new_listings_found'] > 0 or stats['listings_updated'] > 0:
        subject = f"📊 Monthly Update: {stats['new_listings_found']} New, {stats['listings_updated']} Updated"
    else:
        subject = "✅ Monthly Update: All Up to Date"
    
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    
    # Plain text version
    text = f"""
Monthly Update Report
{datetime.now().strftime("%B %d, %Y")}

Statistics:
-----------
New Listings: {stats['new_listings_found']}
Updated Listings: {stats['listings_updated']}
Pricing Updates: {stats['pricing_updates']}
Care Type Updates: {stats['care_type_updates']}
Total Processed: {stats['total_processed']}
Failed Scrapes: {stats['failed_scrapes']}

"""
    
    if stats['new_listings_found'] > 0 or stats['listings_updated'] > 0:
        text += "\nAction Required:\n"
        text += f"- Import {stats['new_listings_found']} new listings\n"
        text += f"- Update {stats['listings_updated']} existing listings\n"
        text += "\nImport files available in: monthly_updates/[timestamp]/\n"
    else:
        text += "\nAll listings are up to date!\n"
    
    # Attach both versions
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(format_html_report(summary), 'html')
    
    msg.attach(part1)
    msg.attach(part2)
    
    # Send email
    print(f"Sending report to {to_email}...")
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    
    print("✅ Report sent successfully!")


def main():
    parser = argparse.ArgumentParser(description="Send monthly update report via email")
    parser.add_argument('--to', required=True, help='Recipient email address')
    parser.add_argument('--from', dest='from_email', required=True, help='Sender email address')
    parser.add_argument('--smtp-server', default='smtp.gmail.com', help='SMTP server (default: Gmail)')
    parser.add_argument('--smtp-port', type=int, default=587, help='SMTP port (default: 587)')
    parser.add_argument('--smtp-user', help='SMTP username (default: same as --from)')
    parser.add_argument('--smtp-password', required=True, help='SMTP password or app password')
    parser.add_argument('--summary-file', help='Specific summary file (default: latest)')
    
    args = parser.parse_args()
    
    # Find summary file
    if args.summary_file:
        summary_file = Path(args.summary_file)
    else:
        summary_file = find_latest_summary()
    
    if not summary_file or not summary_file.exists():
        print("❌ No summary file found. Run monthly update first.")
        return 1
    
    print(f"📄 Loading summary: {summary_file}")
    summary = load_summary(summary_file)
    
    # Send email
    smtp_user = args.smtp_user or args.from_email
    send_email(
        to_email=args.to,
        from_email=args.from_email,
        smtp_server=args.smtp_server,
        smtp_port=args.smtp_port,
        smtp_user=smtp_user,
        smtp_password=args.smtp_password,
        summary=summary
    )


if __name__ == "__main__":
    exit(main() or 0)

