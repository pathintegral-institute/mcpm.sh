#!/usr/bin/env python3
"""
Script to update docstrings in Python files to use MCPM consistently
"""

import os
import re
from pathlib import Path

def update_file(file_path):
    """Update docstrings in a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace only appropriate references
    # Be careful to keep MCP when it refers to the Model Context Protocol itself
    updated = re.sub(r'Client integrations for MCP', r'Client integrations for MCPM', content)
    updated = re.sub(r'MCP utilities package', r'MCPM utilities package', updated)
    updated = re.sub(r'MCP commands package', r'MCPM commands package', updated)
    updated = re.sub(r'Edit command for MCP', r'Edit command for MCPM', updated)
    updated = re.sub(r'Install command for MCP', r'Install command for MCPM', updated)
    updated = re.sub(r'Remove command for MCP', r'Remove command for MCPM', updated)
    updated = re.sub(r'Search command for MCP', r'Search command for MCPM', updated)
    updated = re.sub(r'Toggle command for MCP', r'Toggle command for MCPM', updated)
    updated = re.sub(r'Server command for MCP', r'Server command for MCPM', updated)
    updated = re.sub(r'Status command for MCP', r'Status command for MCPM', updated)
    updated = re.sub(r'Client command for MCP', r'Client command for MCPM', updated)
    updated = re.sub(r'Enable command for MCP', r'Enable command for MCPM', updated)
    updated = re.sub(r'Disable command for MCP', r'Disable command for MCPM', updated)
    updated = re.sub(r'Configuration utilities for MCP', r'Configuration utilities for MCPM', updated)
    updated = re.sub(r'Repository utilities for MCP', r'Repository utilities for MCPM', updated)
    updated = re.sub(r'Client detector utility for MCP', r'Client detector utility for MCPM', updated)
    updated = re.sub(r'Server management utilities for MCP', r'Server management utilities for MCPM', updated)
    updated = re.sub(r'MCP Inspector', r'MCPM Inspector', updated)
    
    if content != updated:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated)
        return True
    return False

def main():
    """Main entry point"""
    base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    src_dir = base_dir / "src" / "mcpm"
    
    count = 0
    for path in src_dir.glob('**/*.py'):
        if update_file(path):
            print(f"Updated: {path}")
            count += 1
    
    print(f"Updated {count} files")

if __name__ == "__main__":
    main()
