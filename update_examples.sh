#!/bin/bash
# Script to update command examples from mcpm to mcp

# Update command examples in all command files
find src/mcpm/commands -name "*.py" -type f -exec sed -i '' 's/mcpm \([a-zA-Z_-]*\)/mcp \1/g' {} \;

# Update the reference to the config directory in install.py
sed -i '' 's/~\/.config\/mcpm/~\/.config\/mcp/g' src/mcpm/commands/install.py

# Update the remaining "Use 'mcpm" references
find src/mcpm/commands -name "*.py" -type f -exec sed -i '' "s/Use 'mcpm/Use 'mcp/g" {} \;

echo "Updated command examples from mcpm to mcp"
