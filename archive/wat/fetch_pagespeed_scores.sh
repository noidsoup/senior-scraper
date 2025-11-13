#!/bin/bash

# List of URLs to analyze
urls=(
  "https://postscript.io/"
  "https://postscript.io/marketing"
  "https://postscript.io/ai"
  "https://postscript.io/cashback"
  "https://postscript.io/sales"
  "https://postscript.io/postscript-plus"
  "https://postscript.io/features"
  "https://postscript.io/infinity-testing"
  "https://postscript.io/customer-service"
  "https://postscript.io/deliverability"
  "https://postscript.io/onsite"
  "https://postscript.io/sms-compliance"
  "https://postscript.io/blog/whats-new-in-postscript-february-2025-product-updates"
)

# API key
api_key="AIzaSyArnXV9FSwhdPb_PE0IBjMwbudKD_PfPxs"

# Loop through each URL and fetch scores for both desktop and mobile
for url in "${urls[@]}"; do
  # Extract the last part of the URL for file naming
  name=$(echo $url | awk -F/ '{print $NF}')
  if [ -z "$name" ]; then
    name="home"
  fi

  # Fetch desktop score
  curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=$url&strategy=desktop&key=$api_key" -o "pagespeed_${name}_desktop.json"

  # Fetch mobile score
  curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=$url&strategy=mobile&key=$api_key" -o "pagespeed_${name}_mobile.json"
done