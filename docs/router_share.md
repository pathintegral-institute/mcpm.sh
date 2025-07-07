# MCPM v2.0 Server Sharing

## Introduction

MCPM v2.0 provides simplified server sharing through secure tunnels. You can share individual servers or entire profiles, allowing others to access your MCP servers remotely through public URLs.

## Share Individual Servers

Share a single server from your global configuration:

```bash
mcpm share SERVER_NAME
mcpm share SERVER_NAME --port 8080
mcpm share SERVER_NAME --subdomain myserver
```

This creates a secure tunnel to your server, generating a public URL that others can use to connect.

## Share Profiles

Share all servers in a profile simultaneously:

```bash
mcpm profile share PROFILE_NAME
mcpm profile share web-dev --port 8080
```

This aggregates all servers in the profile and makes them available through a single endpoint.

## How It Works

MCPM v2.0 uses FastMCP for server aggregation and secure tunneling:

1. **Server Execution**: Servers run directly via stdio or HTTP
2. **Aggregation**: Multiple servers can be combined into a single endpoint
3. **Tunneling**: Secure tunnels expose local servers to the internet
4. **Authentication**: Optional authentication for secure access

## Authentication

Protect shared servers with authentication:

```bash
mcpm share SERVER_NAME --auth
mcpm profile share PROFILE_NAME --auth
```

This generates authentication tokens that must be included when connecting to shared servers.

## Local-Only Sharing

For development and testing, share servers locally without public tunnels:

```bash
mcpm share SERVER_NAME --local-only
mcpm run SERVER_NAME --http --port 8080
```

## Examples

### Basic Server Sharing
```bash
# Install and share a server
mcpm install mcp-server-browse
mcpm share mcp-server-browse

# Share with custom settings
mcpm share mcp-server-browse --port 9000 --subdomain browse
```

### Profile Sharing
```bash
# Create a profile and share it
mcpm profile create web-dev
mcpm profile edit web-dev  # Add servers interactively
mcpm profile share web-dev
```

### Development Workflow
```bash
# Test locally first
mcpm run my-server --http --port 8080

# Share publicly when ready
mcpm share my-server --port 8080
```

## Client Connection

Clients can connect to shared servers using the provided URL:

```json
{
  "mcpServers": {
    "shared-server": {
      "command": ["curl"],
      "args": ["-X", "POST", "https://shared-url.example.com"]
    }
  }
}
```

## Security Considerations

- **Authentication**: Use `--auth` for sensitive servers
- **Network Access**: Shared servers are publicly accessible
- **Resource Usage**: Monitor server resource consumption
- **Access Control**: Only share servers with trusted users

## Troubleshooting

**Share command fails**
- Check that the server exists: `mcpm ls`
- Verify server configuration: `mcpm inspect SERVER_NAME`
- Test local execution: `mcpm run SERVER_NAME`

**Connection issues**
- Verify the shared URL is accessible
- Check authentication tokens if using `--auth`
- Ensure the server is still running locally

**Profile sharing problems**
- Check profile exists: `mcpm profile ls`
- Verify profile has servers: `mcpm profile ls PROFILE_NAME`
- Test profile execution: `mcpm profile run PROFILE_NAME`

## Migration from v1 Router

If you were using the v1 router system:

### Before (v1)
```bash
mcpm router start
mcpm router share --profile web-dev
```

### After (v2)
```bash
mcpm profile share web-dev
```

The v2.0 sharing system eliminates the need for a separate router daemon, providing direct and more reliable sharing capabilities.