#!/usr/bin/env php
<?php
/**
 * WP CLI script to update location taxonomy terms from CSV
 *
 * Usage: wp eval-file update_locations_wpcli.php --city="City Name" --description="Description text"
 * Or: wp eval-file update_locations_wpcli.php --csv=locations.csv
 */

function update_location_description($city_name, $description) {
    // Find term by name
    $term = get_term_by('name', $city_name, 'location');

    if (!$term) {
        WP_CLI::error("Location term not found: $city_name");
        return false;
    }

    // Update the description
    $updated = wp_update_term($term->term_id, 'location', array(
        'description' => $description
    ));

    if (is_wp_error($updated)) {
        WP_CLI::error("Failed to update $city_name: " . $updated->get_error_message());
        return false;
    }

    WP_CLI::success("Updated location: $city_name");
    return true;
}

function bulk_update_from_csv($csv_file) {
    if (!file_exists($csv_file)) {
        WP_CLI::error("CSV file not found: $csv_file");
        return;
    }

    $handle = fopen($csv_file, 'r');
    if (!$handle) {
        WP_CLI::error("Could not open CSV file: $csv_file");
        return;
    }

    // Skip header
    fgetcsv($handle);

    $updated = 0;
    $skipped = 0;

    while (($row = fgetcsv($handle)) !== FALSE) {
        $city_name = trim($row[0]); // City column
        $description = trim($row[2]); // Description column

        if (empty($city_name) || empty($description)) {
            $skipped++;
            continue;
        }

        // Check if term exists and needs updating
        $term = get_term_by('name', $city_name, 'location');
        if ($term && empty($term->description)) {
            if (update_location_description($city_name, $description)) {
                $updated++;
            }
        } else {
            $skipped++;
        }

        // Small delay to be respectful
        usleep(100000); // 0.1 seconds
    }

    fclose($handle);

    WP_CLI::success("Bulk update complete: $updated updated, $skipped skipped");
}

// Check if running via WP CLI
if (!defined('WP_CLI')) {
    echo "This script must be run via WP CLI: wp eval-file update_locations_wpcli.php\n";
    exit(1);
}

// Get command line arguments
$args = $GLOBALS['argv'];
$city = '';
$description = '';
$csv_file = '';

foreach ($args as $arg) {
    if (strpos($arg, '--city=') === 0) {
        $city = str_replace('--city=', '', $arg);
        $city = str_replace('"', '', $city); // Remove quotes
    }
    if (strpos($arg, '--description=') === 0) {
        $description = str_replace('--description=', '', $arg);
        $description = str_replace('"', '', $description); // Remove quotes
    }
    if (strpos($arg, '--csv=') === 0) {
        $csv_file = str_replace('--csv=', '', $arg);
    }
}

// Execute based on provided arguments
if (!empty($csv_file)) {
    bulk_update_from_csv($csv_file);
} elseif (!empty($city) && !empty($description)) {
    update_location_description($city, $description);
} else {
    WP_CLI::error("Usage: wp eval-file update_locations_wpcli.php --city='City Name' --description='Description'");
    WP_CLI::error("Or: wp eval-file update_locations_wpcli.php --csv=locations.csv");
    exit(1);
}
?>
