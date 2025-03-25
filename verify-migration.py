#!/usr/bin/env python3
"""
Verification script for the MCP to MCPM migration.
This script checks that all files in src/mcp have corresponding files in src/mcpm.
"""

import os
from pathlib import Path

def check_migration():
    """
    Check that all files in src/mcp have been migrated to src/mcpm.
    Returns a list of files that haven't been migrated.
    """
    base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    mcp_dir = base_dir / "src" / "mcp"
    mcpm_dir = base_dir / "src" / "mcpm"
    
    missing_files = []
    
    for root, _, files in os.walk(mcp_dir):
        rel_path = os.path.relpath(root, mcp_dir)
        
        for file in files:
            if file.endswith('.py'):
                # Calculate the corresponding path in mcpm
                if rel_path == '.':
                    mcpm_file_path = mcpm_dir / file
                else:
                    mcpm_file_path = mcpm_dir / rel_path / file
                
                if not mcpm_file_path.exists():
                    missing_files.append(os.path.join(rel_path, file))
    
    return missing_files

def main():
    """Main entry point"""
    print("Verifying migration from MCP to MCPM...")
    missing_files = check_migration()
    
    if missing_files:
        print("\n⚠️ The following files in src/mcp do not have corresponding files in src/mcpm:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease migrate these files before removing src/mcp")
        return False
    else:
        print("✅ All files from src/mcp have corresponding files in src/mcpm")
        print("\nIt should be safe to remove the src/mcp directory.")
        return True

if __name__ == "__main__":
    main()
