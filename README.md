![PyPI - Version](https://img.shields.io/pypi/v/mcpm)
![GitHub Release](https://img.shields.io/github/v/release/pathintegral-institute/mcpm.sh)

<div align="center">

```
 ███╗   ███╗ ██████╗██████╗ ███╗   ███╗ 
 ████╗ ████║██╔════╝██╔══██╗████╗ ████║ 
 ██╔████╔██║██║     ██████╔╝██╔████╔██║ 
 ██║╚██╔╝██║██║     ██╔═══╝ ██║╚██╔╝██║ 
 ██║ ╚═╝ ██║╚██████╗██║     ██║ ╚═╝ ██║ 
 ╚═╝     ╚═╝ ╚═════╝╚═╝     ╚═╝     ╚═╝ 

Model Context Protocol Manager
Open Source. Forever Free.
Built with ❤️ by Path Integral Institute
```

</div>

# 🌟 MCPM - Model Context Protocol Manager

MCPM is a Homebrew-like service and command-line interface for managing Model Context Protocol (MCP) servers. It simplifies managing server configurations across various supported clients, allows grouping servers into profiles, and helps discover new servers via a registry.

## 🤝 Community Contributions

> 💡 **Grow the MCP ecosystem!** We welcome contributions to our [MCP Registry](mcp-registry/README.md). Add your own servers, improve documentation, or suggest features. Open source thrives with community participation!

## 🚀 Quick Installation

Choose your preferred installation method:

### 🍺 Homebrew

```bash
brew install mcpm
```

### 📦 pipx (Recommended for Python tools)

```bash
pipx install mcpm
```

### 🐍 pip

```bash
pip install mcpm
```

### 🔄 Shell Script (One-liner)

```bash
curl -sSL https://mcpm.sh/install | bash
```

## 🔎 Overview

MCPM simplifies the installation, configuration, and management of Model Context Protocol servers and their configurations across different applications (clients). Key features include:

- ✨ Easy addition and removal of MCP server configurations for supported clients.
- 📋 Centralized management using profiles: group server configurations together and activate/deactivate them easily.
- 🔍 Discovery of available MCP servers through a central registry.
- 🖥️ Detection of installed MCP clients on your system.
- 💻 A command-line interface (CLI) for all management tasks.
- 🔧 Utilities like a configuration inspector.

## 🖥️ Supported MCP Clients

MCPM will support managing MCP servers for the following clients:

- 🤖 Claude Desktop (Anthropic)
- ⌨️ Cursor
- 🏄 Windsurf
- 📝 Cline
- ➡️ Continue
- 🦢 Goose
- 🔥 5ire
- 🦘 Roo Code
- ✨ More clients coming soon...

## 🔥 Command Line Interface (CLI)

MCPM provides a comprehensive CLI built with Python's Click framework. Commands generally operate on the currently **active client**. You can view/set the active client using `mcpm client`. Many commands also support scope modifiers like `@CLIENT_NAME/SERVER_NAME` or `#PROFILE_NAME/SERVER_NAME` to target specific clients or profiles directly.

Below are the available commands, grouped by functionality:

### ℹ️ General

```bash
mcpm --help          # Display help information and available commands
mcpm --version       # Display the current version of MCPM
```

### 🖥️ Client Management (`client`)

```bash
mcpm client ls        # List all supported MCP clients, detect installed ones, and show active client
mcpm client set CLIENT # Set the active client for subsequent commands
mcpm client edit      # Open the active client's MCP configuration file in an external editor
```

### 🌐 Server Management (`server`)

These commands operate on the active client unless a specific scope (`@CLIENT` or `#PROFILE`) is provided.

```bash
# 🔍 Search and Add
mcpm search [QUERY]       # Search the MCP Registry for available servers
mcpm add SERVER_URL       # Add an MCP server configuration (from URL or registry name)
mcpm add SERVER_URL --alias ALIAS # Add with a custom alias

# 📋 List and Remove
mcpm ls                   # List server configurations for the active client/profile
mcpm list                 # Alias for 'ls'
mcpm rm SERVER_NAME       # Remove a server configuration
mcpm remove SERVER_NAME   # Alias for 'rm'

# 🔄 Modify and Organize
mcpm cp SOURCE TARGET     # Copy a server config (e.g., @client1/serverA #profileB)
mcpm copy SOURCE TARGET   # Alias for 'cp'
mcpm mv SOURCE TARGET     # Move a server config (e.g., #profileA/serverX @client2)
mcpm move SOURCE TARGET   # Alias for 'mv'

# 📦 Stashing (Temporarily disable/enable)
mcpm stash SERVER_NAME    # Temporarily disable/store a server configuration aside
mcpm pop [SERVER_NAME]    # Restore the last stashed server, or a specific one by name
```

### 📂 Profile Management (`profile`)

Profiles are named collections of server configurations. They allow you to easily switch between different sets of MCP servers. For example, you might have a `work` profile and a `personal` profile, each containing different servers. Or you might have a `production` profile and a `development` profile, each containing different configurations for the same servers.

The currently *active* profile's servers are typically used by features like the MCPM Router. Use `mcpm activate` to set the active profile.

```bash
# 🔄 Profile Lifecycle
mcpm profile list              # List all available MCPM profiles
mcpm profile add PROFILE_NAME  # Add a new, empty profile
mcpm profile rm PROFILE_NAME   # Remove a profile (does not delete servers within it)
mcpm profile remove PROFILE_NAME # Alias for 'rm'
mcpm profile rename OLD_NAME NEW_NAME # Rename a profile

# ✅ Activating Profiles
mcpm activate PROFILE_NAME       # Activate a profile, applying its servers to the active client
mcpm deactivate                # Deactivate the current profile for the active client
```

### 🔌 Router Management (`router`)

The MCPM Router runs as a background daemon process, acting as a stable endpoint (e.g., `http://localhost:6276`) that intelligently routes incoming MCP requests to the appropriate server based on the currently **active profile**.

This allows you to change the underlying servers (by switching profiles with `mcpm activate`) without reconfiguring your client applications. They can always point to the MCPM Router's address.

For more technical details on the router's implementation and namespacing, see [`src/mcpm/router/README.md`](src/mcpm/router/README.md).

```bash
mcpm router status                # Check if the router daemon is running
mcpm router on                    # Start the MCP router daemon
mcpm router off                   # Stop the MCP router daemon
mcpm set --host HOST --port PORT  # Set the MCP router daemon's host and port
```

### 🛠️ Utilities (`util`)

```bash
mcpm config clear-cache          # Clear MCPM's registry cache. Cache defaults to refresh every 1 hour.
mcpm inspector                   # Launch the MCPM Inspector UI to examine server configs
```

### 📚 Registry

The MCP Registry is a central repository of available MCP servers that can be installed using MCPM. The registry is available at [mcpm.sh/registry](https://mcpm.sh/registry).

## 🗺️ Roadmap

- [x] Landing page setup (`mcpm.sh`)
- [x] Core CLI foundation (Click)
- [x] Client detection and management (`mcpm client`)
- [x] Basic server management (`mcpm add`, `mcpm ls`, `mcpm rm`)
- [x] Registry integration (`mcpm search`, adding by name)
- [x] Router functionality (`mcpm router`)
- [x] MCP Profiles (`mcpm profile`, `mcpm activate/deactivate`)
- [x] Server copying/moving (`mcpm cp`, `mcpm mv`)
- [x] Server stashing (`mcpm stash`, `mcpm pop`)
- [ ] MCP Server Access Monitoring for MCPM Router (local only, absolutely no data leaving local machine)
- [ ] MCPM Router over STDIO (same powerful feature set with profile and monitoring, but single client/tenant)
- [ ] MCP Server for MCPM Router (experimental, allow MCP clients to dynamically switch between profiles, suggest new MCP servers from registry, etc.)
- [ ] Server-side management capabilities (Beyond config management)
- [ ] Additional client support (Expand registry)

## 👨‍💻 Development

This repository contains the CLI and service components for MCP Manager, built with Python and Click following modern package development practices.

### 📋 Development Requirements

- 🐍 Python 3.10+
- 🚀 uv (for virtual environment and dependency management)
- 🖱️ Click framework for CLI
- ✨ Rich for enhanced console output
- 🌐 Requests for API interactions

### 📁 Project Structure

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

### 🚀 Development Setup

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

### ✅ Best Practices

- 📁 Use the src-based directory structure to prevent import confusion
- 🔧 Develop with an editable install using `uv pip install -e .`
- 🧩 Keep commands modular in the `src/mcpm/commands/` directory
- 🧪 Add tests for new functionality in the `tests/` directory
- 💻 Use the `test_cli.py` script for quick development testing


### 🔢 Version Management

MCP uses a single source of truth pattern for version management to ensure consistency across all components.

#### 🏷️ Version Structure

- 📍 The canonical version is defined in `version.py` at the project root
- 📥 `src/mcpm/__init__.py` imports this version
- 📄 `pyproject.toml` uses dynamic versioning to read from `version.py`
- 🏷️ Git tags are created with the same version number prefixed with 'v' (e.g., v1.0.0)

#### 🔄 Updating the Version

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

## 📜 License

MIT
