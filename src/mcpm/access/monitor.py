"""
Access monitoring functionality for MCPM
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional, Union

import duckdb


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


class DuckDBAccessMonitor(AccessMonitor):
    """DuckDB implementation of MCP access monitoring"""

    def __init__(self, db_path: str = "~/.config/mcpm/access.duckdb"):
        """
        Initialize the DuckDB access monitor

        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = os.path.expanduser(db_path)
        self.db_dir = os.path.dirname(self.db_path)
        self.connection = None

    def initialize_storage(self) -> bool:
        """Initialize the DuckDB database and tables"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.db_dir, exist_ok=True)

            # Connect to database
            self.connection = duckdb.connect(self.db_path)

            # Create a sequence for auto-incrementing IDs
            self.connection.execute("""
                CREATE SEQUENCE IF NOT EXISTS access_events_id_seq START 1;
            """)

            # Create access_events table if it doesn't exist
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS access_events (
                    id INTEGER DEFAULT nextval('access_events_id_seq') PRIMARY KEY,
                    event_type VARCHAR NOT NULL,
                    server_id VARCHAR NOT NULL,
                    resource_id VARCHAR NOT NULL,
                    client_id VARCHAR,
                    timestamp TIMESTAMP NOT NULL,
                    duration_ms INTEGER,
                    request_size INTEGER,
                    response_size INTEGER,
                    success BOOLEAN NOT NULL,
                    error_message VARCHAR,
                    metadata JSON,
                    raw_request JSON,
                    raw_response JSON
                )
            """)

            # Create index on timestamp for efficient time-based queries
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_access_events_timestamp 
                ON access_events (timestamp)
            """)

            # Create index on server_id for filtering by server
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_access_events_server 
                ON access_events (server_id)
            """)

            # Create index on event_type for filtering by event type
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_access_events_type 
                ON access_events (event_type)
            """)

            return True
        except Exception as e:
            print(f"Error initializing DuckDB storage: {e}")
            return False

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
        """Track an MCP access event"""
        # Initialize connection if needed
        if self.connection is None:
            self.initialize_storage()

        # Use current time if no timestamp provided
        if timestamp is None:
            timestamp = datetime.now()

        # Convert metadata to JSON string if provided
        metadata_json = json.dumps(metadata) if metadata else None

        # Convert raw request and response to JSON strings
        # If they're already dictionaries, convert them to JSON strings
        # If they're strings, try to parse as JSON first, if that fails, store as JSON-encoded strings
        request_json = None
        if raw_request is not None:
            if isinstance(raw_request, dict):
                request_json = json.dumps(raw_request)
            else:
                try:
                    # Try to parse as JSON first
                    json.loads(raw_request)
                    request_json = raw_request  # It's already a valid JSON string
                except json.JSONDecodeError:
                    # Not valid JSON, encode as a JSON string
                    request_json = json.dumps(raw_request)

        response_json = None
        if raw_response is not None:
            if isinstance(raw_response, dict):
                response_json = json.dumps(raw_response)
            else:
                try:
                    # Try to parse as JSON first
                    json.loads(raw_response)
                    response_json = raw_response  # It's already a valid JSON string
                except json.JSONDecodeError:
                    # Not valid JSON, encode as a JSON string
                    response_json = json.dumps(raw_response)

        # Insert event into database
        try:
            self.connection.execute(
                """
                INSERT INTO access_events (
                    event_type, server_id, resource_id, client_id, timestamp,
                    duration_ms, request_size, response_size,
                    success, error_message, metadata, raw_request, raw_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    event_type.name,
                    server_id,
                    resource_id,
                    client_id,
                    timestamp,
                    duration_ms,
                    request_size,
                    response_size,
                    success,
                    error_message,
                    metadata_json,
                    request_json,
                    response_json,
                ],
            )
        except Exception as e:
            print(f"Error tracking event: {e}")

    def close(self) -> None:
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __del__(self):
        """Ensure connection is closed when object is deleted"""
        self.close()


# Convenience function to get a monitor instance
def get_monitor(db_path: Optional[str] = None) -> AccessMonitor:
    """
    Get a configured access monitor instance

    Args:
        db_path: Optional custom path to the database file

    Returns:
        Configured AccessMonitor instance
    """
    monitor = DuckDBAccessMonitor(db_path) if db_path else DuckDBAccessMonitor()
    monitor.initialize_storage()
    return monitor
