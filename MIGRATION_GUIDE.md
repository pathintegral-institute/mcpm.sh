# MCPM v2.0 Migration Guide

This guide helps existing MCPM v1 users transition to the new simplified global configuration model.

## What's New in v2.0

### Simplified Architecture
- **Global Server Configuration**: All servers managed in a single global configuration
- **Virtual Profiles**: Profiles are now tags on servers, not separate configurations
- **Direct Execution**: Run servers directly without complex router setup
- **Beautiful CLI**: Enhanced interface with rich formatting and better organization
- **Client Integration**: Manage multiple MCP clients from one place

### Key Improvements
- **Faster Startup**: No daemon dependencies, direct stdio execution
- **Better Performance**: Direct execution eliminates router complexity
- **Enhanced Usability**: Centralized server management, easy profile organization
- **Developer Tools**: Built-in inspector, HTTP testing, public sharing
- **Usage Analytics**: Track and analyze server usage patterns

## Automatic Migration

MCPM v2.0 includes an automatic migration system that detects v1 configurations and guides you through the upgrade process.

### Migration Process

When you run any MCPM command with v1 configuration present, you'll see:

1. **Welcome Screen**: Introduction to v2.0 with migration options
2. **Configuration Analysis**: Review of your current v1 setup
3. **v2.0 Features**: Overview of new capabilities and improvements
4. **Breaking Changes**: Important changes that affect your workflow
5. **Migration Choice**: Three options for proceeding

### Migration Options

#### Option 1: Migrate (Recommended)
```
Y - Migrate to v2 (recommended)
```
- Converts your v1 profiles to v2 virtual profiles
- Migrates all servers to global configuration
- Preserves your existing setup while upgrading to v2
- Creates backup of v1 configuration files

#### Option 2: Start Fresh
```
N - Start fresh with v2 (backup v1 configs)
```
- Backs up your v1 configuration safely
- Starts with a clean v2 installation
- Removes v1 files after backup
- Good option if you want to reorganize from scratch

#### Option 3: Ignore for Now
```
I - Ignore for now (continue with current command)
```
- Continues with your current command
- Keeps v1 configuration unchanged
- Can migrate later with `mcpm migrate`
- Some v2 features may not work properly

### Manual Migration

You can also trigger migration manually:

```bash
mcpm migrate
```

This shows the same migration assistant as the automatic detection.

## Command Changes

### Main Commands

| **v1 Command** | **v2 Command** | **Notes** |
|----------------|----------------|-----------|
| `mcpm add SERVER` | `mcpm install SERVER` | Cleaner naming |
| `mcpm rm SERVER` | `mcpm uninstall SERVER` | Cleaner naming |
| `mcpm ls` | `mcpm ls` | Same command, enhanced output |
| `mcpm target set` | *Removed* | No longer needed |
| `mcpm router start` | `mcpm run --http` | Direct HTTP execution |
| `mcpm share` | `mcpm share` | Simplified sharing |

### Profile Commands

| **v1 Command** | **v2 Command** | **Notes** |
|----------------|----------------|-----------|
| `mcpm target create %profile` | `mcpm profile create PROFILE` | Virtual profiles |
| `mcpm add SERVER --target %profile` | `mcpm profile edit PROFILE` | Interactive management |
| `mcpm target use %profile` | `mcpm profile run PROFILE` | Execute profile servers |
| `N/A` | `mcpm profile share PROFILE` | New: Share entire profiles |

### New Commands

| **Command** | **Description** |
|------------|----------------|
| `mcpm doctor` | System health check and diagnostics |
| `mcpm usage` | Comprehensive analytics and usage data |
| `mcpm inspect SERVER` | Launch MCP Inspector for server testing |
| `mcpm client ls` | List and manage MCP clients |
| `mcpm client edit CLIENT` | Configure client server selections |
| `mcpm client import CLIENT` | Import configurations from clients |
| `mcpm config` | Manage MCPM configuration settings |

