"""
Implementation of the access monitor using DuckDB
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union

import duckdb

from mcpm.monitor.base import AccessEventType, AccessMonitor
from mcpm.utils.config import ConfigManager


class DuckDBAccessMonitor(AccessMonitor):
    """
    Implementation of the access monitor using DuckDB.
    This uses a thread pool to execute DuckDB operations asynchronously.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the DuckDBAccessMonitor.

        Args:
            db_path: Path to the DuckDB database file. If None, uses the default config directory.
        """
        if db_path is None:
            # Use ConfigManager to get the base config directory
            config_manager = ConfigManager()
            db_path = os.path.join(config_manager.config_dir, "monitor.duckdb")

        self.db_path = os.path.expanduser(db_path)
        self.connection = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize_storage(self) -> bool:
        """
        Initialize the storage for the access monitor asynchronously.

        Returns:
            bool: True if successful, False otherwise
        """
        async with self._lock:
            if self._initialized:
                return True

            try:
                # Run the initialization in a thread
                return await asyncio.to_thread(self._initialize_storage_impl)
            except Exception as e:
                print(f"Error initializing storage asynchronously: {e}")
                return False

    def _initialize_storage_impl(self) -> bool:
        """Internal implementation of storage initialization."""
        try:
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            # Connect to the database
            self.connection = duckdb.connect(self.db_path)

            # Create the events table if it doesn't exist using identity column for auto-incrementing
            self.connection.execute("""
                CREATE SEQUENCE IF NOT EXISTS event_id_seq;
                
                CREATE TABLE IF NOT EXISTS monitor_events (
                    id INTEGER DEFAULT nextval('event_id_seq') PRIMARY KEY,
                    event_type VARCHAR,
                    server_id VARCHAR,
                    resource_id VARCHAR,
                    client_id VARCHAR,
                    timestamp TIMESTAMP,
                    duration_ms INTEGER,
                    request_size INTEGER,
                    response_size INTEGER,
                    success BOOLEAN,
                    error_message VARCHAR,
                    metadata JSON,
                    raw_request JSON,
                    raw_response JSON
                )
            """)

            # Create a backward compatibility view
            self.connection.execute("""
                CREATE VIEW IF NOT EXISTS access_events AS 
                SELECT * FROM monitor_events
            """)

            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing storage: {e}")
            return False

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
        raw_request: Optional[Union[str, Dict]] = None,
        raw_response: Optional[Union[str, Dict]] = None,
    ) -> bool:
        """
        Track an access event asynchronously.

        Args:
            event_type: Type of the event
            server_id: Identifier for the server handling the request
            resource_id: Identifier for the accessed resource
            client_id: Identifier for the client making the request
            timestamp: When the event occurred
            duration_ms: Duration of the event in milliseconds
            request_size: Size of the request in bytes
            response_size: Size of the response in bytes
            success: Whether the access was successful
            error_message: Error message if the access failed
            metadata: Additional metadata for the event
            raw_request: Raw request data (string or dict)
            raw_response: Raw response data (string or dict)

        Returns:
            bool: True if event was successfully tracked, False otherwise
        """
        if not self._initialized:
            if not await self.initialize_storage():
                return False

        async with self._lock:
            try:
                # Use current time if timestamp is not provided
                if timestamp is None:
                    timestamp = datetime.now()

                # Run the tracking operation in a thread
                return await asyncio.to_thread(
                    self._track_event_impl,
                    event_type,
                    server_id,
                    resource_id,
                    client_id,
                    timestamp,
                    duration_ms,
                    request_size,
                    response_size,
                    success,
                    error_message,
                    metadata,
                    raw_request,
                    raw_response,
                )
            except Exception as e:
                print(f"Error tracking event asynchronously: {e}")
                return False

    def _track_event_impl(
        self,
        event_type: AccessEventType,
        server_id: str,
        resource_id: str,
        client_id: Optional[str],
        timestamp: datetime,
        duration_ms: Optional[int],
        request_size: Optional[int],
        response_size: Optional[int],
        success: bool,
        error_message: Optional[str],
        metadata: Optional[Dict[str, Any]],
        raw_request: Optional[Union[str, Dict]],
        raw_response: Optional[Union[str, Dict]],
    ) -> bool:
        """Internal implementation of track_event."""
        try:
            # Convert metadata to JSON if provided
            metadata_json = json.dumps(metadata) if metadata else None

            # Process raw request data
            request_json = None
            if raw_request is not None:
                if isinstance(raw_request, dict):
                    request_json = json.dumps(raw_request)
                else:
                    request_json = raw_request

            # Process raw response data
            response_json = None
            if raw_response is not None:
                if isinstance(raw_response, dict):
                    response_json = json.dumps(raw_response)
                else:
                    response_json = raw_response

            # Insert the event into the database
            self.connection.execute(
                """
                INSERT INTO monitor_events (
                    event_type, server_id, resource_id, client_id, timestamp,
                    duration_ms, request_size, response_size, success, error_message,
                    metadata, raw_request, raw_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
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
                ),
            )

            return True
        except Exception as e:
            print(f"Error tracking event: {e}")
            return False

    async def close(self) -> None:
        """Close the database connection asynchronously."""
        async with self._lock:
            if self.connection:
                await asyncio.to_thread(self._close_impl)

    def _close_impl(self) -> None:
        """Internal implementation of close."""
        if self.connection:
            self.connection.close()
            self.connection = None
