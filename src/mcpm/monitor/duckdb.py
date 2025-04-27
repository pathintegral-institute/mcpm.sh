"""
Implementation of the access monitor using DuckDB
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union

try:
    import duckdb
except ImportError as e:
    duckdb = None
    if "DLL load failed while importing duckdb" in str(e):
        print("The DuckDB Python package requires the Microsoft Visual C++ Redistributable. ")
        print(
            "Please install it from: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170"
        )
        print("See https://duckdb.org/docs/installation/?version=stable&environment=python for more information.")
    else:
        raise

from mcpm.monitor.base import AccessEventType, AccessMonitor, MCPEvent, Pagination, QueryEventResponse
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
        if duckdb is None:
            print("DuckDB is not available.")
            return False
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

    async def query_events(
        self, offset: str, page: int, limit: int, event_type: Optional[str] = None
    ) -> QueryEventResponse:
        """
        Query events from the database with pagination.

        Args:
            offset: Time offset pattern like "3h" for past 3 hours, "1d" for past day, etc.
            page: Page number (1-based)
            limit: Number of events per page
            event_type: Type of events to filter by

        Returns:
            Dict containing events, total count, page, and limit
        """
        if not self._initialized:
            if not await self.initialize_storage():
                return QueryEventResponse(pagination=Pagination(total=0, page=0, limit=0, total_pages=0), events=[])

        async with self._lock:
            response = await asyncio.to_thread(
                self._query_events_impl,
                offset,
                page,
                limit,
                event_type,
            )
            return response

    def _query_events_impl(
        self,
        offset: str,
        page: int,
        limit: int,
        event_type: Optional[str],
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
        try:
            # Build the base query and conditions
            conditions = []
            parameters = []

            # handle time offset
            time_value = 0
            time_unit = ""

            # Parse offset pattern like "3h", "1d", etc.
            for i, char in enumerate(offset):
                if char.isdigit():
                    time_value = time_value * 10 + int(char)
                else:
                    time_unit = offset[i:]
                    break

            if time_unit and time_value > 0:
                # Convert to SQL interval format
                interval_map = {"h": "HOUR", "d": "DAY", "w": "WEEK", "m": "MONTH"}

                if time_unit.lower() in interval_map:
                    conditions.append(
                        f"timestamp >= TIMESTAMP '{datetime.now()}' - INTERVAL {time_value} {interval_map.get(time_unit.lower())}"
                    )
            else:
                return QueryEventResponse(pagination=Pagination(total=0, page=0, limit=0, total_pages=0), events=[])

            if event_type:
                conditions.append("event_type = ?")
                parameters.append(event_type)

            # Build the final query
            where_clause = " AND ".join(conditions)
            if where_clause:
                where_clause = f"WHERE {where_clause}"

            sql_offset = (page - 1) * limit
            # Get total count
            count_query = f"SELECT COUNT(*) FROM monitor_events {where_clause}"
            total_result = self.connection.execute(count_query, parameters).fetchone()
            total = total_result[0] if total_result else 0

            # Get paginated results
            query = f"""
                SELECT * FROM monitor_events
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            cursor = self.connection.execute(query, parameters + [limit, sql_offset])

            # Convert result to dictionary
            column_names = [desc[0] for desc in cursor.description]
            events = []

            for row in cursor.fetchall():
                event_dict = dict(zip(column_names, row))

                for field in ["metadata", "raw_request", "raw_response"]:
                    if event_dict[field] and isinstance(event_dict[field], str):
                        try:
                            event_dict[field] = json.loads(event_dict[field])
                        except Exception:
                            pass

                event_dict["timestamp"] = datetime.strftime(event_dict["timestamp"], "%Y-%m-%d %H:%M:%S")
                events.append(MCPEvent.model_validate(event_dict))

            return QueryEventResponse(
                pagination=Pagination(
                    total=total, page=page, limit=limit, total_pages=1 if limit == 0 else (total + limit - 1) // limit
                ),
                events=events,
            )
        except Exception as e:
            print(f"Error querying events: {e}")
            return QueryEventResponse(pagination=Pagination(total=0, page=0, limit=0, total_pages=0), events=[])

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
