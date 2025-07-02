![Homebrew Formula Version](https://img.shields.io/homebrew/v/mcpm?style=flat-square&color=green)
![PyPI - Version](https://img.shields.io/pypi/v/mcpm?style=flat-square&color=green)
![GitHub Release](https://img.shields.io/github/v/release/pathintegral-institute/mcpm.sh?style=flat-square&color=green)
![GitHub License](https://img.shields.io/github/license/pathintegral-institute/mcpm.sh?style=flat-square&color=orange)
![GitHub contributors](https://img.shields.io/github/contributors/pathintegral-institute/mcpm.sh?style=flat-square&color=blue)
![PyPI - Downloads](https://img.shields.io/pypi/dm/mcpm?style=flat-square&color=yellow)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/pathintegral-institute/mcpm.sh?style=flat-square&color=red)

English | [简体中文](README.zh-CN.md)

![mcpm.sh](https://socialify.git.ci/pathintegral-institute/mcpm.sh/image?custom_description=One+CLI+tool+for+all+your+local+MCP+Needs.+Search%2C+add%2C+configure+MCP+servers.+Router%2C+profile%2C+remote+sharing%2C+access+monitoring+etc.&description=1&font=Inter&forks=1&issues=1&name=1&pattern=Floating+Cogs&pulls=1&stargazers=1&theme=Auto)

```
Open Source. Forever Free.
Built with ❤️ by Path Integral Institute
```

# 🌟 MCPM - Model Context Protocol Manager

MCPM is an open source service and a CLI package management tool for MCP servers. It simplifies managing server configurations across various supported clients, allows grouping servers into profiles, helps discover new servers via a registry, and includes a powerful router that aggregates multiple MCP servers behind a single endpoint with shared sessions.

![Demo of MCPM in action](.github/readme/demo.gif)

## 🤝 Community Contributions

> 💡 **Grow the MCP ecosystem!** We welcome contributions to our [MCP Registry](mcp-registry/README.md). Add your own servers, improve documentation, or suggest features. Open source thrives with community participation!

## 🚀 Quick Installation

### Recommended: 

```bash
curl -sSL https://mcpm.sh/install | bash
```

Or choose [other installation methods](#-other-installation-methods) like `brew`, `pipx`, `uv` etc.

## 🔎 Overview

MCPM simplifies the installation, configuration, and management of Model Context Protocol servers using a modern global configuration approach. Key features include:

- ✨ Global server installation and management - install servers once, use everywhere.
- 📋 Profile-based organization: tag servers with profiles for easy grouping and management.
- 🔍 Discovery of available MCP servers through a central registry.
- 🔌 Direct server execution and sharing capabilities.
- 🎛️ Client integration tools for enabling/disabling servers in MCP clients.
- 💻 A modern command-line interface (CLI) with interactive features.

See [Advanced Features](docs/advanced_features.md) for more capabilities like shared server sessions and the MCPM Router.

## 🖥️ Supported MCP Clients

MCPM will support managing MCP servers for the following clients:

- 🤖 Claude Desktop (Anthropic)
- ⌨️ Cursor
- 🏄 Windsurf
- 🧩 Vscode
- 📝 Cline
- ➡️ Continue
- 🦢 Goose
- 🔥 5ire
- 🦘 Roo Code
- ✨ More clients coming soon...

## 🔥 Command Line Interface (CLI)

MCPM provides a comprehensive CLI built with Python's Click framework. The v2.0 architecture uses a global configuration model where servers are installed once and can be organized with profiles, then integrated into specific MCP clients as needed.

Below are the available commands, grouped by functionality:

### ℹ️ General

```bash
mcpm --help          # Display help information and available commands
mcpm --version       # Display the current version of MCPM
```

### 🌐 Server Management

Global server installation and management commands:

```bash
# 🔍 Search and Install
mcpm search [QUERY]           # Search the MCP Registry for available servers
mcpm install SERVER_NAME      # Install a server from registry to global configuration
mcpm install SERVER_NAME --alias ALIAS # Install with a custom alias
mcpm uninstall SERVER_NAME    # Remove a server from global configuration

# 📋 List and Inspect
mcpm ls                       # List all installed servers and their profile assignments
mcpm inspect SERVER_NAME      # Launch MCP Inspector to test/debug a server
mcpm run SERVER_NAME          # Execute a server directly over stdio

# 🔄 Import and Share
mcpm import                   # Import server configurations from supported MCP clients
mcpm share SERVER_NAME        # Share a server through secure tunnel for remote access
```

### 📂 Profile Management

Profiles are used to tag and organize servers into logical groups. Each server can be tagged with multiple profiles.

```bash
# 🔄 Profile Operations
mcpm profile list            # List all profiles and their tagged servers
mcpm profile create PROFILE  # Create a new profile
mcpm profile remove PROFILE  # Remove a profile (servers remain installed)

# 🏷️ Server Tagging
mcpm profile add PROFILE SERVER     # Tag a server with a profile
mcpm profile remove PROFILE SERVER  # Remove profile tag from a server
mcpm profile edit PROFILE           # Interactive server selection for profile
mcpm profile run PROFILE           # Run all servers in a profile together
mcpm profile share PROFILE         # Share all servers in a profile
```

### 🖥️ Client Integration

Manage which MCPM servers are enabled in specific MCP clients:

```bash
mcpm client ls                    # List all supported MCP clients and their status
mcpm client edit CLIENT_NAME      # Interactive server enable/disable for a client
mcpm client edit CLIENT_NAME -e   # Open client config in external editor
```

### 🛠️ System & Configuration

```bash
mcpm doctor                      # Check system health and server status
mcpm usage                       # Display analytics and usage data  
mcpm config                      # Manage MCPM configuration and settings
```

### 🔌 Advanced Features

MCPM also provides advanced capabilities for power users:

```bash
# 🚀 Router and Sharing (Advanced)
mcpm router status              # Check router daemon status
mcpm router on                  # Start MCP router daemon
mcpm router off                 # Stop MCP router daemon

# 🤝 Server Sharing
mcpm share SERVER_NAME          # Share an installed server through secure tunnel
mcpm share SERVER_NAME --port 5000    # Share on specific port
mcpm share SERVER_NAME --retry 3      # Share with auto-retry on errors
```

### 📚 Registry

The MCP Registry is a central repository of available MCP servers that can be installed using MCPM. The registry is available at [mcpm.sh/registry](https://mcpm.sh/registry).

## 🗺️ Roadmap

### ✅ v2.0 Complete
- [x] Global server configuration model
- [x] Profile-based server tagging and organization  
- [x] Interactive command interfaces (InquirerPy)
- [x] Client integration management (`mcpm client edit`)
- [x] Modern CLI with consistent UX
- [x] Registry integration and server discovery
- [x] Direct server execution and sharing
- [x] Import from existing client configurations

### 🔮 Future Enhancements
- [ ] Enhanced router capabilities with profile switching
- [ ] Server access monitoring and analytics
- [ ] Additional client support (VS Code extensions, etc.)
- [ ] Advanced server configuration templates
- [ ] Server dependency management
- [ ] Plugin system for custom server types


## 📦 Other Installation Methods

### 🍺 Homebrew

```bash
brew install mcpm
```

### 📦 pipx (Recommended for Python tools)

```bash
pipx install mcpm
```

### 🪄 uv tool

```bash
uv tool install mcpm
```

## More Installation Methods

### 🐍 pip

```bash
pip install mcpm
```

### 🧰 X-CMD

If you are a user of [x-cmd](https://x-cmd.com), you can run:

```sh
x install mcpm.sh
```


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


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=pathintegral-institute/mcpm.sh&type=Date)](https://www.star-history.com/#pathintegral-institute/mcpm.sh&Date)