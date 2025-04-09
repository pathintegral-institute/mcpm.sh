# MCPM Router

The MCPM Router is a module that allows you to aggregate multiple MCP servers (both SSE and STDIO) and expose them as a single SSE server.

## Features

- Aggregate multiple MCP servers as a single server
- Support both SSE and STDIO connections to underlying servers
- Namespace capabilities from different servers
- Expose a unified SSE server interface

## Usage

### Basic Usage

```python
import asyncio
from mcpm.router import MCPRouter
from mcpm.schema.server_config import STDIOServerConfig, SSEServerConfig

async def main():
    # Create a router
    router = MCPRouter()

    # Add a STDIO server
    await router.add_server(
        "example1",
        STDIOServerConfig(
            command="python",
            args=["-m", "mcp.examples.simple_server"]
        )
    )

    # Add an SSE server
    await router.add_server(
        "example2",
        SSEServerConfig(
            url="http://localhost:3000/sse"
        )
    )

    # Start the SSE server
    await router.start_sse_server(host="localhost", port=8080)

if __name__ == "__main__":
    asyncio.run(main())
```
### Configuration File
by default we use the configure from file `~/.config/mcpm/profile.json` to manage the servers.

## Implementation Details

The router works by:

1. Connecting to each downstream server (SSE or STDIO)
2. Collecting capabilities, tools, prompts, and resources from each server
3. Namespacing these capabilities to avoid conflicts
4. Creating an aggregated server that routes requests to the appropriate downstream server
5. Exposing this aggregated server as an SSE server

## Namespacing

The router uses the following namespacing conventions:

- Tools: `{server_name}_t_{tool_name}`
- Prompts: `{server_name}_p_{prompt_name}`
- Resources: `{server_name}:{resource_uri}`

This allows the router to route requests to the appropriate server based on the namespaced identifier.
