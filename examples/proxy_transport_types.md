# FastMCP Proxy with Multiple Transport Types

The MCPM FastMCP proxy now supports aggregating servers with different transport types (stdio, HTTP, SSE) into a single unified interface.

## Supported Server Types

### 1. STDIO Servers (Local Command-based)
```yaml
name: local-python-server
command: python
args: ["-m", "my_mcp_server"]
env:
  API_KEY: ${MY_API_KEY}
```

### 2. Remote HTTP/SSE Servers
```yaml
name: remote-api-server
url: https://api.example.com/mcp
headers:
  Authorization: Bearer ${TOKEN}
```

### 3. Custom Server Configurations (Client-Specific)
```yaml
name: custom-websocket-server
config:
  url: wss://ws.example.com/mcp
  transport: websocket
  custom_field: value
```

**Note**: CustomServerConfig is used for parsing non-standard MCP configs from client configuration files (like Claude Desktop, Goose, etc.) and is **not processed by MCPM's proxy system**. These are client-specific configurations that don't go through the proxy.

## Example: Mixed Profile

You can create a profile that combines servers with different transports:

```bash
# Add a local stdio server
mcpm add mcp-server-time --profile mixed-demo

# Add a remote HTTP server (hypothetical)
mcpm client add --global --server remote-weather --url https://weather-api.com/mcp

# Run the profile - FastMCP proxy handles all transport types
mcpm profile run mixed-demo

# Or run in HTTP mode for sharing
mcpm profile run --http mixed-demo
```

## How It Works

1. **STDIO Servers**: The proxy runs the command directly with the specified arguments and environment
2. **HTTP/SSE Servers**: The proxy connects to the remote URL, forwarding headers as needed
3. **Custom Servers**: These are skipped by the proxy system (client-specific configurations)

## Benefits

- **Unified Interface**: Access all servers through a single endpoint
- **Transport Bridging**: Expose HTTP-only servers via stdio or vice versa
- **Authentication**: Add MCPM authentication layer to any server type
- **Monitoring**: Track usage across all server types uniformly

## FastMCP Proxy Configuration

When MCPM creates the FastMCP proxy, it generates a configuration like:

```json
{
  "mcpServers": {
    "local-server": {
      "command": ["python", "-m", "server"],
      "env": {"KEY": "value"}
    },
    "remote-server": {
      "url": "https://api.example.com/mcp",
      "transport": "http",
      "headers": {"Authorization": "Bearer token"}
    }
  }
}
```

**Note**: CustomServerConfig entries are not included in the proxy configuration as they are client-specific and not processed by MCPM's proxy system.

FastMCP handles the complexity of connecting to each supported server type and presents a unified MCP interface.