# MCPM v2.0 Migration Guide

This guide helps existing MCPM users transition from the target-based system to the new simplified global configuration model.

## What Changed

### New Architecture
- **Global Configuration Model**: All servers managed in a single global configuration
- **Profile Tagging**: Profiles are now virtual tags, not separate configurations
- **Direct Execution**: Run servers directly without target management
- **Simplified Commands**: Cleaner command structure with logical grouping

### Removed Features
- **Active Target System**: No more `mcpm target set` requirement
- **Client-Specific Management**: No more `--target @client` flags
- **Complex Target Routing**: Simplified to direct specification

## Command Migration

### Server Management

| **Old Command** | **New Command** | **Notes** |
|----------------|----------------|-----------|
| `mcpm add SERVER` | `mcpm install SERVER` | `add` still works as alias |
| `mcpm add SERVER --target @client` | `mcpm install SERVER` | Install to global config |
| `mcpm rm SERVER` | `mcpm uninstall SERVER` | `rm` still works as alias |
| `mcpm ls --target @client` | `mcpm ls` | Single global view |
| `mcpm target set @client` | *Removed* | No longer needed |

### Profile Management

| **Old Command** | **New Command** | **Notes** |
|----------------|----------------|-----------|
| `mcpm profile add NAME` | `mcpm profile create NAME` | Consistent naming |
| `mcpm add SERVER --target %profile` | `mcpm profile add PROFILE SERVER` | Tag-based approach |
| `N/A` | `mcpm profile remove PROFILE SERVER` | Remove profile tag |
| `N/A` | `mcpm profile run PROFILE` | Execute profile servers |

### New Commands

| **Command** | **Description** |
|------------|----------------|
| `mcpm doctor` | System health check and diagnostics |
| `mcpm usage` | Analytics and usage data |
| `mcpm run SERVER` | Execute server directly over stdio |
| `mcpm inspect SERVER` | Launch MCP Inspector for specific server |
| `mcpm import CLIENT` | Import configurations from supported clients |
| `mcpm profile share PROFILE` | Share entire profile via tunnel |

## Migration Steps

### 1. Update Your Workflow

**Before (v1.x):**
```bash
# Set active target
mcpm target set @cursor

# Add servers to specific client
mcpm add mcp-server-browse
mcpm add mcp-server-git

# Create and populate profile
mcpm profile add web-dev
mcpm add mcp-server-browse --target %web-dev
```

**After (v2.0):**
```bash
# Install servers globally
mcpm install mcp-server-browse
mcpm install mcp-server-git

# Create and tag with profile
mcpm profile create web-dev
mcpm profile add web-dev mcp-server-browse
mcpm profile add web-dev mcp-server-git
```

### 2. Client Configuration

**Update your MCP client configurations to use direct execution:**

```json
{
  "mcpServers": {
    "browse": {
      "command": ["mcpm", "run", "mcp-server-browse"]
    },
    "git": {
      "command": ["mcpm", "run", "mcp-server-git"]
    }
  }
}
```

### 3. Import Existing Configurations

**Import from existing clients:**
```bash
# Import servers from Cursor to a profile
mcpm import cursor --profile development

# Import from Claude Desktop to global config
mcpm import claude-desktop
```

### 4. Organize with Profiles

**Create organized profiles:**
```bash
# Create profiles for different contexts
mcpm profile create web-dev
mcpm profile create ai-tools
mcpm profile create data-analysis

# Tag servers with profiles
mcpm profile add web-dev mcp-server-browse
mcpm profile add web-dev mcp-server-git
mcpm profile add ai-tools mcp-server-anthropic
mcpm profile add data-analysis mcp-server-pandas
```

## Benefits of v2.0

### Simplified Management
- **No Active Target**: Commands work immediately without setup
- **Global Workspace**: All servers in one place, easy to discover
- **Flexible Organization**: Tag servers with multiple profiles

### Better Developer Experience
- **Direct Execution**: `mcpm run server-name` for instant testing
- **Health Monitoring**: `mcpm doctor` for system diagnostics
- **Usage Analytics**: `mcpm usage` for insights
- **Easy Import**: `mcpm import client-name` for migrations

### Enhanced Workflows
- **Profile Execution**: `mcpm profile run web-dev` for environment setup
- **Profile Sharing**: `mcpm profile share web-dev` for collaboration
- **Comprehensive Testing**: `mcpm inspect server-name` for debugging

## Troubleshooting

### Common Issues

**Issue**: `mcpm add` not working
- **Solution**: Use `mcpm install` or update to new command structure

**Issue**: "No active target set" error
- **Solution**: Update to v2.0 commands that don't require targets

**Issue**: Can't find installed servers
- **Solution**: Use `mcpm ls` to see all servers, no target required

**Issue**: Profile commands not working as expected
- **Solution**: Profiles are now tags, use `mcpm profile add PROFILE SERVER`

### Getting Help

- **Health Check**: `mcpm doctor` - Diagnose system issues
- **Command Help**: `mcpm COMMAND --help` - Detailed command information
- **List Available**: `mcpm --help` - See all available commands
- **Import Options**: `mcpm import --list-clients` - See supported clients

## Legacy Support

### Backward Compatibility
- **`mcpm add`** still works (alias for `install`)
- **`mcpm rm`** still works (alias for `uninstall`)
- **Existing profiles** continue to work with new tagging system
- **Client configurations** work with `mcpm run` approach

### Deprecation Timeline
- **v2.0**: Legacy commands work with deprecation warnings
- **v2.1**: Legacy commands show migration suggestions
- **v3.0**: Legacy commands removed (target system, client management)

## Support

For questions or issues during migration:
- **Documentation**: https://github.com/pathintegral-institute/mcpm.sh
- **Issues**: https://github.com/pathintegral-institute/mcpm.sh/issues
- **Help Command**: `mcpm --help` for quick reference

---

*This migration preserves all your existing functionality while providing a cleaner, more intuitive interface for managing MCP servers.*