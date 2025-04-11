from mcpm.clients.base import ROUTER_SERVER_NAME
from mcpm.schemas.server_config import ServerConfig, SSEServerConfig, STDIOServerConfig


def format_server_url(client: str, profile: str, router_url: str) -> ServerConfig:
    return SSEServerConfig(
        name=ROUTER_SERVER_NAME,
        url=f"{router_url}?/client={client}&profile={profile}",
    )


def format_server_url_with_proxy_param(client: str, profile: str, router_url: str) -> ServerConfig:
    result = STDIOServerConfig(
        name=ROUTER_SERVER_NAME,
        command="uvx",
        args=["mcp-proxy", f"{router_url}?/client={client}&profile={profile}"],
    )
    return result


def format_server_url_with_proxy_headers(client: str, profile: str, router_url: str) -> ServerConfig:
    result = STDIOServerConfig(
        name=ROUTER_SERVER_NAME,
        command="uvx",
        args=["mcp-proxy", router_url, "--headers", "profile", profile],
    )
    return result
