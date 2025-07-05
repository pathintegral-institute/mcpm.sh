"""
Core interfaces for MCPM monitoring functionality
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

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
    resource_id: str = Field(description="Resource ID (tool name, resource URI, or 'session' for session events)")
    session_id: Optional[str] = Field(description="Session ID - links all events in a session", default=None)
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

    # Operation-level events (existing)
    TOOL_INVOCATION = auto()  # Tool was invoked (modifying content)
    RESOURCE_ACCESS = auto()  # Resource was accessed (reading content)
    PROMPT_EXECUTION = auto()  # Prompt was executed (generating content)

    # Session-level events (new for unified tracking)
    SESSION_START = auto()  # Session/proxy started
    SESSION_END = auto()  # Session/proxy ended


class SessionTransport(Enum):
    """Transport mechanism for client connections"""

    STDIO = "stdio"  # Standard input/output
    HTTP = "http"  # HTTP server


class SessionSource(Enum):
    """Origin of the session request"""

    LOCAL = "local"  # Local machine request
    REMOTE = "remote"  # Remote network request


class UsageSession(BaseModel):
    """High-level usage session tracking"""

    id: Optional[int] = Field(description="Session ID")
    server_name: Optional[str] = Field(description="Server name")
    profile_name: Optional[str] = Field(description="Profile name")
    action: str = Field(description="Action performed")  # Keep backward compatibility
    timestamp: str = Field(description="Session timestamp")
    duration_ms: Optional[int] = Field(description="Session duration in milliseconds")
    success: bool = Field(description="Session success status", default=True)
    metadata: Optional[Dict[str, Any]] = Field(description="Session metadata")

    @property
    def transport(self) -> SessionTransport:
        """Extract transport from metadata or infer from action"""
        if self.metadata and "server_info" in self.metadata:
            transport_str = self.metadata["server_info"].get("transport", "stdio")
            return SessionTransport.HTTP if transport_str == "http" else SessionTransport.STDIO
        # Fallback based on action
        return SessionTransport.HTTP if "http" in self.action else SessionTransport.STDIO

    @property
    def source(self) -> SessionSource:
        """Extract source from metadata"""
        if self.metadata and "client_info" in self.metadata:
            origin = self.metadata["client_info"].get("origin", "local")
            return SessionSource.REMOTE if origin == "public_internet" else SessionSource.LOCAL
        return SessionSource.LOCAL


class ServerStats(BaseModel):
    """Server usage statistics"""

    server_name: str = Field(description="Server name")
    total_runs: int = Field(description="Total run count")
    total_sessions: int = Field(description="Total sessions")
    first_used: Optional[str] = Field(description="First usage timestamp")
    last_used: Optional[str] = Field(description="Last usage timestamp")
    total_duration_ms: Optional[int] = Field(description="Total runtime in milliseconds")
    success_rate: float = Field(description="Success rate percentage")
    primary_transport: str = Field(description="Primary transport type", default="unknown")
    origin_breakdown: Optional[Dict[str, int]] = Field(description="Request origin breakdown", default=None)


class ProfileStats(BaseModel):
    """Profile usage statistics"""

    profile_name: str = Field(description="Profile name")
    total_runs: int = Field(description="Total run count")
    total_sessions: int = Field(description="Total sessions")
    first_used: Optional[str] = Field(description="First usage timestamp")
    last_used: Optional[str] = Field(description="Last usage timestamp")
    server_count: int = Field(description="Number of servers in profile")


class UsageStats(BaseModel):
    """Combined usage statistics"""

    servers: List[ServerStats] = Field(description="Server statistics")
    profiles: List[ProfileStats] = Field(description="Profile statistics")
    recent_sessions: List[UsageSession] = Field(description="Recent sessions")
    total_servers: int = Field(description="Total active servers")
    total_profiles: int = Field(description="Total active profiles")
    total_sessions: int = Field(description="Total sessions")
    date_range_days: int = Field(description="Date range for statistics")


class AccessMonitor(ABC):
    """Abstract interface for monitoring MCP access events"""

    @abstractmethod
    async def track_event(
        self,
        event_type: AccessEventType,
        server_id: str,
        resource_id: str,
        session_id: Optional[str] = None,
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
            event_type: Type of access event (tool, resource, prompt, session_start, session_end)
            server_id: ID of the MCP server
            resource_id: ID of the specific resource/tool/prompt, or "session" for session events
            session_id: Session ID to link events in the same session
            client_id: ID of the client (if available)
            timestamp: When the event occurred (defaults to now if None)
            duration_ms: Duration of the operation in milliseconds
            request_size: Size of the request in bytes
            response_size: Size of the response in bytes
            success: Whether the operation succeeded
            error_message: Error message if operation failed
            metadata: Additional metadata about the event (includes transport, source, action for session events)
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

    # track_session method removed - use track_event with SESSION_START/SESSION_END instead

    @abstractmethod
    async def get_usage_stats(self, days: int = 30) -> UsageStats:
        """
        Get comprehensive usage statistics

        Args:
            days: Number of days to include in statistics

        Returns:
            UsageStats: Comprehensive usage statistics
        """
        pass

    @abstractmethod
    async def get_server_stats(self, server_name: str, days: int = 30) -> Optional[ServerStats]:
        """
        Get usage statistics for a specific server

        Args:
            server_name: Name of the server
            days: Number of days to include in statistics

        Returns:
            ServerStats: Server usage statistics or None if not found
        """
        pass

    @abstractmethod
    async def get_profile_stats(self, profile_name: str, days: int = 30) -> Optional[ProfileStats]:
        """
        Get usage statistics for a specific profile

        Args:
            profile_name: Name of the profile
            days: Number of days to include in statistics

        Returns:
            ProfileStats: Profile usage statistics or None if not found
        """
        pass
