"""Server configuration utilities for MCPM"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from mcpm.core.schema import RemoteServerConfig, ServerConfig, STDIOServerConfig


class FullServerConfig(BaseModel):
    """Standard server configuration object that is client-agnostic

    This class provides a common representation of server configurations
    that can be used across different clients. Client-specific formatting
    should be implemented in each client manager class.
    """

    # Required fields
    name: str

    # Fields that are required for STDIO servers but optional for HTTP servers
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)

    # Optional fields
    env: Dict[str, str] = Field(default_factory=dict)
    display_name: Optional[str] = None
    description: str = ""
    installation: Optional[str] = None
    url: Optional[str] = None  # For HTTP servers
    headers: Dict[str, str] = Field(default_factory=dict)  # For HTTP servers

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
        "json_encoders": {
            # Custom encoders can be added here if needed
        },
    }

    @model_validator(mode="after")
    def set_display_name_default(self) -> "FullServerConfig":
        """Set default display_name to name if not provided"""
        if self.display_name is None:
            self.display_name = self.name
        return self

    @classmethod
    def from_dict(cls, data: Dict) -> "FullServerConfig":
        """Create a FullServerConfig from a dictionary

        Args:
            data: Dictionary containing server configuration

        Returns:
            FullServerConfig object
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

    def to_server_config(self) -> ServerConfig:
        """Convert FullServerConfig to a common server configuration format"""
        # Check if this is an HTTP server
        if self.installation == "http":
            if not self.url:
                raise ValueError(f"URL is required for HTTP server '{self.name}'")
            return RemoteServerConfig(name=self.name, url=self.url, headers=self.headers)
        else:
            # Default to STDIO for all other cases
            # Command is required for STDIO servers
            if not self.command:
                raise ValueError(f"Command is required for non-HTTP server '{self.name}'")
            return STDIOServerConfig(name=self.name, command=self.command, args=self.args, env=self.env)
