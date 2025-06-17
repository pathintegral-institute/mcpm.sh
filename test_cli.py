#!/usr/bin/env python3
"""
Test script for MCPM CLI
Run this script directly to test the CLI without installation
"""

import os
import sys

os.environ.setdefault("MCPM_REPO_URL", f"file://{os.getcwd()}/_dev/api/servers.json")


# Add the src directory to the path so we can import mcpm
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from mcpm.cli import main

os.system("./scripts/prepare.sh _dev")

if __name__ == "__main__":
    # Run the CLI with any command line arguments passed to this script
    sys.exit(main())
