"""
Defines Pydantic models and enums for connection details used by the manager.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

# Import Pydantic components
from pydantic import BaseModel, Field, model_validator


class ConnectionType(Enum):
    """Enumeration of supported client connection transport types."""

    STDIO = "stdio"
    SSE = "sse"
    # Add other types like HTTP, WS etc. here if needed


class ConnectionDetails(BaseModel):
    """Pydantic model holding the details needed to establish a client transport connection."""

    type: ConnectionType  # Use the Enum

    # Stdio specific
    command: Optional[str] = None  # Command for stdio transport
    args: List[str] = Field(default_factory=list)  # Args for stdio transport
    env: Optional[Dict[str, str]] = None  # Environment variables for stdio

    # SSE / HTTP specific
    url: Optional[str] = None  # URL for SSE or other HTTP-based transports

    # Use model_validator (Pydantic v2 style) for cross-field validation
    @model_validator(mode="after")
    def check_required_fields(cls, data: Any) -> Any:
        if isinstance(data, ConnectionDetails):  # Ensure we operate on the model instance
            conn_type = data.type
            if conn_type == ConnectionType.STDIO:
                if not data.command:
                    raise ValueError("'command' is required for stdio connection type")
            elif conn_type == ConnectionType.SSE:
                if not data.url:
                    raise ValueError("'url' is required for sse connection type")
            # Add validation for other enum members if they are added
        return data

    # Example of a field validator (not strictly needed here but shows capability)
    # @field_validator('url')
    # def check_url_format(cls, v: Optional[str]):
    #     if v is not None and not v.startswith(('http://', 'https://')):
    #         raise ValueError('URL must start with http:// or https://')
    #     return v
