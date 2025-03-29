#!/bin/bash

# Function to display error messages
error_exit() {
  echo "❌ $1"
  exit 1
}

# Function to display status messages
status_message() {
  echo -e "🔄 $1"
}

# Set up the directory structure and copy necessary files
setup_directories() {
  TARGET_DIR="$1"
  
  # Create API and registry directories if they don't exist
  mkdir -p "$TARGET_DIR/api/servers"
  
  # Copy registry files to target directory
  status_message "Copying registry files..."
  cp -r mcp-registry/* "$TARGET_DIR/registry/"
  
  # Create API endpoints for server json files
  status_message "Creating API endpoints..."
  find mcp-registry/servers -name "*.json" -type f | while read server_file; do
    server_name=$(basename "$server_file" .json)
    echo "  - Processing $server_name..."
    cp "$server_file" "$TARGET_DIR/api/servers/$server_name.json"
  done
}

# Use Python script to generate servers.json and stars.json
generate_server_data() {
  TARGET_DIR="$1"
  
  # Check if stars.json already exists
  if [ -f "$TARGET_DIR/api/stars.json" ]; then
    status_message "Using existing stars.json file..."
    SKIP_STARS="--skip-stars"
  else
    status_message "Processing server JSON data and fetching GitHub stars..."
    SKIP_STARS=""
  fi
  
  # Get the absolute path to the script directory
  SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
  if python3 "$SCRIPT_DIR/prepare.py" "$(pwd)/mcp-registry" "$TARGET_DIR" $SKIP_STARS; then
    echo "  ✓ Successfully generated servers.json and stars.json"
  else
    error_exit "Failed to process server data with Python script"
  fi
}

# Main function to prepare the site
prepare_site() {
  TARGET_DIR="$1"
  
  # Setup directories and copy files
  setup_directories "$TARGET_DIR"
  
  # Generate servers.json and stars.json using Python script
  generate_server_data "$TARGET_DIR"
  
  echo -e "✅ Preparation complete!\n"
}

# If this script is executed directly, run the preparation
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if [ -z "$1" ]; then
    error_exit "Target directory not specified. Usage: $0 <target_directory>"
  fi
  
  prepare_site "$1"
fi
