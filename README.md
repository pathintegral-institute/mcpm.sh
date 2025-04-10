![PyPI - Version](https://img.shields.io/pypi/v/mcpm)
![GitHub Release](https://img.shields.io/github/v/release/pathintegral-institute/mcpm.sh)

# MCPM - Model Context Protocol Manager

MCPM is a Homebrew-like service and command-line interface for managing Model Context Protocol (MCP) servers across various MCP clients.

## Overview

MCPM aims to simplify the installation, configuration, and management of Model Context Protocol servers with a focus on:

- Easy installation of MCP servers via a simple CLI
- Centralized management of server configurations across multiple clients
- Seamless updates for installed servers
- Server-side management capabilities
- Registry of available MCP servers

## Supported MCP Clients

MCPM will support managing MCP servers for the following clients:

- Claude Desktop (Anthropic)
- Cursor
- Windsurf
- Cline
- Continue
- Goose
- 5ire
- Roo Code
- More clients coming soon...

## Command Line Interface (CLI)

MCPM provides a comprehensive CLI built with Python's Click framework. Below are the available commands:

### Basic Commands

```
mcpm --help                             # Display help information and available commands
mcpm --version                          # Display the current version of MCPM
```

### Available Commands

```
# client
mcpm client ls                       # List all supported MCP clients and their status
mcpm client set CLIENT               # 
mcpm client edit                     # open client mcp setting in external editor


# editing ops, applying to the active scope
# add @client or #profile to set explicit scope
# for example: 
#     mcpm rm #PROFILE/SERVER_NAME to remove server for a profile (even when it's not activated)
#     mcpm cp @CLIENT/SERVER_NAME #PROFILE

mcpm add SERVER_NAME                     # Add an MCP server to the active client
mcpm add SERVER_NAME --alias ALIAS_NAME  # Add an MCP server to the active client with a custom alias
mcpm cp SOURCE TARGET                    # Copy an MCP server from one client/profile to another
mcpm mv SOURCE TARGET                    # Move an MCP server from one client/profile to another
mcpm rm 
mcpm remove SERVER_NAME                  # Remove an installed MCP server
mcpm ls
mcpm list                                # List all installed MCP servers
mcpm stash SERVER_NAME                   # Temporarily disable an MCP server for a client
mcpm pop SERVER_NAME                     # Re-enable an MCP server for a client


# profile
mcpm profile add PROFILE                 # Add a new MCPM profile
mcpm profile list                        # List all MCPM profiles
mcpm profile rm PROFILE                  # Remove an MCPM profile
mcpm profile remove PROFILE              # Remove an MCPM profile
mcpm profile rename PROFILE              # Rename an MCPM profile

mcpm activate PROFILE                    # activate a profile for a client
mcpm deactivate                          # deactivate a profile for a client

# router
mcpm router on -p port -h host           # start router daemon
mcpm router off


# util
mcpm config clear-cache   
mcpm inspect SERVER_NAME                 # Launch the MCPM Inspector UI to examine servers
```

### Registry

The MCP Registry is a central repository of available MCP servers that can be installed using MCPM. The registry is available at [mcpm.sh/registry](https://mcpm.sh/registry).

## Roadmap

- [x] Landing page setup
- [x] CLI foundation
- [x] Search
- [x] Install
- [x] Registry integration
- [ ] Server management functionality
- [ ] Support SSE Server
- [ ] Additional client support
- [ ] MCP profiles - collections of tools that can be added to any clients with a single command

## Development

This repository contains the CLI and service components for MCP Manager, built with Python and Click following modern package development practices.

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
├── pages/           # Website content
│   └── registry/    # Registry website
├── mcp-registry/    # MCP Registry data
└── README.md        # Documentation
```

### Development Setup

1. Clone the repository
   ```
   git clone https://github.com/pathintegral-institute/mcpm.sh.git
   cd mcpm.sh
   ```

2. Set up a virtual environment with uv
   ```
   uv venv --seed
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


### Version Management

MCP uses a single source of truth pattern for version management to ensure consistency across all components.

#### Version Structure

- The canonical version is defined in `version.py` at the project root
- `src/mcpm/__init__.py` imports this version
- `pyproject.toml` uses dynamic versioning to read from `version.py`
- Git tags are created with the same version number prefixed with 'v' (e.g., v1.0.0)

#### Updating the Version

When releasing a new version:

1. Use the provided version bump script
   ```
   ./bump_version.sh NEW_VERSION
   # Example: ./bump_version.sh 1.1.0
   ```

2. Push the changes and tags
   ```
   git push && git push --tags
   ```

3. Create a GitHub release matching the new version

This process ensures that the version is consistent in all places: code, package metadata, and git tags.
PyPI release is handled by the CI/CD pipeline and will be triggered automatically.

## License

MIT
