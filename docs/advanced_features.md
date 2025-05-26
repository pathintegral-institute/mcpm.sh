# MCPM Router

The MCPM Router is a module that allows you to aggregate multiple MCP servers (both SSE and STDIO) and expose them as a single SSE server. The router acts in a dual role:

1. **As an MCP Client**: Connects to multiple downstream MCP servers
2. **As an MCP Server**: Provides a unified interface to upstream MCP clients

This design allows for aggregation of capabilities from multiple MCP servers while providing a single, stable connection point for clients. The router also supports profile management to control which servers are available to specific clients.

A key benefit of the MCPM Router is that it maintains persistent connections to MCP servers, allowing multiple clients to share these server sessions. This eliminates the need to start separate server instances for each client, significantly reducing resource usage and startup time.

## How It Works

The MCPM Router sits between your clients and multiple MCP servers, acting as a central hub:

```mermaid
flowchart TD
    %% Clients
    client1[Claude Desktop<br>Profile: Study]
    client2[Cursor<br>Profile: Development]
    client3[Goose<br>Profile: Creativity]
    
    %% Router with profiles inside
    subgraph router[MCPM Router]
        subgraph profiles[Profiles]
            studyProfile[Study Profile]
            devProfile[Development Profile]
            creativeProfile[Creativity Profile]
        end
    end
    
    %% Servers - concrete examples
    server1[Notion MCP Server]
    server2[Python Interpreter MCP Server]
    server3[Image Generation MCP Server]
    server4[Web Search MCP Server]
    server5[Web Fetch MCP Server]
    server6[Blender MCP Server]
    server7[Slack MCP Server]
    
    %% Client to profile connections directly
    client1 --> studyProfile
    client2 --> devProfile
    client3 --> creativeProfile
    
    %% Profile to server access
    studyProfile --> server1
    studyProfile --> server4
    studyProfile --> server5
    
    devProfile --> server1
    devProfile --> server2
    devProfile --> server4
    devProfile --> server5
    devProfile --> server7
    
    creativeProfile --> server1
    creativeProfile --> server3
    creativeProfile --> server6
    
    %% Styling
    classDef client fill:#d4f1f9,stroke:#333,stroke-width:1px;
    classDef router fill:#ffcc99,stroke:#333,stroke-width:1px;
    classDef server fill:#d5e8d4,stroke:#333,stroke-width:1px;
    classDef profile fill:#e1d5e7,stroke:#333,stroke-width:1px;
    
    class client1,client2,client3 client;
    class router router;
    class server1,server2,server3,server4,server5,server6,server7 server;
    class studyProfile,devProfile,creativeProfile,profiles profile;
```

### Key Concepts

#### 1. Unified Access
Clients connect only to the router, not directly to servers. The router provides a single endpoint for accessing capabilities from all connected servers.

#### 2. Profiles
Profiles are configurations within the router that determine which servers' capabilities are exposed to each client:

| Client         | Profile     | Available Servers                                        |
| -------------- | ----------- | -------------------------------------------------------- |
| Claude Desktop | Study       | Notion, Web Search, Web Fetch                            |
| Cursor         | Development | Notion, Python Interpreter, Web Search, Web Fetch, Slack |
| Goose          | Creativity  | Notion, Image Generation, Blender                        |

#### 3. Namespacing
The router prefixes capabilities from different servers to avoid conflicts:
- Tools: `notion_t_pageSearch` or `python_t_executeCode`
- Prompts: `image_p_generatePortrait`
- Resources: `webfetch:https://example.com`

#### 4. Server Connections
The router supports both STDIO (command-line) and Remote (HTTP and SSE) server connections. For example:
- STDIO: Python Interpreter, Blender
- Remote: Web Search, Notion, Slack

#### 5. Shared Server Sessions
The router maintains persistent connections to all configured servers, allowing multiple clients to share the same server sessions. This means:
- Only one instance of each server is needed regardless of client count
- Server initialization happens only once
- State can be shared across clients when appropriate
- Resources like memory and CPU usage are significantly reduced

## Features

- Aggregate multiple MCP servers as a single server
- Support both Remote and STDIO connections to underlying servers
- Namespace capabilities from different servers
- Expose a unified Remote server interface
- Profile-based server access control
- Dynamic configuration reloading
- Share server connections among multiple clients (no need for separate server instances per client)
- Reduce resource usage through connection pooling