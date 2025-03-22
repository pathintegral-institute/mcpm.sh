"""
Pytest configuration for MCP tests
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent))
