from mcpm.core.schema import RemoteServerConfig, ServerConfig, STDIOServerConfig


def format_server_url(client: str, profile: str, router_url: str, server_name: str | None = None) -> ServerConfig:
    return RemoteServerConfig(
        name=server_name if server_name else profile,
        # Correct query parameters.
        url=f"{router_url}?client={client}&profile={profile}",
    )


def format_server_url_with_proxy_param(
    client: str, profile: str, router_url: str, server_name: str | None = None
) -> ServerConfig:
    result = STDIOServerConfig(
        name=server_name if server_name else profile,
        command="uvx",
        args=["mcp-proxy", f"{router_url}?client={client}&profile={profile}"],
    )
    return result


def format_server_url_with_proxy_headers(
    client: str, profile: str, router_url: str, server_name: str | None = None
) -> ServerConfig:
    result = STDIOServerConfig(
        name=server_name if server_name else profile,
        command="uvx",
        args=["mcp-proxy", router_url, "--headers", "profile", profile],
    )
    return result
