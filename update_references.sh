#!/bin/bash
# Script to update references from MCPM to MCP across the project

# Update command file docstrings
find src/mcpm/commands -name "*.py" -type f -exec sed -i '' 's/command for MCPM/command for MCP/g' {} \;
find src/mcpm/commands -name "*.py" -type f -exec sed -i '' 's/commands for MCPM/commands for MCP/g' {} \;
find src/mcpm/commands -name "*.py" -type f -exec sed -i '' 's/MCPM commands package/MCP commands package/g' {} \;

# Update specific references in toggle.py
sed -i '' 's/stored in the MCPM configuration/stored in the MCP configuration/g' src/mcpm/commands/toggle.py
sed -i '' 's/Server configuration is stored in MCPM and/Server configuration is stored in MCP and/g' src/mcpm/commands/toggle.py

# Update reference in client.py
sed -i '' 's/will be used for all MCPM operations/will be used for all MCP operations/g' src/mcpm/commands/client.py

# Update any remaining instances in the utils directory
find src/mcpm/utils -name "*.py" -type f -exec sed -i '' 's/for MCPM/for MCP/g' {} \;

echo "Updated references from MCPM to MCP"
