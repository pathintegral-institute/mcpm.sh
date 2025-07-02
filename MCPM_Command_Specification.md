# MCPM Command Specification v2.0

This document defines the complete command structure for MCPM, implementing a simplified global workspace model without client-specific management complexity.

## Core Architecture

**Global Configuration Model:**
- All servers are managed in a single global configuration
- Profiles organize servers into logical groups via tagging
- Clients configure themselves to run servers via `mcpm run`
- No active target or client-specific state management

---

## Command Reference

### Server Management

Core commands for managing servers in the global configuration.

| Command | Description |
|---------|-------------|
| `mcpm install [NAME \| PATH \| URL]` | Installs a server from registry, local file, or URL |
| `mcpm uninstall [SERVER_NAME]` | Removes a server from configuration |
| `mcpm ls` | Lists all installed servers and their profile assignments |
| `mcpm search [QUERY]` | Searches the MCP Registry for available servers |
| `mcpm info [SERVER_NAME]` | Shows detailed registry information for a server |
| `mcpm inspect [SERVER_NAME]` | Launches MCP Inspector to test and debug an installed server |
| `mcpm import [CLIENT_NAME]` | Imports server configurations from a supported client |

### Server Execution

Commands for running servers directly (stateless model).

| Command | Description |
|---------|-------------|
| `mcpm run [SERVER_NAME]` | Executes a single server over stdio |

**Example Client Configuration:**
```json
{
  "name": "MCPM: Browse",
  "command": ["mcpm", "run", "mcp-server-browse"]
}
```

### Profile Management

Commands for organizing servers with virtual groups/tags. Profiles are logical groupings that don't move servers, but tag them for organization.

| Command | Description |
|---------|-------------|
| `mcpm profile create [NAME]` | Creates a new profile |
| `mcpm profile rm [NAME]` | Deletes a profile |
| `mcpm profile ls` | Lists all profiles and their tagged servers |
| `mcpm profile add [PROFILE] [SERVER]` | Tags a server with a profile |
| `mcpm profile remove [PROFILE] [SERVER]` | Removes profile tag from a server |
| `mcpm profile run [PROFILE_NAME]` | Executes all servers tagged with profile over stdio |

### Server Sharing

Commands for exposing servers via secure tunnels.

| Command | Description |
|---------|-------------|
| `mcpm share [SERVER_NAME]` | Creates public tunnel to a single server |
| `mcpm profile share [PROFILE_NAME]` | Creates public tunnel to all servers in a profile |

### System & Configuration

Commands for managing system health, analytics, and global settings.

| Command | Description |
|---------|-------------|
| `mcpm doctor` | Checks system health and installed server status |
| `mcpm usage` | Displays analytics and usage data for servers |
| `mcpm config set [KEY] [VALUE]` | Sets a global configuration value |
| `mcpm config get [KEY]` | Retrieves a global configuration value |
| `mcpm config clear-cache` | Clears the local registry cache |

---

## Workflow Examples

### Basic Server Management
```bash
# Discover and install servers
mcpm search browser
mcpm info mcp-server-browse
mcpm install mcp-server-browse

# Import from existing clients
mcpm import cursor

# List and inspect installed servers  
mcpm ls
mcpm inspect mcp-server-browse

# Run server directly
mcpm run mcp-server-browse

# Check system health
mcpm doctor
```

### Profile Organization
```bash
# Create profiles for different contexts
mcpm profile create web-dev
mcpm profile create data-analysis

# Tag servers with profiles
mcpm profile add web-dev mcp-server-browse
mcpm profile add data-analysis mcp-server-pandas

# Run entire profiles
mcpm profile run web-dev
```

### Client Integration
```bash
# Install servers
mcpm install mcp-server-browse
mcpm install mcp-server-email

# Configure in MCP client (e.g., Cursor)
# Multiple configs, one per server:
```
```json
{
  "mcpServers": {
    "browse": {
      "command": ["mcpm", "run", "mcp-server-browse"]
    },
    "email": {
      "command": ["mcpm", "run", "mcp-server-email"] 
    }
  }
}
```

### Sharing and Collaboration
```bash
# Share individual servers
mcpm share mcp-server-browse

# Share entire development environment
mcpm profile create dev-env
mcpm profile add dev-env mcp-server-browse
mcpm profile add dev-env mcp-server-git
mcpm profile share dev-env

# Import existing client configurations  
mcpm import cursor
mcpm import claude-desktop
```

---

## Migration from Current System

### Command Mapping

| Current Command | New Command | Notes |
|----------------|-------------|-------|
| `mcpm add SERVER` | `mcpm install SERVER` | Simplified to global configuration |
| `mcpm rm SERVER` | `mcpm uninstall SERVER` | No target specification needed |
| `mcpm ls --target @client` | `mcpm ls` | Single global view |
| `mcpm info SERVER` | `mcpm info SERVER` | Unchanged (registry details) |
| `mcpm inspector` | `mcpm inspect SERVER` | Now launches inspector for specific server |
| `mcpm target set @client` | *Removed* | No active target concept |

### Deprecated Features

**Removed in v2.0:**
- Active target management (`mcpm target`)
- Client-specific operations (`--target @client`)
- Target prefixes (`@client`, `%profile`) 
- Cross-client server copying/moving
- Stash/pop server configuration

**Simplified Alternatives:**
- Global configuration replaces per-client management
- Manual client configuration replaces automatic target injection
- Profile tagging replaces complex target routing

---

## Implementation Status

- ✅ **Existing:** `search`, `info`, `ls`, `profile create/rm/ls`, `share`, `config`
- 🔄 **Needs Aliases:** `install` (alias for `add`), `uninstall` (alias for `rm`)
- 🆕 **New Commands:** `doctor`, `usage`, `inspect`, `run`, `profile add/remove`, `profile run`, `profile share`, `import`
- 🗑️ **To Remove:** Target system, client management, stash/pop operations

This specification provides a clear, simplified command structure focused on workspace management and direct server execution.