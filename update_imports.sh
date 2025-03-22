#!/bin/bash
# Script to update all Python import statements from mcpm to mcp

# Update import statements in all Python files in src/mcp
find src/mcp -name "*.py" -type f -exec sed -i '' 's/from mcpm\./from mcp\./g' {} \;
find src/mcp -name "*.py" -type f -exec sed -i '' 's/import mcpm\./import mcp\./g' {} \;

# Update sys.path.insert line in test_cli.py
sed -i '' 's/from mcpm.cli/from mcp.cli/g' test_cli.py

# Update pyproject.toml entries for package directory
sed -i '' 's/"src\/mcpm"/"src\/mcp"/g' pyproject.toml

# Update the CLI entry point
sed -i '' 's/mcp = "mcpm.cli:main"/mcp = "mcp.cli:main"/g' pyproject.toml

echo "Updated all imports from mcpm to mcp"
