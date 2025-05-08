from mcpm.clients.base import ROUTER_SERVER_NAME
from mcpm.core.schema import ServerConfig, SSEServerConfig, STDIOServerConfig


def format_server_url(client: str, profile: str, router_url: str, server_name: str | None = None) -> ServerConfig:
    return SSEServerConfig(
        name=server_name if server_name else ROUTER_SERVER_NAME,
        url=f"{router_url}?/client={client}&profile={profile}",
    )


def format_server_url_with_proxy_param(
    client: str, profile: str, router_url: str, server_name: str | None = None
) -> ServerConfig:
    result = STDIOServerConfig(
        name=server_name if server_name else ROUTER_SERVER_NAME,
        command="uvx",
        args=["mcp-proxy", f"{router_url}?/client={client}&profile={profile}"],
    )
    return result


def format_server_url_with_proxy_headers(
    client: str, profile: str, router_url: str, server_name: str | None = None
) -> ServerConfig:
    result = STDIOServerConfig(
        name=server_name if server_name else ROUTER_SERVER_NAME,
        command="uvx",
        args=["mcp-proxy", router_url, "--headers", "profile", profile],
    )
    return result
