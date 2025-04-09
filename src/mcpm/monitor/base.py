"""
Core interfaces for MCPM monitoring functionality
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional, Union


class AccessEventType(Enum):
    """Type of MCP access event"""

    TOOL_INVOCATION = auto()  # Tool was invoked (modifying content)
    RESOURCE_ACCESS = auto()  # Resource was accessed (reading content)
    PROMPT_EXECUTION = auto()  # Prompt was executed (generating content)


class AccessMonitor(ABC):
    """Abstract interface for monitoring MCP access events"""

    @abstractmethod
    def track_event(
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
    ) -> None:
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
        """
        pass

    @abstractmethod
    def initialize_storage(self) -> bool:
        """
        Initialize the storage backend for tracking events

        Returns:
            True if initialization succeeded, False otherwise
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close any open connections to the storage backend
        """
        pass
