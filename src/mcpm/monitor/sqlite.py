"""
Implementation of the access monitor using SQLite
"""

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from mcpm.monitor.base import (
    AccessEventType,
    AccessMonitor,
    MCPEvent,
    Pagination,
    ProfileStats,
    QueryEventResponse,
    ServerStats,
    UsageSession,
    UsageStats,
)
from mcpm.utils.config import ConfigManager


class SQLiteAccessMonitor(AccessMonitor):
    """
    Implementation of the access monitor using SQLite.
    This uses a thread pool to execute SQLite operations asynchronously.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the SQLiteAccessMonitor.

        Args:
            db_path: Path to the SQLite database file. If None, uses the default config directory.
        """
        if db_path is None:
            # Use ConfigManager to get the base config directory
            config_manager = ConfigManager()
            db_path = os.path.join(config_manager.config_dir, "monitor.db")

        self.db_path = os.path.expanduser(db_path)
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
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and performance
            conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout for busy database

            # Create the events table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitor_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    server_id TEXT,
                    resource_id TEXT,
                    session_id TEXT,
                    client_id TEXT,
                    timestamp DATETIME,
                    duration_ms INTEGER,
                    request_size INTEGER,
                    response_size INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    metadata TEXT,
                    raw_request TEXT,
                    raw_response TEXT
                )
            """)

            # Add session_id column if it doesn't exist (migration)
            try:
                conn.execute("SELECT session_id FROM monitor_events LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                conn.execute("ALTER TABLE monitor_events ADD COLUMN session_id TEXT")

            # usage_sessions table removed - now using events for session tracking

            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON monitor_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_server ON monitor_events(server_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON monitor_events(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON monitor_events(event_type)")
            # usage_sessions indexes removed with table

            # Create a backward compatibility view
            conn.execute("""
                CREATE VIEW IF NOT EXISTS access_events AS
                SELECT * FROM monitor_events
            """)

            conn.commit()
            conn.close()

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
        session_id: Optional[str] = None,
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
        """Track an access event asynchronously."""
        if not self._initialized:
            if not await self.initialize_storage():
                return False

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
                session_id,
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
        session_id: Optional[str],
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
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA busy_timeout=30000")

            conn.execute(
                """
                INSERT INTO monitor_events (
                    event_type, server_id, resource_id, session_id, client_id, timestamp,
                    duration_ms, request_size, response_size, success, error_message,
                    metadata, raw_request, raw_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type.name,
                    server_id,
                    resource_id,
                    session_id,
                    client_id,
                    timestamp.isoformat(),
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

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error tracking event: {e}")
            return False

    async def query_events(
        self, offset: str, page: int, limit: int, event_type: Optional[str] = None
    ) -> QueryEventResponse:
        """Query events from the database with pagination."""
        if not self._initialized:
            if not await self.initialize_storage():
                return QueryEventResponse(pagination=Pagination(total=0, page=0, limit=0, total_pages=0), events=[])

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
        """Query events from the storage backend"""
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
                # Convert to datetime
                time_delta_map = {"h": "hours", "d": "days", "w": "weeks", "m": "days"}
                if time_unit.lower() == "m":  # months
                    time_value *= 30  # approximate

                if time_unit.lower() in time_delta_map:
                    delta_kwargs = {time_delta_map[time_unit.lower()]: time_value}
                    threshold_time = datetime.now() - timedelta(**delta_kwargs)
                    conditions.append("datetime(timestamp) >= datetime(?)")
                    parameters.append(threshold_time.isoformat())
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

            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA busy_timeout=30000")

            # Get total count
            count_query = f"SELECT COUNT(*) FROM monitor_events {where_clause}"
            cursor = conn.execute(count_query, parameters)
            total = cursor.fetchone()[0]

            # Get paginated results
            query = f"""
                SELECT * FROM monitor_events
                {where_clause}
                ORDER BY datetime(timestamp) DESC
                LIMIT ? OFFSET ?
            """
            cursor = conn.execute(query, parameters + [limit, sql_offset])

            # Convert result to dictionary
            column_names = [desc[0] for desc in cursor.description]
            events = []

            for row in cursor.fetchall():
                event_dict = dict(zip(column_names, row))

                for field in ["metadata", "raw_request", "raw_response"]:
                    if event_dict[field] and isinstance(event_dict[field], str):
                        try:
                            event_dict[field] = json.loads(event_dict[field])
                        except json.JSONDecodeError:
                            pass

                # Convert timestamp back to readable format
                if event_dict["timestamp"]:
                    try:
                        dt = datetime.fromisoformat(event_dict["timestamp"])
                        event_dict["timestamp"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass

                events.append(MCPEvent.model_validate(event_dict))

            conn.close()

            return QueryEventResponse(
                pagination=Pagination(
                    total=total, page=page, limit=limit, total_pages=1 if limit == 0 else (total + limit - 1) // limit
                ),
                events=events,
            )
        except Exception as e:
            print(f"Error querying events: {e}")
            return QueryEventResponse(pagination=Pagination(total=0, page=0, limit=0, total_pages=0), events=[])

    # track_session method removed - use track_event with SESSION_START/SESSION_END instead

    async def get_computed_usage_stats(self, days: int = 30) -> UsageStats:
        """Get comprehensive usage statistics computed from events."""
        if not self._initialized:
            if not await self.initialize_storage():
                return UsageStats(
                    servers=[],
                    profiles=[],
                    recent_sessions=[],
                    total_servers=0,
                    total_profiles=0,
                    total_sessions=0,
                    date_range_days=days,
                )

        return await asyncio.to_thread(self._get_computed_usage_stats_impl, days)

    def _get_computed_usage_stats_impl(self, days: int) -> UsageStats:
        """Internal implementation computing usage stats from events."""
        try:
            # Calculate date threshold
            threshold = datetime.now() - timedelta(days=days)

            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA busy_timeout=30000")

            # Get session data from session_start events
            sessions_query = """
                SELECT
                    session_id,
                    server_id,
                    json_extract(metadata, '$.action') as action,
                    json_extract(metadata, '$.profile_name') as profile_name,
                    json_extract(metadata, '$.transport') as transport,
                    json_extract(metadata, '$.source') as source,
                    timestamp as start_time,
                    (SELECT e2.timestamp FROM monitor_events e2
                     WHERE e2.session_id = e1.session_id AND e2.event_type = 'SESSION_END'
                     LIMIT 1) as end_time,
                    (SELECT e2.success FROM monitor_events e2
                     WHERE e2.session_id = e1.session_id AND e2.event_type = 'SESSION_END'
                     LIMIT 1) as session_success
                FROM monitor_events e1
                WHERE e1.event_type = 'SESSION_START'
                  AND datetime(e1.timestamp) >= datetime(?)
                ORDER BY e1.timestamp DESC
            """

            cursor = conn.execute(sessions_query, [threshold.isoformat()])
            session_results = cursor.fetchall()

            # Build sessions list
            recent_sessions = []
            for row in session_results:
                (
                    session_id,
                    server_id,
                    action,
                    profile_name,
                    transport,
                    source,
                    start_time,
                    end_time,
                    session_success,
                ) = row

                # Calculate duration
                duration_ms = None
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                        duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
                    except (ValueError, AttributeError):
                        pass

                # Create session object
                recent_sessions.append(
                    UsageSession(
                        id=None,  # No separate session ID in events
                        server_name=server_id,
                        profile_name=profile_name,
                        action=action or "unknown",
                        timestamp=start_time,
                        duration_ms=duration_ms,
                        success=bool(session_success) if session_success is not None else True,
                        metadata={
                            "session_id": session_id,
                            "transport": transport,
                            "source": source,
                            "computed_from_events": True,
                        },
                    )
                )

            # Compute server statistics
            server_stats_query = """
                SELECT
                    server_id,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(DISTINCT CASE
                        WHEN json_extract(metadata, '$.action') IN ('run', 'run_http', 'profile_run')
                        THEN session_id
                    END) as total_runs,
                    MIN(datetime(timestamp)) as first_used,
                    MAX(datetime(timestamp)) as last_used,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
                    json_extract(metadata, '$.transport') as primary_transport
                FROM monitor_events
                WHERE event_type = 'SESSION_START'
                  AND datetime(timestamp) >= datetime(?)
                  AND server_id IS NOT NULL
                GROUP BY server_id
                ORDER BY total_sessions DESC
            """

            cursor = conn.execute(server_stats_query, [threshold.isoformat()])
            server_results = cursor.fetchall()
            servers = []
            for row in server_results:
                server_id, total_sessions, total_runs, first_used, last_used, success_rate, primary_transport = row

                servers.append(
                    ServerStats(
                        server_name=server_id,
                        total_sessions=total_sessions or 0,
                        total_runs=total_runs or 0,
                        first_used=first_used,
                        last_used=last_used,
                        total_duration_ms=0,  # Would need to compute from session pairs
                        success_rate=success_rate or 0.0,
                        primary_transport=primary_transport or "unknown",
                        origin_breakdown=None,  # Would need additional computation
                    )
                )

            # Compute profile statistics
            profile_stats_query = """
                SELECT
                    json_extract(metadata, '$.profile_name') as profile_name,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(DISTINCT session_id) as total_runs,
                    MIN(datetime(timestamp)) as first_used,
                    MAX(datetime(timestamp)) as last_used,
                    COUNT(DISTINCT server_id) as server_count
                FROM monitor_events
                WHERE event_type = 'SESSION_START'
                  AND datetime(timestamp) >= datetime(?)
                  AND json_extract(metadata, '$.profile_name') IS NOT NULL
                GROUP BY json_extract(metadata, '$.profile_name')
                ORDER BY total_sessions DESC
            """

            cursor = conn.execute(profile_stats_query, [threshold.isoformat()])
            profile_results = cursor.fetchall()
            profiles = []
            for row in profile_results:
                profile_name, total_sessions, total_runs, first_used, last_used, server_count = row

                if profile_name:  # Skip null profile names
                    profiles.append(
                        ProfileStats(
                            profile_name=profile_name,
                            total_sessions=total_sessions or 0,
                            total_runs=total_runs or 0,
                            first_used=first_used,
                            last_used=last_used,
                            server_count=server_count or 0,
                        )
                    )

            # Get totals
            totals_query = """
                SELECT
                    COUNT(DISTINCT server_id) as total_servers,
                    COUNT(DISTINCT json_extract(metadata, '$.profile_name')) as total_profiles,
                    COUNT(DISTINCT session_id) as total_sessions
                FROM monitor_events
                WHERE event_type = 'SESSION_START'
                  AND datetime(timestamp) >= datetime(?)
            """

            cursor = conn.execute(totals_query, [threshold.isoformat()])
            totals_result = cursor.fetchone()

            conn.close()

            return UsageStats(
                servers=servers,
                profiles=profiles,
                recent_sessions=recent_sessions[:50],  # Limit to last 50
                total_servers=totals_result[0] or 0,
                total_profiles=totals_result[1] or 0,
                total_sessions=totals_result[2] or 0,
                date_range_days=days,
            )

        except Exception as e:
            print(f"Error getting computed usage stats: {e}")
            return UsageStats(
                servers=[],
                profiles=[],
                recent_sessions=[],
                total_servers=0,
                total_profiles=0,
                total_sessions=0,
                date_range_days=days,
            )

    async def get_usage_stats(self, days: int = 30) -> UsageStats:
        """Get comprehensive usage statistics (delegates to computed stats)."""
        return await self.get_computed_usage_stats(days)

    # _get_usage_stats_impl removed - now using computed stats from events

    async def get_server_stats(self, server_name: str, days: int = 30) -> Optional[ServerStats]:
        """Get usage statistics for a specific server (from computed stats)."""
        # Get from computed stats and filter for specific server
        stats = await self.get_computed_usage_stats(days)
        for server in stats.servers:
            if server.server_name == server_name:
                return server
        return None

    async def get_profile_stats(self, profile_name: str, days: int = 30) -> Optional[ProfileStats]:
        """Get usage statistics for a specific profile (from computed stats)."""
        # Get from computed stats and filter for specific profile
        stats = await self.get_computed_usage_stats(days)
        for profile in stats.profiles:
            if profile.profile_name == profile_name:
                return profile
        return None

    # _get_server_transport_info and _get_server_origin_breakdown removed - no longer needed with computed stats

    async def close(self) -> None:
        """Close any database connections."""
        # SQLite connections are per-operation, so nothing to close
        pass
