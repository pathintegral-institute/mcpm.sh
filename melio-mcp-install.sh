#!/bin/bash

# melio-mcp-install.sh - Universal MCP server installer and runner
# Usage: Set environment variables and run the script:
#   export MCP_REPO_URL="https://github.com/user/repo.git"
#   export MCP_SETUP_COMMAND="npm install && npm run build"  
#   export MCP_RUN_COMMAND="node dist/cli.js --stdio"
#   ./melio-mcp-install.sh

set -e  # Exit on any error

# Check for required environment variables
if [ -z "$MCP_REPO_URL" ] || [ -z "$MCP_SETUP_COMMAND" ] || [ -z "$MCP_RUN_COMMAND" ]; then
    echo "Error: Missing required environment variables:" >&2
    echo "  MCP_REPO_URL: $MCP_REPO_URL" >&2
    echo "  MCP_SETUP_COMMAND: $MCP_SETUP_COMMAND" >&2
    echo "  MCP_RUN_COMMAND: $MCP_RUN_COMMAND" >&2
    echo "" >&2
    echo "Usage:" >&2
    echo "  export MCP_REPO_URL=\"https://github.com/user/repo.git\"" >&2
    echo "  export MCP_SETUP_COMMAND=\"npm install && npm run build\"" >&2
    echo "  export MCP_RUN_COMMAND=\"node dist/cli.js --stdio\"" >&2
    echo "  $0" >&2
    exit 1
fi

REPO_URL="$MCP_REPO_URL"
SETUP_COMMAND="$MCP_SETUP_COMMAND"
RUN_COMMAND="$MCP_RUN_COMMAND"

#echo "\n🔧 Setting up MCP server from repository: $REPO_URL\n"
#echo "📦 Setup command: $SETUP_COMMAND"
#echo "🚀 Run command: $RUN_COMMAND\n"

# Extract repo name from URL (last part without .git)
REPO_NAME=$(basename "$REPO_URL" .git)
TARGET_DIR="$HOME/.meliomcp/$REPO_NAME"

# Create base directory
mkdir -p "$HOME/.meliomcp"

# Clone repository if it doesn't exist (redirect output to stderr)
if [ ! -d "$TARGET_DIR/.git" ]; then
    git clone "$REPO_URL" "$TARGET_DIR" >&2
fi

# Change to target directory
cd "$TARGET_DIR"

# Run setup command if dependencies aren't installed (redirect output to stderr)
if [ ! -d "node_modules" ] && [ ! -d ".venv" ] && [ ! -f ".setup_complete" ]; then
    eval "$SETUP_COMMAND" >&2
    # Create marker file to indicate setup is complete
    touch ".setup_complete"
fi

# Run the server
#echo "🚀 Starting server: $RUN_COMMAND"
eval "$RUN_COMMAND"
