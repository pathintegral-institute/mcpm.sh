#!/usr/bin/env python3
"""
Script to update imports and references from 'mcp' to 'mcpm' across all Python files
"""

import os
import re
from pathlib import Path

def update_file(file_path):
    """Update a file's contents to replace mcp with mcpm"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update imports
    updated = re.sub(r'from mcp\.', r'from mcpm.', content)
    updated = re.sub(r'import mcp\.', r'import mcpm.', updated)
    
    # Update docstrings
    updated = re.sub(r'MCP Manager - Model Context Protocol Management Tool', 
                    r'MCPM - Model Context Protocol Manager', updated)
    updated = re.sub(r'MCP Manager', r'MCPM', updated)
    
    # Update command examples
    updated = re.sub(r'mcp ([a-z-]+)', r'mcpm \1', updated)
    
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
