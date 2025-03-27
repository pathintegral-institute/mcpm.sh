"""
Server configuration utilities for MCPM
"""

import os
from typing import Dict, Any, List, Optional, ClassVar, Type, TypeVar

T = TypeVar('T', bound='ServerConfig')

class ServerConfig:
    """Standard server configuration object that is client-agnostic
    
    This class provides a common representation of server configurations
    that can be used across different clients. Client-specific formatting
    should be implemented in each client manager class.
    """
    
    # Fields that should be included in all serializations
    REQUIRED_FIELDS: ClassVar[List[str]] = [
        "name", "command", "args", "env_vars"
    ]
    
    # Fields that should be optional in serializations
    OPTIONAL_FIELDS: ClassVar[List[str]] = [
        "display_name", "description", "installation"
    ]
    
    def __init__(
        self,
        name: str,
        command: str,
        args: List[str],
        env_vars: Optional[Dict[str, str]] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        installation: Optional[str] = None
    ):
        """Initialize a standard server configuration"""
        self.name = name
        self.command = command
        self.args = args
        self.env_vars = env_vars or {}
        self.display_name = display_name or name
        self.description = description or ""
        self.installation = installation
        
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create a ServerConfig from a dictionary
        
        Args:
            data: Dictionary containing server configuration
            
        Returns:
            ServerConfig object
        """
        # Filter the dictionary to include only the fields we care about
        filtered_data = {}
        
        # Add all required and optional fields that are present
        for field in cls.REQUIRED_FIELDS + cls.OPTIONAL_FIELDS:
            if field in data:
                filtered_data[field] = data[field]
        
        return cls(**filtered_data)
    
    def get_filtered_env_vars(self) -> Dict[str, str]:
        """Get filtered environment variables with empty values removed
        
        This is a common utility for clients to filter out empty environment 
        variables, regardless of client-specific formatting.
        
        Returns:
            Dictionary of non-empty environment variables
        """
        if not self.env_vars:
            return {}
            
        # Filter out empty environment variables
        non_empty_env = {}
        for key, value in self.env_vars.items():
            # For environment variable references like ${VAR_NAME}, check if the variable exists
            # and has a non-empty value. If it doesn't exist or is empty, exclude it.
            if value is not None and isinstance(value, str):
                if value.startswith("${") and value.endswith("}"):
                    # Extract the variable name from ${VAR_NAME}
                    env_var_name = value[2:-1]
                    env_value = os.environ.get(env_var_name, "")
                    # Only include if the variable has a value in the environment
                    if env_value.strip() != "":
                        non_empty_env[key] = value
                # For regular values, only include if they're not empty
                elif value.strip() != "":
                    non_empty_env[key] = value
                    
        return non_empty_env
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary with all fields
        
        Returns:
            Dictionary representation of this ServerConfig
        """
        result = {}
        
        # Include all fields, filtering out None values
        for field in self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS:
            value = getattr(self, field, None)
            if value is not None:
                result[field] = value
                
        return result