## Migration Examples

### Before v2.0 (v1 workflow)
```bash
# Complex target-based workflow
mcpm target create @cursor
mcpm target set @cursor
mcpm add mcp-server-browse
mcpm add mcp-server-git

mcpm target create %web-dev
mcpm add mcp-server-browse --target %web-dev
mcpm add mcp-server-git --target %web-dev

mcpm router start
mcpm share mcp-server-browse
```

### After v2.0 (simplified workflow)
```bash
# Simple global configuration
mcpm install mcp-server-browse
mcpm install mcp-server-git

# Create and organize with profiles
mcpm profile create web-dev
mcpm profile edit web-dev  # Interactive server selection

# Direct execution and sharing
mcpm run mcp-server-browse
mcpm share mcp-server-browse
mcpm profile run web-dev
mcpm profile share web-dev
```

## Client Integration

### Before: Complex Router Setup
```json
{
  "mcpServers": {
    "mcpm-router": {
      "command": ["mcpm", "router", "run"],
      "args": ["--port", "3000"]
    }
  }
}
```

### After: Direct Execution
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

Or use MCPM's client management:
```bash
mcpm client edit claude-desktop  # Interactive configuration
mcpm client edit cursor         # Select servers for Cursor
```

## Post-Migration Workflow

### 1. Verify Migration
```bash
mcpm ls                    # See all migrated servers
mcpm profile ls           # See migrated profiles
mcpm run SERVER-NAME      # Test server execution
```

### 2. Explore New Features
```bash
mcpm client ls            # See detected MCP clients
mcpm doctor              # Check system health
mcpm usage               # View usage analytics
mcpm inspect SERVER      # Debug server with inspector
```

### 3. Organize with Profiles
```bash
mcpm profile create frontend
mcpm profile create backend
mcpm profile create ai-tools

# Use interactive editor to assign servers
mcpm profile edit frontend
```

### 4. Client Integration
```bash
# Configure clients interactively
mcpm client edit claude-desktop
mcpm client edit cursor

# Or import existing configurations
mcpm client import claude-desktop
```

## Troubleshooting

### Migration Issues

**Migration fails with profile errors**
- Check that profile servers exist in global config
- Verify server configurations are valid
- Run `mcpm doctor` for diagnostic information

**"No v1 config found" when you have v1 files**
- Ensure files are in `~/.config/mcpm/`
- Check file permissions and format
- Try `mcpm migrate` to trigger manual migration

**Stashed servers not migrated**
- Migration asks what to do with stashed servers
- Choose "restore" to add them to global config
- Choose "document" to save them for manual review

### Post-Migration Issues

**Servers not working in clients**
- Update client configurations to use `mcpm run SERVER`
- Use `mcpm client edit CLIENT` for interactive setup
- Check server status with `mcpm ls`

**Profile commands not working**
- Profiles are now virtual tags, not separate configurations
- Use `mcpm profile edit PROFILE` to manage server assignments
- Check profile status with `mcpm profile ls`

**Command not found errors**
- Some v1 commands have been removed or renamed
- Use `mcpm --help` to see all available commands
- Check this guide for command equivalents

## Getting Help

- **Health Check**: `mcpm doctor` - Diagnose system issues
- **Command Help**: `mcpm COMMAND --help` - Detailed command information  
- **Migration Help**: `mcpm migrate --help` - Migration-specific options
- **Support**: https://github.com/pathintegral-institute/mcpm.sh/issues

## Backup Information

During migration, MCPM creates comprehensive backups:

- **Location**: `~/.config/mcpm/backups/`
- **Contents**: Original v1 `config.json` and `profiles.json`
- **README**: Detailed backup information and recovery instructions
- **Timestamp**: Each backup includes creation timestamp

Your original v1 configuration is never modified until you confirm migration.

---

*MCPM v2.0 provides a cleaner, more powerful interface while preserving all your existing functionality. The migration process is designed to be safe and reversible.*