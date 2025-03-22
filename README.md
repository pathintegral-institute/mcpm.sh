# MCPM - Model Context Protocol Package Manager

MCPM is a Homebrew-like service and command-line interface for managing Model Context Protocol (MCP) servers across various MCP clients.

## Overview

MCPM aims to simplify the installation, configuration, and management of Model Context Protocol servers with a focus on:

- Easy installation of MCP servers via a simple CLI
- Centralized management of server configurations across multiple clients
- Seamless updates for installed servers
- Server-side management capabilities

## Supported MCP Clients

MCPM will support managing MCP servers for the following clients:

- Claude Desktop (Anthropic)
- Cursor
- Windsurf
- Additional clients coming soon...

## Command Line Interface (CLI)

MCPM provides a comprehensive CLI built with Python's Click framework. Below are the available commands:

### Basic Commands

```
mcpm --help                   # Display help information and available commands
mcpm --version                # Display the current version of MCPM
```

### Search Commands

```
mcpm search [QUERY]           # Search available MCP servers
mcpm search --tags=TAG        # Search servers by tag
```

### Installation Commands

```
mcpm install SERVER_NAME      # Install an MCP server
mcpm install SERVER_NAME --version=VERSION  # Install specific version
mcpm remove SERVER_NAME       # Remove an installed MCP server
mcpm update [SERVER_NAME]     # Update installed servers (or specific server)
```

### List Commands

```
mcpm list                     # List all installed MCP servers
mcpm list --available         # List all available MCP servers
mcpm list --outdated          # List installed servers with updates available
```

### Configuration Commands

```
mcpm config SERVER_NAME       # Configure an installed MCP server
mcpm config --edit SERVER_NAME # Open server config in default editor
mcpm config --reset SERVER_NAME # Reset server config to defaults
```

### Status Commands

```
mcpm status [SERVER_NAME]     # Show status of all or specific MCP servers
mcpm status --client=CLIENT_NAME  # Show status of MCP servers for a specific client
mcpm enable SERVER_NAME --client=CLIENT_NAME  # Enable an MCP server for a specific client
mcpm disable SERVER_NAME --client=CLIENT_NAME # Disable an MCP server for a specific client
```

### Server Management

```
mcpm server start SERVER_NAME   # Start an MCP server
mcpm server stop SERVER_NAME    # Stop an MCP server
mcpm server restart SERVER_NAME # Restart an MCP server
mcpm server log SERVER_NAME     # View server logs
```

## Roadmap

- [x] Landing page setup
- [ ] CLI foundation
- [ ] Server repository structure
- [ ] Claude Desktop client integration
- [ ] Server management functionality
- [ ] Additional client support

## Development

This repository contains the CLI and service components for MCPM, built with Python and Click following modern package development practices.

### Development Requirements

- Python 3.8+
- uv (for virtual environment and dependency management)
- Click framework for CLI
- Rich for enhanced console output
- Requests for API interactions

### Project Structure

The project follows the modern src-based layout:

```
mcpm.sh/
├── src/             # Source package directory
│   └── mcpm/        # Main package code
├── tests/           # Test directory
├── test_cli.py      # Development CLI runner
├── pyproject.toml   # Project configuration
└── README.md        # Documentation
```

### Development Setup

1. Clone the repository
   ```
   git clone https://github.com/pathintegral-xyz/mcpm.sh.git
   cd mcpm.sh
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
   mcpm --help
   
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
- Keep commands modular in the `src/mcpm/commands/` directory
- Add tests for new functionality in the `tests/` directory
- Use the `test_cli.py` script for quick development testing

## License

MIT
