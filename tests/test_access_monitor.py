"""
Tests for the access monitoring functionality
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from mcpm.monitor import (
    AccessEventType,
    DuckDBAccessMonitor,
    get_monitor,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_mcpm_monitor.duckdb")
        yield db_path  # This will create a new database file for each test


@pytest.mark.asyncio
async def test_initialize_storage(temp_db_path):
    """Test that the storage can be initialized"""
    monitor = DuckDBAccessMonitor(db_path=temp_db_path)
    result = await monitor.initialize_storage()
    assert result is True

    # Check that the database file was created
    assert os.path.exists(temp_db_path)

    # Close the connection
    await monitor.close()


@pytest.mark.asyncio
async def test_track_event(temp_db_path):
    """Test tracking an event"""
    monitor = DuckDBAccessMonitor(db_path=temp_db_path)
    await monitor.initialize_storage()

    # Track a test event
    test_time = datetime.now()
    result = await monitor.track_event(
        event_type=AccessEventType.TOOL_INVOCATION,
        server_id="test-server",
        resource_id="test-tool",
        client_id="test-client",
        timestamp=test_time,
        duration_ms=100,
        request_size=1024,
        response_size=2048,
        success=True,
        metadata={"param1": "value1", "param2": 42},
    )
    assert result is True

    # Query the database directly to check if the event was recorded
    result = monitor.connection.execute("""
        SELECT * FROM monitor_events
        WHERE server_id = 'test-server'
        AND resource_id = 'test-tool'
    """).fetchall()

    # Check that exactly one event was recorded
    assert len(result) == 1

    # Check that the event has the correct data
    event = result[0]
    assert event[1] == "TOOL_INVOCATION"  # event_type
    assert event[2] == "test-server"  # server_id
    assert event[3] == "test-tool"  # resource_id
    assert event[4] == "test-client"  # client_id

    # Duration and sizes
    assert event[6] == 100  # duration_ms
    assert event[7] == 1024  # request_size
    assert event[8] == 2048  # response_size

    # Success and metadata
    assert event[9] is True  # success
    assert "param1" in event[11]  # metadata
    assert "param2" in event[11]

    # Close the connection
    await monitor.close()


@pytest.mark.asyncio
async def test_multiple_events(temp_db_path):
    """Test tracking multiple events"""
    monitor = DuckDBAccessMonitor(db_path=temp_db_path)
    await monitor.initialize_storage()

    # Track multiple events
    base_time = datetime.now()

    # Event 1: Tool invocation
    await monitor.track_event(
        event_type=AccessEventType.TOOL_INVOCATION,
        server_id="server1",
        resource_id="tool1",
        timestamp=base_time,
        success=True,
    )

    # Event 2: Resource access
    await monitor.track_event(
        event_type=AccessEventType.RESOURCE_ACCESS,
        server_id="server1",
        resource_id="resource1",
        timestamp=base_time + timedelta(minutes=1),
        success=True,
    )

    # Event 3: Prompt execution
    await monitor.track_event(
        event_type=AccessEventType.PROMPT_EXECUTION,
        server_id="server2",
        resource_id="prompt1",
        timestamp=base_time + timedelta(minutes=2),
        success=False,
        error_message="Test error",
    )

    # Query all events
    result = monitor.connection.execute("""
        SELECT * FROM monitor_events
        ORDER BY timestamp
    """).fetchall()

    # Check that we have three events
    assert len(result) == 3

    # Check first event
    assert result[0][1] == "TOOL_INVOCATION"
    assert result[0][2] == "server1"
    assert result[0][3] == "tool1"

    # Check second event
    assert result[1][1] == "RESOURCE_ACCESS"
    assert result[1][2] == "server1"
    assert result[1][3] == "resource1"

    # Check third event
    assert result[2][1] == "PROMPT_EXECUTION"
    assert result[2][2] == "server2"
    assert result[2][3] == "prompt1"
    assert result[2][9] is False
    assert result[2][10] == "Test error"

    # Close the connection
    await monitor.close()


@pytest.mark.asyncio
async def test_get_monitor_utility():
    """Test the get_monitor utility function"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a monitor with a custom path
        db_path = os.path.join(temp_dir, "test.duckdb")
        monitor = await get_monitor(db_path)

        # Check that the monitor is initialized
        assert monitor.connection is not None

        # Close the connection
        await monitor.close()


@pytest.mark.asyncio
async def test_raw_request_response(temp_db_path):
    """Test tracking events with raw request and response data"""
    monitor = DuckDBAccessMonitor(db_path=temp_db_path)
    await monitor.initialize_storage()

    # Test with JSON dictionary
    json_dict = {"method": "test", "params": {"param1": "value1"}}

    # Test with JSON string
    json_str = '{"result": "success", "data": 42}'

    # Track event with raw request/response
    await monitor.track_event(
        event_type=AccessEventType.PROMPT_EXECUTION,
        server_id="test-server",
        resource_id="test-prompt",
        raw_request=json_dict,
        raw_response=json_str,
        success=True,
    )

    # Query the database
    result = monitor.connection.execute("""
        SELECT raw_request, raw_response
        FROM monitor_events
        WHERE server_id = 'test-server'
    """).fetchone()

    # Check the raw data was stored correctly
    assert result is not None
    assert result[0] is not None
    assert result[1] is not None

    # Check content
    assert "method" in result[0]  # raw_request
    assert "params" in result[0]
    assert "result" in result[1]  # raw_response
    assert "data" in result[1]

    # Close the connection
    await monitor.close()


@pytest.mark.asyncio
async def test_backward_compatibility(temp_db_path):
    """Test that the backward compatibility view works"""
    monitor = DuckDBAccessMonitor(db_path=temp_db_path)
    await monitor.initialize_storage()

    # Track an event
    await monitor.track_event(
        event_type=AccessEventType.TOOL_INVOCATION,
        server_id="test-server",
        resource_id="test-tool",
        success=True,
    )

    # Query using the old table name via the view
    result = monitor.connection.execute("""
        SELECT * FROM access_events
        WHERE server_id = 'test-server'
    """).fetchall()

    assert len(result) == 1
    assert result[0][1] == "TOOL_INVOCATION"

    # Close the connection
    await monitor.close()
