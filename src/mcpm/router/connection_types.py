"""
Defines Pydantic models and enums for connection details used by the manager.
"""

from enum import StrEnum
from typing import Annotated, Dict, Literal, Optional, Union

# Import Pydantic components
from pydantic import BaseModel, Field


class ConnectionType(StrEnum):
    """Enumeration of supported client connection transport types."""

    STDIO = "stdio"
    SSE = "sse"
    # Add other types like HTTP, WS etc. here if needed


class BaseConnectionDetails(BaseModel):
    id: str
    type: ConnectionType


class StdioConnectionDetails(BaseConnectionDetails):
    type: Literal[ConnectionType.STDIO] = ConnectionType.STDIO
    command: str
    args: list[str]
    env: Dict[str, str] = Field(default_factory=dict)  # Environment variables for stdio


class SSEConnectionDetails(BaseConnectionDetails):
    type: Literal[ConnectionType.SSE] = ConnectionType.SSE
    url: str
    headers: Optional[Dict[str, str]] = None


ConnectionDetails = Annotated[Union[StdioConnectionDetails, SSEConnectionDetails], Field(discriminator="type")]
