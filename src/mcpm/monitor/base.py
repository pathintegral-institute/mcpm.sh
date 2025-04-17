"""
Core interfaces for MCPM monitoring functionality
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    total: int = Field(description="Total number of events")
    page: int = Field(description="Page number")
    limit: int = Field(description="Number of events per page")
    total_pages: int = Field(description="Total number of pages")


class MCPEvent(BaseModel):
    id: int = Field(description="Event ID")
    event_type: str = Field(description="Event type")
    server_id: str = Field(description="Server ID")
    resource_id: str = Field(description="Resource ID")
    client_id: Optional[str] = Field(description="Client ID")
    timestamp: str = Field(description="Event timestamp")
    duration_ms: Optional[int] = Field(description="Event duration in milliseconds")
    request_size: Optional[int] = Field(description="Request size in bytes")
    response_size: Optional[int] = Field(description="Response size in bytes")
    success: bool = Field(description="Event success status")
    error_message: Optional[str] = Field(description="Error message")
    metadata: Optional[Dict[str, Any]] = Field(description="Event metadata")
    raw_request: Optional[Union[str, Dict]] = Field(description="Raw request data")
    raw_response: Optional[Union[str, Dict]] = Field(description="Raw response data")


class QueryEventResponse(BaseModel):
    pagination: Pagination = Field(description="Pagination information")
    events: list[MCPEvent] = Field(description="List of events")


class AccessEventType(Enum):
    """Type of MCP access event"""

    TOOL_INVOCATION = auto()  # Tool was invoked (modifying content)
    RESOURCE_ACCESS = auto()  # Resource was accessed (reading content)
    PROMPT_EXECUTION = auto()  # Prompt was executed (generating content)


class AccessMonitor(ABC):
    """Abstract interface for monitoring MCP access events"""

    @abstractmethod
    async def track_event(
        self,
        event_type: AccessEventType,
        server_id: str,
        resource_id: str,
        client_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        raw_request: Optional[Union[Dict[str, Any], str]] = None,
        raw_response: Optional[Union[Dict[str, Any], str]] = None,
    ) -> bool:
        """
        Track an MCP access event

        Args:
            event_type: Type of access event (tool, resource, or prompt)
            server_id: ID of the MCP server
            resource_id: ID of the specific resource/tool/prompt
            client_id: ID of the client (if available)
            timestamp: When the event occurred (defaults to now if None)
            duration_ms: Duration of the operation in milliseconds
            request_size: Size of the request in bytes
            response_size: Size of the response in bytes
            success: Whether the operation succeeded
            error_message: Error message if operation failed
            metadata: Additional metadata about the event
            raw_request: Raw request data as JSON object or string
            raw_response: Raw response data as JSON object or string

        Returns:
            bool: True if event was successfully tracked, False otherwise
        """
        pass

    @abstractmethod
    async def initialize_storage(self) -> bool:
        """
        Initialize the storage backend for tracking events

        Returns:
            True if initialization succeeded, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close any open connections to the storage backend
        """
        pass

    @abstractmethod
    async def query_events(
        self, offset: str, page: int, limit: int, event_type: Optional[str] = None
    ) -> QueryEventResponse:
        """
        Query events from the storage backend

        Args:
            offset: Time offset for the query
            page: Page number
            limit: Number of events per page
            event_type: Type of events to query (optional)

        Returns:
            QueryEventResponse: List of events matching the query
        """
        pass
