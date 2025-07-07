"""
Tests for the access monitoring functionality
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from mcpm.monitor import (
    AccessEventType,
    SQLiteAccessMonitor,
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
    monitor = SQLiteAccessMonitor(db_path=temp_db_path)
    result = await monitor.initialize_storage()
    assert result is True

    # Check that the database file was created
    assert os.path.exists(temp_db_path)

    # Close the connection
    await monitor.close()


@pytest.mark.asyncio
async def test_track_event(temp_db_path):
    """Test tracking an event"""
    monitor = SQLiteAccessMonitor(db_path=temp_db_path)
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

    # Query events using the monitor's query_events method
    response = await monitor.query_events("1d", 1, 10)

    # Check that exactly one event was recorded
    assert len(response.events) == 1

    # Check that the event has the correct data
    event = response.events[0]
    assert event.event_type == "TOOL_INVOCATION"
    assert event.server_id == "test-server"
    assert event.resource_id == "test-tool"
    assert event.client_id == "test-client"

    # Duration and sizes
    assert event.duration_ms == 100
    assert event.request_size == 1024
    assert event.response_size == 2048

    # Success and metadata
    assert event.success is True
    assert event.metadata is not None
    assert "param1" in event.metadata
    assert "param2" in event.metadata

    # Close the connection
    await monitor.close()


@pytest.mark.asyncio
async def test_multiple_events(temp_db_path):
    """Test tracking multiple events"""
    monitor = SQLiteAccessMonitor(db_path=temp_db_path)
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
    response = await monitor.query_events("1d", 1, 10)

    # Check that we have three events
    assert len(response.events) == 3

    # Events come in reverse chronological order, so last event is first
    # Check third event (most recent)
    assert response.events[0].event_type == "PROMPT_EXECUTION"
    assert response.events[0].server_id == "server2"
    assert response.events[0].resource_id == "prompt1"

    # Check second event
    assert response.events[1].event_type == "RESOURCE_ACCESS"
    assert response.events[1].server_id == "server1"
    assert response.events[1].resource_id == "resource1"

    # Check first event (oldest)
    assert response.events[2].event_type == "TOOL_INVOCATION"
    assert response.events[2].server_id == "server1"
    assert response.events[2].resource_id == "tool1"

    # Check error details in the most recent event
    assert response.events[0].success is False
    assert response.events[0].error_message == "Test error"

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
        assert monitor._initialized is True

        # Close the connection
        await monitor.close()


@pytest.mark.asyncio
async def test_raw_request_response(temp_db_path):
    """Test tracking events with raw request and response data"""
    monitor = SQLiteAccessMonitor(db_path=temp_db_path)
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

    # Query the database using the monitor's query_events method
    response = await monitor.query_events("1d", 1, 10)

    # Check that the event was recorded
    assert len(response.events) == 1
    event = response.events[0]

    # Check the raw data was stored correctly
    assert event.raw_request is not None
    assert event.raw_response is not None

    # Check content
    assert "method" in event.raw_request  # raw_request
    assert "params" in event.raw_request
    assert "result" in event.raw_response  # raw_response
    assert "data" in event.raw_response

    # Close the connection
    await monitor.close()


@pytest.mark.asyncio
async def test_backward_compatibility(temp_db_path):
    """Test that the backward compatibility view works"""
    monitor = SQLiteAccessMonitor(db_path=temp_db_path)
    await monitor.initialize_storage()

    # Track an event
    await monitor.track_event(
        event_type=AccessEventType.TOOL_INVOCATION,
        server_id="test-server",
        resource_id="test-tool",
        success=True,
    )

    # Query using the monitor's query_events method (backward compatibility is handled internally)
    response = await monitor.query_events("1d", 1, 10)

    assert len(response.events) == 1
    assert response.events[0].event_type == "TOOL_INVOCATION"

    # Close the connection
    await monitor.close()
