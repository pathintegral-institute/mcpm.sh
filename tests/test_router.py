"""
Tests for the router module
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp import InitializeResult
from mcp.types import ListToolsResult, ServerCapabilities, Tool, ToolsCapability

from mcpm.core.router.client_connection import ServerConnection
from mcpm.router.router import MCPRouter
from mcpm.router.router_config import RouterConfig
from mcpm.schemas.server_config import RemoteServerConfig


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
    # Create a ListToolsResult to be returned directly
    tools_result = ListToolsResult(tools=[mock_tool])
    mock_session.list_tools = AsyncMock(return_value=tools_result)
    # If you have prompts/resources, mock them similarly:
    mock_session.list_prompts = AsyncMock(return_value=MagicMock(prompts=[]))
    mock_session.list_resources = AsyncMock(return_value=MagicMock(resources=[]))
    mock_session.list_resource_templates = AsyncMock(return_value=MagicMock(resourceTemplates=[]))

    mock_conn.session = mock_session
    return mock_conn


@pytest.mark.asyncio
async def test_router_init():
    """Test initializing the router"""
    # Test with default values
    router = MCPRouter()
    assert router.profile_manager is not None
    assert router.watcher is None
    assert router.router_config is not None
    assert router.router_config.strict is False

    # Test with custom values
    config = RouterConfig(api_key="test-api-key", strict=True)
    router = MCPRouter(
        reload_server=True,
        router_config=config,
    )

    assert router.watcher is not None
    assert router.router_config == config
    assert router.router_config.api_key == "test-api-key"
    assert router.router_config.strict is True


@pytest.mark.asyncio
async def test_add_server(mock_server_connection):
    """Test adding a server to the router"""
    router = MCPRouter()

    # Mock get_active_servers to return all server IDs
    def mock_get_active_servers(_profile):
        return list(router.server_sessions.keys())

    # Patch the _patch_handler_func method to use our mock
    with patch.object(router, "_patch_handler_func", wraps=router._patch_handler_func) as mock_patch_handler:
        mock_patch_handler.return_value.get_target_servers = mock_get_active_servers

        server_config = RemoteServerConfig(name="test-server", url="http://localhost:8080/sse")

        with patch("mcpm.core.router.router.ServerConnection", return_value=mock_server_connection):
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
    server_config = RemoteServerConfig(name="unhealthy-server", url="http://localhost:8080/sse")

    mock_conn = MagicMock(spec=ServerConnection)
    mock_conn.healthy.return_value = False

    with patch("mcpm.core.router.router.ServerConnection", return_value=mock_conn):
        with pytest.raises(ValueError, match="Failed to connect to server unhealthy-server"):
            await router.add_server("unhealthy-server", server_config)


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
        mock_patch_handler.return_value.get_target_servers = mock_get_active_servers

        # Setup initial servers with awaitable request_for_shutdown
        mock_old_server = MagicMock(spec=ServerConnection)
        mock_old_server.session = AsyncMock()
        mock_old_server.request_for_shutdown = AsyncMock()

        router.server_sessions = {"old-server": mock_old_server}
        # Initialize capabilities_mapping for the old server
        router.capabilities_mapping = {"old-server": {"tools": True}}

        # Configure new servers
        server_configs = [RemoteServerConfig(name="test-server", url="http://localhost:8080/sse")]

        with patch("mcpm.core.router.router.ServerConnection", return_value=mock_server_connection):
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
    server_configs = [RemoteServerConfig(name="test-server", url="http://localhost:8080/sse")]

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
    with patch("mcpm.router.router.RouterSseTransport") as mock_transport:
        router = MCPRouter(router_config=RouterConfig(auth_enabled=True, api_key="test-api-key"))
        await router.get_sse_server_app()
        mock_transport.assert_called_once()
        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs.get("api_key") == "test-api-key"


@pytest.mark.asyncio
async def test_get_sse_server_app_without_api_key():
    with patch("mcpm.router.router.RouterSseTransport") as mock_transport:
        router = MCPRouter(router_config=RouterConfig(auth_enabled=False, api_key="custom-secret"))
        await router.get_sse_server_app()
        mock_transport.assert_called_once()
        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs.get("api_key") is None
