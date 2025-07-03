"""
Profile management commands - reimported from modular structure.
This maintains backward compatibility while using the new modular structure.
"""

# Import the main profile command group from the new modular structure
from .profile import profile

# Export for backward compatibility
__all__ = ["profile"]
