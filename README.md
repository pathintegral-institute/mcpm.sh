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

MCPM is an open source CLI tool for managing MCP servers. It provides a simplified global configuration approach where you install servers once and organize them with profiles, then integrate them into any MCP client. Features include server discovery through a central registry, direct execution, sharing capabilities, and client integration tools.

Demo is showing outdated v1 commands, new demo is baking ...
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

MCPM v2.0 provides a simplified approach to managing MCP servers with a global configuration model. Key features include:

- ✨ **Global Server Management**: Install servers once, use everywhere
- 📋 **Virtual Profiles**: Organize servers with tags for different workflows  
- 🔍 **Server Discovery**: Browse and install from the MCP Registry
- 🚀 **Direct Execution**: Run servers over stdio or HTTP for testing
- 🌐 **Public Sharing**: Share servers through secure tunnels
- 🎛️ **Client Integration**: Manage configurations for Claude Desktop, Cursor, Windsurf, and more
- 💻 **Beautiful CLI**: Rich formatting and interactive interfaces
- 📊 **Usage Analytics**: Monitor server usage and performance

MCPM v2.0 eliminates the complexity of v1's target-based system in favor of a clean global workspace model.

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

MCPM provides a comprehensive CLI with a clean, organized interface. The v2.0 architecture uses a global configuration model where servers are installed once and can be organized with profiles, then integrated into specific MCP clients as needed.

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
mcpm info SERVER_NAME         # Display detailed information about a server
mcpm install SERVER_NAME      # Install a server from registry to global configuration
mcpm uninstall SERVER_NAME    # Remove a server from global configuration

# 📋 List and Inspect
mcpm ls                       # List all installed servers and their profile assignments
mcpm edit SERVER_NAME         # Edit a server configuration
mcpm inspect SERVER_NAME      # Launch MCP Inspector to test/debug a server
```

### 🚀 Server Execution

Execute servers directly for testing or integration:

```bash
mcpm run SERVER_NAME          # Execute a server directly over stdio
mcpm run SERVER_NAME --http   # Execute a server over HTTP for testing
mcpm share SERVER_NAME        # Share a server through secure tunnel for remote access
mcpm usage                    # Display comprehensive analytics and usage data
```

### 📂 Profile Management

Profiles are virtual tags that organize servers into logical groups for different workflows:

```bash
# 🔄 Profile Operations
mcpm profile ls               # List all profiles and their tagged servers
mcpm profile create PROFILE   # Create a new profile
mcpm profile rm PROFILE       # Remove a profile (servers remain installed)
mcpm profile edit PROFILE     # Interactive server selection for profile

# 🚀 Profile Execution
mcpm profile run PROFILE      # Execute all servers in a profile over stdio or HTTP
mcpm profile share PROFILE    # Share all servers in a profile through secure tunnel
mcpm profile inspect PROFILE  # Launch MCP Inspector for all servers in profile
```

### 🖥️ Client Integration

Manage MCP client configurations (Claude Desktop, Cursor, Windsurf, etc.):

```bash
mcpm client ls                 # List all supported MCP clients and their status
mcpm client edit CLIENT_NAME   # Interactive server enable/disable for a client
mcpm client edit CLIENT_NAME -e # Open client config in external editor
mcpm client import CLIENT_NAME  # Import server configurations from a client
```

### 🛠️ System & Configuration

```bash
mcpm doctor                   # Check system health and server status
mcpm config                   # Manage MCPM configuration and settings
mcpm migrate                  # Migrate from v1 to v2 configuration
```

### 📚 Registry

The MCP Registry is a central repository of available MCP servers that can be installed using MCPM. The registry is available at [mcpm.sh/registry](https://mcpm.sh/registry).

## 🗺️ Roadmap

### ✅ v2.0 Complete
- [x] Global server configuration model
- [x] Profile-based server tagging and organization  
- [x] Interactive command interfaces
- [x] Client integration management (`mcpm client edit`)
- [x] Modern CLI with consistent UX
- [x] Registry integration and server discovery
- [x] Direct server execution and sharing
- [x] Import from existing client configurations

### 🔮 Future Enhancements
- [ ] Advanced Server access monitoring and analytics
- [ ] Additional client support (gemini-cli, codex, etc.)
- [ ] Execution in docker


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