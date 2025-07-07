# MCPM v2.0 Advanced Features

MCPM v2.0 provides advanced capabilities for power users, including server aggregation, sharing, analytics, and client integration. This document covers features beyond basic server management.

## FastMCP Integration

MCPM v2.0 uses FastMCP for server aggregation and advanced execution capabilities:

### Profile Aggregation

Execute multiple servers simultaneously through profiles:

```bash
# Create a development profile
mcpm profile create web-dev
mcpm profile edit web-dev  # Add: browse, git, filesystem servers

# Run all servers in profile together
mcpm profile run web-dev --http --port 8080
```

This aggregates all servers in the profile into a single endpoint, allowing clients to access multiple server capabilities through one connection.

### Server Namespacing

When multiple servers are aggregated, FastMCP automatically namespaces capabilities to avoid conflicts:

- **Tools**: `browse_t_getPage`, `git_t_commitChanges`
- **Prompts**: `filesystem_p_listFiles`
- **Resources**: Prefixed by server name

## Server Sharing and Tunneling

### Individual Server Sharing

Share single servers with secure tunnels:

```bash
mcpm share mcp-server-browse
mcpm share mcp-server-git --port 9000 --subdomain git-server
```

### Profile Sharing

Share entire profiles as aggregated endpoints:

```bash
mcpm profile share web-dev
mcpm profile share ai-tools --auth --port 8080
```

### Authentication and Security

Protect shared servers with authentication:

```bash
# Generate auth token for sharing
mcpm share my-server --auth

# Local-only sharing for development
mcpm share my-server --local-only
```

## Client Integration

### Multi-Client Management

Manage server configurations across multiple MCP clients:

```bash
# List all detected clients
mcpm client ls

# Configure servers for specific clients
mcpm client edit claude-desktop
mcpm client edit cursor
mcpm client edit windsurf
```

### Configuration Import/Export

Import existing server configurations from clients:

```bash
# Import from Claude Desktop
mcpm client import claude-desktop

# Import from Cursor to a specific profile
mcpm client import cursor --profile development
```

## Analytics and Monitoring

### Usage Analytics

Track server usage patterns and performance:

```bash
# View comprehensive usage data
mcpm usage

# Server-specific analytics
mcpm usage --server mcp-server-browse

# Profile usage patterns
mcpm usage --profile web-dev
```

### Health Monitoring

Monitor system and server health:

```bash
# Comprehensive health check
mcpm doctor

# Check specific server health
mcpm doctor --server my-server

# System diagnostics
mcpm doctor --verbose
```

## Development and Testing

### HTTP Mode for Testing

Run servers in HTTP mode for development and testing:

```bash
# Single server HTTP mode
mcpm run my-server --http --port 8080

# Profile HTTP mode with aggregation
mcpm profile run web-dev --http --port 8080
```

### MCP Inspector Integration

Launch MCP Inspector for debugging:

```bash
# Inspect individual servers
mcpm inspect mcp-server-browse

# Inspect entire profiles
mcpm profile inspect web-dev
```

## Configuration Management

### Global Configuration

Manage MCPM settings and preferences:

```bash
# View current configuration
mcpm config

# Edit configuration interactively
mcpm config edit

# Reset to defaults
mcpm config reset
```

### Environment Variables

Control MCPM behavior with environment variables:

```bash
# Custom config directory
export MCPM_CONFIG_DIR="~/.config/mcpm-custom"

# Debug mode
export MCPM_DEBUG=1

# Custom registry URL
export MCPM_REGISTRY_URL="https://custom-registry.example.com"
```

## Performance Optimization

### Server Caching

MCPM automatically caches server metadata and configurations for better performance.

### Connection Pooling

FastMCP maintains connection pools for efficient server communication.

### Resource Management

Monitor and optimize resource usage:

```bash
# View resource usage
mcpm usage --resources

# Clean up unused servers
mcpm doctor --cleanup
```

## Migration from v1

### Router Replacement

v2.0 eliminates the separate router daemon:

```bash
# v1 router commands
mcpm router start
mcpm router share --profile web-dev

# v2 equivalent
mcpm profile share web-dev
```

### Profile System Changes

Profiles are now virtual tags instead of separate configurations:

```bash
# v1 target-based profiles
mcpm target create %web-dev
mcpm add server --target %web-dev

# v2 virtual profiles
mcpm profile create web-dev
mcpm profile edit web-dev  # Interactive server selection
```

## Troubleshooting Advanced Features

### Sharing Issues
- Check network connectivity and firewall settings
- Verify authentication tokens for protected shares
- Test local execution before sharing

### Aggregation Problems
- Ensure all servers in profile are functional
- Check for naming conflicts between servers
- Verify FastMCP compatibility

### Client Integration Issues
- Confirm client is supported and detected
- Check client configuration permissions
- Verify server compatibility with client

### Performance Issues
- Monitor resource usage with `mcpm usage --resources`
- Use `mcpm doctor` for system diagnostics
- Consider reducing concurrent server count

For additional support, see the [troubleshooting guide](https://github.com/pathintegral-institute/mcpm.sh/issues) or run `mcpm --help` for command-specific help.