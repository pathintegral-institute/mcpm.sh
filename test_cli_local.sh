#!/bin/bash

# MCPM Local Development CLI Helper
# This script runs the CLI using local server data from mcp-registry/servers

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to local servers.json file
LOCAL_SERVERS_JSON="file://${PROJECT_DIR}/_dev/api/servers.json"

# Check if _dev/api/servers.json exists
if [ ! -f "${PROJECT_DIR}/_dev/api/servers.json" ]; then
    echo -e "${BLUE}Local servers.json not found. Generating it now...${NC}"
    
    # Run prepare script to generate local servers.json
    if ! ./scripts/prepare.sh _dev; then
        echo "❌ Failed to generate local servers.json file"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Local servers.json generated successfully!${NC}"
fi

# Run the CLI with local repository URL
echo -e "${BLUE}Running MCPM CLI with local server data...${NC}"
echo -e "${BLUE}Repository URL: ${LOCAL_SERVERS_JSON}${NC}"
echo ""

MCPM_REPO_URL="${LOCAL_SERVERS_JSON}" python3 test_cli.py "$@" 