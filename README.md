# MCP - Model Context Protocol Package Manager

MCP is a Homebrew-like service and command-line interface for managing Model Context Protocol (MCP) servers across various MCP clients.

## Overview

MCP aims to simplify the installation, configuration, and management of Model Context Protocol servers with a focus on:

- Easy installation of MCP servers via a simple CLI
- Centralized management of server configurations across multiple clients
- Seamless updates for installed servers
- Server-side management capabilities

## Supported MCP Clients

MCP will support managing MCP servers for the following clients:

- Claude Desktop (Anthropic)
- Cursor
- Windsurf
- Additional clients coming soon...

## Command Line Interface (CLI)

MCP provides a comprehensive CLI built with Python's Click framework. Below are the available commands:

### Basic Commands

```
mcp --help                  # Display help information and available commands
mcp --version                # Display the current version of MCP
```

### Search Commands

```
mcp search [QUERY]           # Search available MCP servers
mcp search --tags=TAG        # Search servers by tag
```

### Installation Commands

```
mcp install SERVER_NAME      # Install an MCP server
mcp install SERVER_NAME --version=VERSION  # Install specific version
mcp remove SERVER_NAME       # Remove an installed MCP server
mcp update [SERVER_NAME]     # Update installed servers (or specific server)
```

### List Commands

```
mcp list                     # List all installed MCP servers
mcp list --available         # List all available MCP servers
mcp list --outdated          # List installed servers with updates available
```

### Configuration Commands

```
mcp config SERVER_NAME       # Configure an installed MCP server
mcp config --edit SERVER_NAME # Open server config in default editor
mcp config --reset SERVER_NAME # Reset server config to defaults
```

### Status Commands

```
mcp status [SERVER_NAME]     # Show status of all or specific MCP servers
mcp status --client=CLIENT_NAME  # Show status of MCP servers for a specific client
mcp enable SERVER_NAME --client=CLIENT_NAME  # Enable an MCP server for a specific client
mcp disable SERVER_NAME --client=CLIENT_NAME # Disable an MCP server for a specific client
```

### Server Management

```
mcp server start SERVER_NAME   # Start an MCP server
mcp server stop SERVER_NAME    # Stop an MCP server
mcp server restart SERVER_NAME # Restart an MCP server
mcp server log SERVER_NAME     # View server logs
```

## Roadmap

- [x] Landing page setup
- [ ] CLI foundation
- [ ] Server repository structure
- [ ] Claude Desktop client integration
- [ ] Server management functionality
- [ ] Additional client support

## Development

This repository contains the CLI and service components for MCP, built with Python and Click following modern package development practices.

### Development Requirements

- Python 3.8+
- uv (for virtual environment and dependency management)
- Click framework for CLI
- Rich for enhanced console output
- Requests for API interactions

### Project Structure

The project follows the modern src-based layout:

```
getmcp.sh/
├── src/             # Source package directory
│   └── mcp/         # Main package code
├── tests/           # Test directory
├── test_cli.py      # Development CLI runner
├── pyproject.toml   # Project configuration
└── README.md        # Documentation
```

### Development Setup

1. Clone the repository
   ```
   git clone https://github.com/pathintegral-xyz/getmcp.sh.git
   cd getmcp.sh
   ```

2. Set up a virtual environment with uv
   ```
   uv venv
   source .venv/bin/activate  # On Unix/Mac
   ```

3. Install dependencies in development mode
   ```
   uv pip install -e .
   ```

4. Run the CLI directly during development
   ```
   # Either use the installed package
   mcp --help
   
   # Or use the development script
   ./test_cli.py --help
   ```

5. Run tests
   ```
   pytest tests/
   ```

### Best Practices

- Use the src-based directory structure to prevent import confusion
- Develop with an editable install using `uv pip install -e .`
- Keep commands modular in the `src/mcp/commands/` directory
- Add tests for new functionality in the `tests/` directory
- Use the `test_cli.py` script for quick development testing

## License

MIT
