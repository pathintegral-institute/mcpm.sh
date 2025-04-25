"""
Tests for the router module
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from mcp import InitializeResult
from mcp.types import ListToolsResult, ServerCapabilities, ServerResult, Tool, ToolsCapability

from mcpm.router.client_connection import ServerConnection
from mcpm.router.router import MCPRouter
from mcpm.schemas.server_config import SSEServerConfig
from mcpm.utils.config import TOOL_SPLITOR


@pytest.fixture
def mock_server_connection():
    """Create a mock server connection for testing"""
    mock_conn = MagicMock(spec=ServerConnection)
    mock_conn.healthy.return_value = True
    mock_conn.request_for_shutdown = AsyncMock()

    # Create valid ServerCapabilities with ToolsCapability
    tools_capability = ToolsCapability(listChanged=False)
    capabilities = ServerCapabilities(
        prompts=None, resources=None, tools=tools_capability, logging=None, experimental={}
    )

    # Mock session initialized response
    mock_conn.session_initialized_response = InitializeResult(
        protocolVersion="1.0", capabilities=capabilities, serverInfo={"name": "test-server", "version": "1.0.0"}
    )

    # Mock session
    mock_session = AsyncMock()
    # Create a valid tool with proper inputSchema structure
    mock_tool = Tool(name="test-tool", description="A test tool", inputSchema={"type": "object", "properties": {}})
    # Create a ListToolsResult to be the root of ServerResult
    tools_result = ListToolsResult(tools=[mock_tool])
    # Create a ServerResult with ListToolsResult as its root
    mock_list_tools_result = ServerResult(root=tools_result)
    mock_session.list_tools = AsyncMock(return_value=mock_list_tools_result)
    mock_conn.session = mock_session

    return mock_conn


@pytest.mark.asyncio
async def test_router_init():
    """Test initializing the router"""
    # Test with default values
    router = MCPRouter()
    assert router.profile_manager is not None
    assert router.watcher is None
    assert router.strict is False
    assert router.api_key is None
    assert router.router_config is None

    # Test with custom values
    router_config = {"host": "custom-host", "port": 9000}
    router = MCPRouter(
        reload_server=True,
        strict=True,
        api_key="test-api-key",
        router_config=router_config,
    )

    assert router.watcher is not None
    assert router.strict is True
    assert router.api_key == "test-api-key"
    assert router.router_config == router_config


def test_create_global_config():
    """Test creating a global config from router config"""
    router_config = {"host": "custom-host", "port": 9000, "share_address": "custom-share-address"}

    with patch("mcpm.router.router.ConfigManager") as mock_config_manager:
        mock_instance = Mock()
        mock_config_manager.return_value = mock_instance

        # Test without API key
        router = MCPRouter(router_config=router_config)
        router.create_global_config()
        mock_instance.save_share_config.assert_not_called()
        mock_instance.save_router_config.assert_not_called()

        # Test with API key
        router = MCPRouter(api_key="test-api-key", router_config=router_config)
        router.create_global_config()
        mock_instance.save_share_config.assert_called_once_with(api_key="test-api-key")
        mock_instance.save_router_config.assert_called_once_with("custom-host", 9000, "custom-share-address")


@pytest.mark.asyncio
async def test_add_server(mock_server_connection):
    """Test adding a server to the router"""
    router = MCPRouter()

    # Mock get_active_servers to return all server IDs
    def mock_get_active_servers(_profile):
        return list(router.server_sessions.keys())

    # Patch the _patch_handler_func method to use our mock
    with patch.object(router, "_patch_handler_func", wraps=router._patch_handler_func) as mock_patch_handler:
        mock_patch_handler.return_value.get_active_servers = mock_get_active_servers

        server_config = SSEServerConfig(name="test-server", url="http://localhost:8080/sse")

        with patch("mcpm.router.router.ServerConnection", return_value=mock_server_connection):
            await router.add_server("test-server", server_config)

            # Verify server was added
            assert "test-server" in router.server_sessions
            assert router.server_sessions["test-server"] == mock_server_connection

            # Verify capabilities were stored
            assert "test-server" in router.capabilities_mapping

            # Verify tool was stored
            assert "test-tool" in router.tools_mapping
            assert router.capabilities_to_server_id["tools"]["test-tool"] == "test-server"

            # Test adding duplicate server
            with pytest.raises(ValueError):
                await router.add_server("test-server", server_config)


@pytest.mark.asyncio
async def test_add_server_unhealthy():
    """Test adding an unhealthy server"""
    router = MCPRouter()
    server_config = SSEServerConfig(name="unhealthy-server", url="http://localhost:8080/sse")

    mock_conn = MagicMock(spec=ServerConnection)
    mock_conn.healthy.return_value = False

    with patch("mcpm.router.router.ServerConnection", return_value=mock_conn):
        with pytest.raises(ValueError, match="Failed to connect to server unhealthy-server"):
            await router.add_server("unhealthy-server", server_config)


@pytest.mark.asyncio
async def test_add_server_duplicate_tool_strict():
    """Test adding a server with duplicate tool name in strict mode"""
    router = MCPRouter(strict=True)

    # Mock get_active_servers to return all server IDs
    def mock_get_active_servers(_profile):
        return list(router.server_sessions.keys())

    # Patch the _patch_handler_func method to use our mock
    with patch.object(router, "_patch_handler_func", wraps=router._patch_handler_func) as mock_patch_handler:
        mock_patch_handler.return_value.get_active_servers = mock_get_active_servers

        server_config = SSEServerConfig(name="test-server", url="http://localhost:8080/sse")

        # Add first server with a tool
        mock_conn1 = MagicMock(spec=ServerConnection)
        mock_conn1.healthy.return_value = True
        mock_conn1.request_for_shutdown = AsyncMock()

        # Create valid ServerCapabilities with ToolsCapability
        tools_capability = ToolsCapability(listChanged=False)
        capabilities = ServerCapabilities(
            prompts=None, resources=None, tools=tools_capability, logging=None, experimental={}
        )

        mock_conn1.session_initialized_response = InitializeResult(
            protocolVersion="1.0", capabilities=capabilities, serverInfo={"name": "test-server", "version": "1.0.0"}
        )

        mock_session1 = AsyncMock()
        mock_tool = Tool(
            name="duplicate-tool", description="A test tool", inputSchema={"type": "object", "properties": {}}
        )
        # Create a ListToolsResult to be the root of ServerResult
        tools_result = ListToolsResult(tools=[mock_tool])
        # Create a ServerResult with ListToolsResult as its root
        mock_list_tools_result = ServerResult(root=tools_result)
        mock_session1.list_tools = AsyncMock(return_value=mock_list_tools_result)
        mock_conn1.session = mock_session1

        # Add second server with same tool name
        mock_conn2 = MagicMock(spec=ServerConnection)
        mock_conn2.healthy.return_value = True
        mock_conn2.request_for_shutdown = AsyncMock()

        mock_conn2.session_initialized_response = InitializeResult(
            protocolVersion="1.0", capabilities=capabilities, serverInfo={"name": "second-server", "version": "1.0.0"}
        )

        mock_session2 = AsyncMock()
        mock_session2.list_tools = AsyncMock(return_value=mock_list_tools_result)
        mock_conn2.session = mock_session2

        with patch("mcpm.router.router.ServerConnection", side_effect=[mock_conn1, mock_conn2]):
            # Add first server should succeed
            await router.add_server("test-server", server_config)

            # Add second server with duplicate tool should fail in strict mode
            with pytest.raises(ValueError, match="Tool duplicate-tool already exists"):
                await router.add_server("second-server", server_config)


@pytest.mark.asyncio
async def test_add_server_duplicate_tool_non_strict():
    """Test adding a server with duplicate tool name in non-strict mode"""
    router = MCPRouter(strict=False)

    # Mock get_active_servers to return all server IDs
    def mock_get_active_servers(_profile):
        return list(router.server_sessions.keys())

    # Patch the _patch_handler_func method to use our mock
    with patch.object(router, "_patch_handler_func", wraps=router._patch_handler_func) as mock_patch_handler:
        mock_patch_handler.return_value.get_active_servers = mock_get_active_servers

        server_config = SSEServerConfig(name="test-server", url="http://localhost:8080/sse")
        second_server_config = SSEServerConfig(name="second-server", url="http://localhost:8081/sse")

        # Add first server with a tool
        mock_conn1 = MagicMock(spec=ServerConnection)
        mock_conn1.healthy.return_value = True
        mock_conn1.request_for_shutdown = AsyncMock()

        # Create valid ServerCapabilities with ToolsCapability
        tools_capability = ToolsCapability(listChanged=False)
        capabilities = ServerCapabilities(
            prompts=None, resources=None, tools=tools_capability, logging=None, experimental={}
        )

        mock_conn1.session_initialized_response = InitializeResult(
            protocolVersion="1.0", capabilities=capabilities, serverInfo={"name": "test-server", "version": "1.0.0"}
        )

        mock_session1 = AsyncMock()
        mock_tool = Tool(
            name="duplicate-tool", description="A test tool", inputSchema={"type": "object", "properties": {}}
        )
        # Create a ListToolsResult to be the root of ServerResult
        tools_result = ListToolsResult(tools=[mock_tool])
        # Create a ServerResult with ListToolsResult as its root
        mock_list_tools_result = ServerResult(root=tools_result)
        mock_session1.list_tools = AsyncMock(return_value=mock_list_tools_result)
        mock_conn1.session = mock_session1

        # Add second server with same tool name
        mock_conn2 = MagicMock(spec=ServerConnection)
        mock_conn2.healthy.return_value = True
        mock_conn2.request_for_shutdown = AsyncMock()

        mock_conn2.session_initialized_response = InitializeResult(
            protocolVersion="1.0", capabilities=capabilities, serverInfo={"name": "second-server", "version": "1.0.0"}
        )

        mock_session2 = AsyncMock()
        mock_session2.list_tools = AsyncMock(return_value=mock_list_tools_result)
        mock_conn2.session = mock_session2

        with patch("mcpm.router.router.ServerConnection", side_effect=[mock_conn1, mock_conn2]):
            # Add first server
            await router.add_server("test-server", server_config)
            assert "duplicate-tool" in router.tools_mapping
            assert router.capabilities_to_server_id["tools"]["duplicate-tool"] == "test-server"

            # Add second server with duplicate tool - should prefix the tool name
            await router.add_server("second-server", second_server_config)
            prefixed_tool_name = f"second-server{TOOL_SPLITOR}duplicate-tool"
            assert prefixed_tool_name in router.capabilities_to_server_id["tools"]
            assert router.capabilities_to_server_id["tools"][prefixed_tool_name] == "second-server"


@pytest.mark.asyncio
async def test_remove_server():
    """Test removing a server from the router"""
    router = MCPRouter()

    # Setup mock server session with an awaitable request_for_shutdown
    mock_session = AsyncMock()
    mock_session.close = AsyncMock()

    mock_server = MagicMock(spec=ServerConnection)
    mock_server.session = mock_session
    mock_server.request_for_shutdown = AsyncMock()

    # Mock server and capabilities
    router.server_sessions = {"test-server": mock_server}
    router.capabilities_mapping = {"test-server": {"tools": True}}
    router.capabilities_to_server_id = {"tools": {"test-tool": "test-server"}}
    router.tools_mapping = {"test-tool": MagicMock()}

    # Remove server
    await router.remove_server("test-server")

    # Verify server was removed
    assert "test-server" not in router.server_sessions
    assert "test-server" not in router.capabilities_mapping
    assert "test-tool" not in router.capabilities_to_server_id["tools"]
    assert "test-tool" not in router.tools_mapping

    # Verify request_for_shutdown was called
    mock_server.request_for_shutdown.assert_called_once()

    # Test removing non-existent server
    with pytest.raises(ValueError, match="Server with ID non-existent does not exist"):
        await router.remove_server("non-existent")


@pytest.mark.asyncio
async def test_update_servers(mock_server_connection):
    """Test updating servers based on configuration"""
    router = MCPRouter()

    # Mock get_active_servers to return all server IDs
    def mock_get_active_servers(_profile):
        return list(router.server_sessions.keys())

    # Patch the _patch_handler_func method to use our mock
    with patch.object(router, "_patch_handler_func", wraps=router._patch_handler_func) as mock_patch_handler:
        mock_patch_handler.return_value.get_active_servers = mock_get_active_servers

        # Setup initial servers with awaitable request_for_shutdown
        mock_old_server = MagicMock(spec=ServerConnection)
        mock_old_server.session = AsyncMock()
        mock_old_server.request_for_shutdown = AsyncMock()

        router.server_sessions = {"old-server": mock_old_server}
        # Initialize capabilities_mapping for the old server
        router.capabilities_mapping = {"old-server": {"tools": True}}

        # Configure new servers
        server_configs = [SSEServerConfig(name="test-server", url="http://localhost:8080/sse")]

        with patch("mcpm.router.router.ServerConnection", return_value=mock_server_connection):
            await router.update_servers(server_configs)

            # Verify old server was removed
            assert "old-server" not in router.server_sessions
            mock_old_server.request_for_shutdown.assert_called_once()

            # Verify new server was added
            assert "test-server" in router.server_sessions

        # Test with empty configs - should not change anything
        router.server_sessions = {"test-server": mock_server_connection}
        await router.update_servers([])
        assert "test-server" in router.server_sessions


@pytest.mark.asyncio
async def test_update_servers_error_handling():
    """Test error handling during server updates"""
    router = MCPRouter()

    # Setup initial servers with awaitable request_for_shutdown
    mock_old_server = MagicMock(spec=ServerConnection)
    mock_old_server.session = AsyncMock()
    mock_old_server.request_for_shutdown = AsyncMock()

    router.server_sessions = {"old-server": mock_old_server}
    # Initialize capabilities_mapping for the old server
    router.capabilities_mapping = {"old-server": {"tools": True}}

    # Configure new servers
    server_configs = [SSEServerConfig(name="test-server", url="http://localhost:8080/sse")]

    # Mock add_server to raise exception
    with patch.object(router, "add_server", side_effect=Exception("Test error")):
        # Should not raise exception
        await router.update_servers(server_configs)

        # Old server should still be removed
        assert "old-server" not in router.server_sessions
        mock_old_server.request_for_shutdown.assert_called_once()

        # New server should not be added
        assert "test-server" not in router.server_sessions


@pytest.mark.asyncio
async def test_router_sse_transport_no_api_key():
    """Test RouterSseTransport with no API key (authentication disabled)"""

    from mcpm.router.transport import RouterSseTransport

    # Create a RouterSseTransport with no API key
    transport = RouterSseTransport("/messages/", api_key=None)

    # Create a mock scope
    mock_scope = {"type": "http"}

    # Test _validate_api_key method directly
    assert transport._validate_api_key(mock_scope, api_key=None)
    assert transport._validate_api_key(mock_scope, api_key="any-key")

    # Test with various API key values - all should be allowed
    assert transport._validate_api_key(mock_scope, api_key="test-key")
    assert transport._validate_api_key(mock_scope, api_key="invalid-key")
    assert transport._validate_api_key(mock_scope, api_key="")


@pytest.mark.asyncio
async def test_router_sse_transport_with_api_key():
    """Test RouterSseTransport with API key (authentication enabled)"""

    from mcpm.router.transport import RouterSseTransport

    # Create a RouterSseTransport with an API key
    transport = RouterSseTransport("/messages/", api_key="correct-api-key")

    # Create a mock scope
    mock_scope = {"type": "http"}

    # Test _validate_api_key method directly
    # With the correct API key
    assert transport._validate_api_key(mock_scope, api_key="correct-api-key")

    # With an incorrect API key
    assert not transport._validate_api_key(mock_scope, api_key="wrong-api-key")

    # With no API key
    assert not transport._validate_api_key(mock_scope, api_key=None)

    # Test with empty string
    assert not transport._validate_api_key(mock_scope, api_key="")


@pytest.mark.asyncio
async def test_get_sse_server_app_with_api_key():
    """Test that the API key is passed to RouterSseTransport when creating the server app"""
    router = MCPRouter(api_key="test-api-key")

    # Patch the RouterSseTransport constructor and get_active_servers method
    with (
        patch("mcpm.router.router.RouterSseTransport") as mock_transport,
        patch.object(router, "_patch_handler_func", wraps=router._patch_handler_func) as mock_patch_handler,
    ):
        # Set up mocks for initialization
        def mock_get_active_servers(_profile):
            return list(router.server_sessions.keys())

        mock_patch_handler.return_value.get_active_servers = mock_get_active_servers

        # Call the method
        await router.get_sse_server_app()

        # Check that RouterSseTransport was created with the correct API key
        mock_transport.assert_called_once()
        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs.get("api_key") == "test-api-key"


@pytest.mark.asyncio
async def test_get_sse_server_app_without_api_key():
    """Test that None is passed to RouterSseTransport when no API key is provided"""
    router = MCPRouter()  # No API key

    # Patch the RouterSseTransport constructor and get_active_servers method
    with (
        patch("mcpm.router.router.RouterSseTransport") as mock_transport,
        patch.object(router, "_patch_handler_func", wraps=router._patch_handler_func) as mock_patch_handler,
    ):
        # Set up mocks for initialization
        def mock_get_active_servers(_profile):
            return list(router.server_sessions.keys())

        mock_patch_handler.return_value.get_active_servers = mock_get_active_servers

        # Call the method
        await router.get_sse_server_app()

        # Check that RouterSseTransport was created with api_key=None
        mock_transport.assert_called_once()
        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs.get("api_key") is None
