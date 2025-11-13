<?php
/**
 * WordPress duplicate deletion script
 * Upload this to your WordPress site and run via browser or command line
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    require_once('../wp-config.php');
}

$duplicate_ids = [13314,11011,10634,10636,13965,10897,13586,12706,9000,14251,10670,14773,13751,9789,10434,10436,10312,8781,10702,14678,13399,10993,7409,10353,10356,12661,14458];

echo "Deleting " . count($duplicate_ids) . " duplicate listings...\n";

foreach ($duplicate_ids as $post_id) {
    $result = wp_delete_post($post_id, true); // true = force delete, skip trash
    
    if ($result) {
        echo "✓ Deleted post ID: $post_id\n";
    } else {
        echo "✗ Failed to delete post ID: $post_id\n";
    }
}

echo "Deletion complete!\n";
?>