"""Tests for connection_types.py"""

import json

import pytest
from pydantic import ValidationError

from mcpm.router.connection_types import ConnectionDetails, ConnectionType


def test_connection_details_stdio_success():
    """Test successful creation of ConnectionDetails for STDIO."""
    details = ConnectionDetails(type=ConnectionType.STDIO, command="/bin/echo", args=["hello"], env={"VAR": "value"})
    assert details.type == ConnectionType.STDIO
    assert details.command == "/bin/echo"
    assert details.args == ["hello"]
    assert details.env == {"VAR": "value"}
    assert details.url is None


def test_connection_details_sse_success():
    """Test successful creation of ConnectionDetails for SSE."""
    details = ConnectionDetails(type=ConnectionType.SSE, url="http://localhost:8080/events")
    assert details.type == ConnectionType.SSE
    assert details.url == "http://localhost:8080/events"
    assert details.command is None
    assert details.args == []  # Default
    assert details.env is None  # Default


def test_connection_details_stdio_missing_command():
    """Test validation error when command is missing for STDIO."""
    with pytest.raises(ValidationError, match="'command' is required for stdio"):
        ConnectionDetails(type=ConnectionType.STDIO)  # Missing command


def test_connection_details_sse_missing_url():
    """Test validation error when url is missing for SSE."""
    with pytest.raises(ValidationError, match="'url' is required for sse"):
        ConnectionDetails(type=ConnectionType.SSE)  # Missing url


def test_connection_details_defaults():
    """Test default values for optional fields."""
    details_stdio = ConnectionDetails(type=ConnectionType.STDIO, command="test")
    assert details_stdio.args == []
    assert details_stdio.env is None

    details_sse = ConnectionDetails(type=ConnectionType.SSE, url="test")
    assert details_sse.args == []
    assert details_sse.env is None
    assert details_sse.command is None


def test_connection_type_coercion():
    """Test that Pydantic coerces string to Enum."""
    details = ConnectionDetails(type="stdio", command="/bin/ls")
    assert details.type == ConnectionType.STDIO

    details = ConnectionDetails(type="sse", url="http://example.com")
    assert details.type == ConnectionType.SSE


def test_connection_type_coercion_invalid():
    """Test validation error for invalid connection type string."""
    with pytest.raises(ValidationError):
        ConnectionDetails(type="invalid_type", command="test")


def test_json_serialization_stdio():
    """Test JSON serialization of ConnectionDetails for STDIO."""
    details = ConnectionDetails(type=ConnectionType.STDIO, command="/bin/echo", args=["hello"], env={"VAR": "value"})
    json_str = details.model_dump_json()
    parsed = json.loads(json_str)

    assert parsed["type"] == "stdio"
    assert parsed["command"] == "/bin/echo"
    assert parsed["args"] == ["hello"]
    assert parsed["env"] == {"VAR": "value"}
    assert "url" in parsed and parsed["url"] is None


def test_json_serialization_sse():
    """Test JSON serialization of ConnectionDetails for SSE."""
    details = ConnectionDetails(type=ConnectionType.SSE, url="http://localhost:8080/events")
    json_str = details.model_dump_json()
    parsed = json.loads(json_str)

    assert parsed["type"] == "sse"
    assert parsed["url"] == "http://localhost:8080/events"
    assert "command" in parsed and parsed["command"] is None
    assert parsed["args"] == []
    assert "env" in parsed and parsed["env"] is None


def test_json_deserialization_stdio():
    """Test JSON deserialization to ConnectionDetails for STDIO."""
    json_str = '{"type": "stdio", "command": "/bin/echo", "args": ["hello"], "env": {"VAR": "value"}, "url": null}'
    details = ConnectionDetails.model_validate_json(json_str)

    assert details.type == ConnectionType.STDIO
    assert details.command == "/bin/echo"
    assert details.args == ["hello"]
    assert details.env == {"VAR": "value"}
    assert details.url is None


def test_json_deserialization_sse():
    """Test JSON deserialization to ConnectionDetails for SSE."""
    json_str = '{"type": "sse", "url": "http://localhost:8080/events", "command": null, "args": [], "env": null}'
    details = ConnectionDetails.model_validate_json(json_str)

    assert details.type == ConnectionType.SSE
    assert details.url == "http://localhost:8080/events"
    assert details.command is None
    assert details.args == []
    assert details.env is None


def test_json_roundtrip_stdio():
    """Test full JSON serialization and deserialization roundtrip for STDIO."""
    original = ConnectionDetails(type=ConnectionType.STDIO, command="/bin/echo", args=["hello"], env={"VAR": "value"})
    json_str = original.model_dump_json()
    deserialized = ConnectionDetails.model_validate_json(json_str)

    assert deserialized.type == original.type
    assert deserialized.command == original.command
    assert deserialized.args == original.args
    assert deserialized.env == original.env
    assert deserialized.url == original.url


def test_json_roundtrip_sse():
    """Test full JSON serialization and deserialization roundtrip for SSE."""
    original = ConnectionDetails(type=ConnectionType.SSE, url="http://localhost:8080/events")
    json_str = original.model_dump_json()
    deserialized = ConnectionDetails.model_validate_json(json_str)

    assert deserialized.type == original.type
    assert deserialized.url == original.url
    assert deserialized.command == original.command
    assert deserialized.args == original.args
    assert deserialized.env == original.env
