#!/bin/sh
set -e

echo "Replacing __SERVER_URL__ with ${SERVER_URL} in static assets..."
# Ensure SERVER_URL is set, or provide a default if appropriate for your use case
if [ -z "${SERVER_URL}" ]; then
  echo "Error: SERVER_URL environment variable is not set."
  exit 1
fi
sed -i "s|__SERVER_URL__|${SERVER_URL}|g" /app/web_assets/index.html
sed -i "s|__SERVER_URL__|${SERVER_URL}|g" /app/web_assets/common.js
echo "Replacement complete."

echo "Executing command: $@"
exec "$@"