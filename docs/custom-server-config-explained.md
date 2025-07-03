# Understanding CustomServerConfig in MCPM

## What is CustomServerConfig?

`CustomServerConfig` is a flexible server configuration type in MCPM that allows for arbitrary, non-standard server configurations. It's designed to support future extensibility and edge cases that don't fit into the standard STDIO or Remote server models.

## Structure

```python
class CustomServerConfig(BaseServerConfig):
    config: Dict[str, Any]
```

- Inherits from `BaseServerConfig` (provides `name` and `profile_tags`)
- Has a single `config` field that can contain any dictionary structure

## Purpose and Use Cases

### 1. **Future-Proofing**
CustomServerConfig allows MCPM to support new server types without changing the core schema. For example:
- WebSocket-based MCP servers
- Custom transport protocols
- Proprietary server implementations

### 2. **Client-Specific Configurations**
Different MCP clients might have unique configuration requirements:
```python
# Example: A hypothetical WebSocket server
CustomServerConfig(
    name="websocket-server",
    config={
        "url": "wss://example.com/mcp",
        "transport": "websocket",
        "reconnect": True,
        "ping_interval": 30
    }
)
```

### 3. **Built-in or Special Servers**
In the Goose client integration, CustomServerConfig is used for "builtin" type servers:
```python
# From goose.py client manager
elif isinstance(server_config, CustomServerConfig):
    result = dict(server_config.config)
    result["type"] = "builtin"
```

## How It Works in the FastMCP Proxy

When the FastMCP proxy encounters a CustomServerConfig, it passes the entire `config` dictionary directly to FastMCP:

```python
elif isinstance(server, CustomServerConfig):
    # CustomServerConfig - pass through the custom config
    proxy_config["mcpServers"][server.name] = server.config
```

This allows FastMCP to handle any configuration format it supports, including:
- Custom transports
- Special authentication methods
- Non-standard connection parameters

## Example Usage Scenarios

### 1. WebSocket Server
```yaml
name: realtime-data
config:
  url: wss://data.example.com/mcp
  transport: websocket
  auth_token: ${WEBSOCKET_TOKEN}
  reconnect_delay: 5000
```

### 2. Plugin-Based Server
```yaml
name: plugin-server
config:
  type: plugin
  module: mcp_plugins.analytics
  class: AnalyticsServer
  options:
    cache_size: 1000
    refresh_rate: 60
```

### 3. Embedded Server
```yaml
name: embedded-llm
config:
  type: embedded
  model_path: /models/local-llm
  gpu_layers: 32
  context_size: 4096
```

## Current Implementation Status

As of now, CustomServerConfig is:
- ✅ Defined in the schema
- ✅ Supported by the FastMCP proxy
- ✅ Handled by client managers (like Goose)
- ⚠️ Not yet used in practice by MCPM commands

## Why It Exists

1. **Extensibility**: Allows MCPM to support new server types without breaking changes
2. **Flexibility**: Clients can define their own server configuration formats
3. **Forward Compatibility**: Future MCP transport types can be supported
4. **Special Cases**: Handles edge cases that don't fit STDIO or HTTP/SSE models

## Integration with FastMCP

FastMCP's proxy system is designed to handle arbitrary configurations. When it receives a CustomServerConfig, it:
1. Extracts the `config` dictionary
2. Passes it directly to FastMCP's configuration system
3. FastMCP interprets the configuration based on its own rules

This design allows MCPM to be transport-agnostic while still providing structured configuration for known transport types (STDIO and Remote).

## Future Possibilities

CustomServerConfig opens the door for:
- gRPC-based MCP servers
- Message queue-based servers (RabbitMQ, Kafka)
- In-process servers (Python modules loaded directly)
- Cloud-native integrations (Lambda, Cloud Functions)
- Custom authentication schemes
- Load-balanced server pools

The key insight is that CustomServerConfig is MCPM's escape hatch for innovation - it ensures the tool can adapt to new MCP server types without requiring schema changes.