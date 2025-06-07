#!/bin/bash

# melio-mcp-install.sh - Universal MCP server installer and runner
# Usage: melio-mcp-install.sh <repo_url> <setup_command> <run_command>
# Example: melio-mcp-install.sh "https://github.com/melio/Figma-Context-MCP.git" "npm install && npm run build" "node dist/cli.js"

set -e  # Exit on any error

REPO_URL="$1"
SETUP_COMMAND="$2"
RUN_COMMAND="$3"

#echo "\n🔧 Setting up MCP server from repository: $REPO_URL\n"
#echo "📦 Setup command: $SETUP_COMMAND"
#echo "🚀 Run command: $RUN_COMMAND\n"

if [ $# -ne 3 ]; then
    # Redirect error to stderr, not stdout (to avoid breaking MCP JSON protocol)
    echo "Error: Invalid arguments. Usage: $0 <repo_url> <setup_command> <run_command>" >&2
    exit 1
fi

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
