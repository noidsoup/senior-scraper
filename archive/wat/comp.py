import os
import json
from tabulate import tabulate

# Directory containing JSON files
json_dir = '.'

# List to store extracted data
data = []

# Iterate over files in the directory
for filename in os.listdir(json_dir):
    if filename.endswith('.json'):
        filepath = os.path.join(json_dir, filename)
        with open(filepath, 'r') as file:
            content = json.load(file)
            # Extract the URL and score
            url = content.get('id', 'N/A')
            score = content.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', 'N/A')
            # Determine strategy based on filename
            strategy = 'Desktop' if 'desktop' in filename else 'Mobile'
            # Append to data list
            data.append([filename, url, strategy, score])

# Print the table
print(tabulate(data, headers=['File', 'URL', 'Strategy', 'Score']))