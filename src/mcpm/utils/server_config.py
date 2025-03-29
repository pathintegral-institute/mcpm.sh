"""Server configuration utilities for MCPM"""

import os
from typing import Dict, List, Optional, ClassVar

from pydantic import BaseModel, Field, model_validator


class ServerConfig(BaseModel):
    """Standard server configuration object that is client-agnostic

    This class provides a common representation of server configurations
    that can be used across different clients. Client-specific formatting
    should be implemented in each client manager class.
    """

    # Required fields
    name: str
    command: str
    args: List[str]

    # Optional fields
    env_vars: Dict[str, str] = Field(default_factory=dict)
    display_name: Optional[str] = None
    description: str = ""
    installation: Optional[str] = None

    # Lists of field names for compatibility with existing code
    REQUIRED_FIELDS: ClassVar[List[str]] = ["name", "command", "args", "env_vars"]
    OPTIONAL_FIELDS: ClassVar[List[str]] = ["display_name", "description", "installation"]

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
        "json_encoders": {
            # Custom encoders can be added here if needed
        },
    }

    @model_validator(mode="after")
    def set_display_name_default(self) -> "ServerConfig":
        """Set default display_name to name if not provided"""
        if self.display_name is None:
            self.display_name = self.name
        return self

    @classmethod
    def from_dict(cls, data: Dict) -> "ServerConfig":
        """Create a ServerConfig from a dictionary

        Args:
            data: Dictionary containing server configuration

        Returns:
            ServerConfig object
        """
        # This is now a simple wrapper around the Pydantic model constructor
        # We keep it for backwards compatibility
        return cls.model_validate(data)

    def to_dict(self) -> Dict:
        """Convert to a dictionary with all fields

        Returns:
            Dictionary representation of this ServerConfig
        """
        # This is now a simple wrapper around the Pydantic model.model_dump() method
        # We keep it for backwards compatibility
        return self.model_dump(exclude_none=True)

    def get_filtered_env_vars(self, env: Dict[str, str]) -> Dict[str, str]:
        """Get filtered environment variables with empty values removed

        This is a utility for clients to filter out empty environment
        variables, regardless of client-specific formatting.

        Args:
            env: Dictionary of environment variables to use for resolving
                 ${VAR_NAME} references.

        Returns:
            Dictionary of non-empty environment variables
        """
        if not self.env_vars:
            return {}

        # Use provided environment without falling back to os.environ
        environment = env

        # Filter out empty environment variables
        non_empty_env = {}
        for key, value in self.env_vars.items():
            # For environment variable references like ${VAR_NAME}, check if the variable exists
            # and has a non-empty value. If it doesn't exist or is empty, exclude it.
            if value is not None and isinstance(value, str):
                if value.startswith("${") and value.endswith("}"):
                    # Extract the variable name from ${VAR_NAME}
                    env_var_name = value[2:-1]
                    env_value = environment.get(env_var_name, "")
                    # Only include if the variable has a value in the environment
                    if env_value.strip() != "":
                        non_empty_env[key] = value
                # For regular values, only include if they're not empty
                elif value.strip() != "":
                    non_empty_env[key] = value

        return non_empty_env
