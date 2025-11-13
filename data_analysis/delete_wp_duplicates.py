#!/usr/bin/env python3
"""
WordPress duplicate deletion scripts
Choose your method based on your WordPress setup
"""

import pandas as pd

def create_deletion_scripts():
    # Read the deleted IDs
    deleted_df = pd.read_csv('organized_csvs/TRUE_DUPLICATES_DELETED_IDS.csv')
    deleted_ids = deleted_df['Deleted_ID'].tolist()
    
    print(f"Creating deletion scripts for {len(deleted_ids)} duplicate listings...")
    
    # Method 1: Direct SQL DELETE statements
    sql_deletes = []
    sql_deletes.append("-- WordPress SQL DELETE statements for duplicate listings")
    sql_deletes.append("-- BACKUP YOUR DATABASE FIRST!")
    sql_deletes.append("")
    
    for post_id in deleted_ids:
        sql_deletes.extend([
            f"-- Delete post ID {post_id}",
            f"DELETE FROM wp_posts WHERE ID = {post_id};",
            f"DELETE FROM wp_postmeta WHERE post_id = {post_id};",
            f"DELETE FROM wp_term_relationships WHERE object_id = {post_id};",
            ""
        ])
    
    # Save SQL script
    with open('organized_csvs/DELETE_WORDPRESS_DUPLICATES.sql', 'w') as f:
        f.write('\\n'.join(sql_deletes))
    
    # Method 2: WordPress WP-CLI commands
    wp_cli_commands = []
    wp_cli_commands.append("#!/bin/bash")
    wp_cli_commands.append("# WordPress WP-CLI deletion commands")
    wp_cli_commands.append("# Run this from your WordPress root directory")
    wp_cli_commands.append("")
    
    for post_id in deleted_ids:
        wp_cli_commands.append(f"wp post delete {post_id} --force")
    
    # Save WP-CLI script
    with open('organized_csvs/DELETE_WORDPRESS_DUPLICATES_WPCLI.sh', 'w') as f:
        f.write('\\n'.join(wp_cli_commands))
    
    # Method 3: WordPress REST API / PHP script
    php_script = '''<?php
/**
 * WordPress duplicate deletion script
 * Upload this to your WordPress site and run via browser or command line
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    require_once('../wp-config.php');
}

$duplicate_ids = [''' + ','.join(map(str, deleted_ids)) + '''];

echo "Deleting " . count($duplicate_ids) . " duplicate listings...\\n";

foreach ($duplicate_ids as $post_id) {
    $result = wp_delete_post($post_id, true); // true = force delete, skip trash
    
    if ($result) {
        echo "✓ Deleted post ID: $post_id\\n";
    } else {
        echo "✗ Failed to delete post ID: $post_id\\n";
    }
}

echo "Deletion complete!\\n";
?>'''
    
    # Save PHP script
    with open('organized_csvs/DELETE_WORDPRESS_DUPLICATES.php', 'w') as f:
        f.write(php_script)
    
    # Method 4: WP All Import CSV for deletion
    deletion_csv_data = []
    for post_id in deleted_ids:
        deletion_csv_data.append({
            'ID': post_id,
            'Status': 'trash'
        })
    
    deletion_df = pd.DataFrame(deletion_csv_data)
    deletion_df.to_csv('organized_csvs/DELETE_DUPLICATES_WP_IMPORT.csv', index=False)
    
    # Create instructions
    instructions = '''
# WordPress Duplicate Deletion Instructions

You have 4 options to delete the 27 duplicate listings from WordPress:

## Option 1: WP All Import (EASIEST)
1. File: DELETE_DUPLICATES_WP_IMPORT.csv
2. In WordPress Admin → All Import → Create New Import
3. Upload the CSV file
4. Map: ID → Post ID, Status → Post Status
5. Set to "Update existing posts" matching by ID
6. Run import - this will move all duplicates to trash

## Option 2: WP-CLI (COMMAND LINE)
1. File: DELETE_WORDPRESS_DUPLICATES_WPCLI.sh
2. Upload to your WordPress root directory
3. SSH to your server
4. Run: chmod +x DELETE_WORDPRESS_DUPLICATES_WPCLI.sh
5. Run: ./DELETE_WORDPRESS_DUPLICATES_WPCLI.sh

## Option 3: Direct SQL (ADVANCED - BACKUP FIRST!)
1. File: DELETE_WORDPRESS_DUPLICATES.sql
2. Backup your WordPress database first!
3. Run SQL commands in phpMyAdmin or similar
4. This permanently deletes posts and all associated data

## Option 4: PHP Script (UPLOAD TO WP)
1. File: DELETE_WORDPRESS_DUPLICATES.php
2. Upload to your WordPress site
3. Visit the file in browser or run via PHP CLI
4. Permanently deletes the duplicate posts

## RECOMMENDATION: Use Option 1 (WP All Import)
- Safest method (moves to trash instead of permanent deletion)
- Easy to undo if needed
- Uses familiar WordPress interface
- No server access required

## IDs to be deleted:
''' + ', '.join(map(str, deleted_ids))
    
    with open('organized_csvs/WORDPRESS_DELETION_INSTRUCTIONS.txt', 'w') as f:
        f.write(instructions)
    
    print("\\nFiles created:")
    print("  📄 DELETE_DUPLICATES_WP_IMPORT.csv - For WP All Import (RECOMMENDED)")
    print("  🖥️  DELETE_WORDPRESS_DUPLICATES_WPCLI.sh - WP-CLI commands") 
    print("  💾 DELETE_WORDPRESS_DUPLICATES.sql - Direct SQL")
    print("  🐘 DELETE_WORDPRESS_DUPLICATES.php - PHP script")
    print("  📋 WORDPRESS_DELETION_INSTRUCTIONS.txt - Full instructions")
    
    print(f"\\n✅ Ready to delete {len(deleted_ids)} duplicate listings from WordPress!")
    print("\\n🚨 RECOMMENDATION: Use WP All Import method (safest)")
    print("   → Upload DELETE_DUPLICATES_WP_IMPORT.csv via WP All Import")
    print("   → Map ID to Post ID, Status to Post Status") 
    print("   → This moves duplicates to trash (recoverable)")

if __name__ == "__main__":
    create_deletion_scripts()
