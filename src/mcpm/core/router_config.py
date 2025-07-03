"""Simple RouterConfig for backward compatibility."""


class RouterConfig:
    """Simple router configuration for backward compatibility."""
    
    def __init__(self, api_key=None, auth_enabled=False):
        self.api_key = api_key
        self.auth_enabled = auth_enabled