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

MCPM simplifies the installation, configuration, and management of Model Context Protocol servers and their configurations across different applications (clients). Key features include:

- ✨ Easy addition and removal of MCP server configurations for supported clients.
- 📋 Centralized management using profiles: group server configurations together and add/remove them to client easily.
- 🔍 Discovery of available MCP servers through a central registry.
- 🔌 MCPM Router for aggregating multiple MCP servers behind a single endpoint with shared sessions.
- 💻 A command-line interface (CLI) for all management tasks.

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

MCPM provides a comprehensive CLI built with Python's Click framework. Commands generally operate on the currently **active client**. You can view/set the active client using `mcpm client`. Many commands also support scope modifiers like `@CLIENT_NAME/SERVER_NAME` or `%PROFILE_NAME/SERVER_NAME` to target specific clients or profiles directly.

Below are the available commands, grouped by functionality:

### ℹ️ General

```bash
mcpm --help          # Display help information and available commands
mcpm --version       # Display the current version of MCPM
```

### 🖥️ Client Management (`client`)

```bash
mcpm client ls        # List all supported MCP clients, detect installed ones, and show active client
mcpm client edit      # Open the active client's MCP configuration file in an external editor
```

### 🌐 Server Management (`server`)

These commands operate on the active client unless a specific scope (`@CLIENT` or `%PROFILE`) is provided.

```bash
# 🔍 Search and Add
mcpm search [QUERY]       # Search the MCP Registry for available servers
mcpm add SERVER_URL       # Add an MCP server configuration (from URL or registry name)
mcpm add SERVER_URL --alias ALIAS # Add with a custom alias

# 🛠️ Add custom server
mcpm import stdio SERVER_NAME --command COMMAND --args ARGS --env ENV # Add a stdio MCP server to a client
mcpm import remote SERVER_NAME --url URL # Add a remote MCP server to a client
mcpm import interact # Add a server by configuring it interactively

# 📋 List and Remove
mcpm ls                   # List server configurations for the active client/profile
mcpm rm SERVER_NAME       # Remove a server configuration

# 🔄 Modify and Organize
mcpm cp SOURCE TARGET     # Copy a server config (e.g., @client1/serverA %profileB)
mcpm mv SOURCE TARGET     # Move a server config (e.g., %profileA/serverX @client2)

# 📦 Stashing (Temporarily disable/enable)
mcpm stash SERVER_NAME    # Temporarily disable/store a server configuration aside
mcpm pop [SERVER_NAME]    # Restore the last stashed server, or a specific one by name
```

### 📂 Profile Management (`profile`)

Profiles are named collections of server configurations. They allow you to easily switch between different sets of MCP servers. For example, you might have a `work` profile and a `personal` profile, each containing different servers. Or you might have a `production` profile and a `development` profile, each containing different configurations for the same servers.

The currently *active* profile's servers are typically used by features like the MCPM Router. Use `mcpm target set %profile_name` to set the active profile.

```bash
# 🔄 Profile Lifecycle
mcpm profile ls              # List all available MCPM profiles
mcpm profile add PROFILE_NAME  # Add a new, empty profile
mcpm profile rm PROFILE_NAME   # Remove a profile (does not delete servers within it)
mcpm profile rename OLD_NAME NEW_NAME # Rename a profile
mcpm add %profile_name    # Add a profile to the active client
```

### 🔌 Router Management (`router`)

The MCPM Router runs as a background daemon process, acting as a stable endpoint (e.g., `http://localhost:6276`) that intelligently routes incoming MCP requests to the appropriate server based on the currently **active profile**.

This allows you to change the underlying servers (by switching profiles with `mcpm target set %profile_name`) without reconfiguring your client applications. They can always point to the MCPM Router's address.

The Router also maintains persistent connections to MCP servers, enabling multiple clients to share these server sessions. This eliminates the need to start separate server instances for each client, significantly reducing resource usage and startup time. Learn more about these advanced capabilities in [Advanced Features](docs/advanced_features.md).

For more technical details on the router's implementation and namespacing, see [`docs/router_tech_design.md`](docs/router_tech_design.md).

The Router can be shared in public network by `mcpm router share`. Be aware that the share link will be exposed to the public, make sure the generated secret is secure and only share to trusted users. See [MCPM Router Share](docs/router_share.md) for more details about how it works.

```bash
mcpm router status                # Check if the router daemon is running
mcpm router on                    # Start the MCP router daemon
mcpm router off                   # Stop the MCP router daemon
mcpm router set --host HOST --port PORT --address ADDRESS  # Set the MCP router daemon's host port and the remote share address
mcpm router share                 # Share the router to public
mcpm router unshare               # Unshare the router
```

### 🤝 Share Management (`share`)

The `mcpm share` command allows you to take any shell command that starts an MCP server and instantly expose it as an SSE (Server-Sent Events) server. It uses `mcp-proxy` to handle the server transformation and then creates a secure tunnel for remote access, making your local MCP server accessible from anywhere.

This is particularly useful for quickly sharing a development server, a custom MCP server, or even a standard server with specific configurations without needing to deploy it publicly.

```bash
# 🚀 Share a local MCP server
mcpm share "COMMAND" # Replace COMMAND with your actual server start command

# ⚙️ Options
# COMMAND: The shell command that starts your MCP server (e.g., "uvx mcp-server-fetch", "npx mcp-server"). This must be enclosed in quotes if it contains spaces.
# --port PORT: Specify a local port for the mcp-proxy to listen on. Defaults to a random available port.
# --address ADDRESS: Specify a public address for the tunnel (e.g., yourdomain.com:7000). If not provided, a random tunnel URL will be generated.
# --http: If set, the tunnel will use HTTP instead of HTTPS. Use with caution.
# --timeout TIMEOUT: Timeout in seconds for the mcp-proxy to wait for the server to start. Defaults to 60.
# --retry RETRY: Number of times to retry starting the server if it fails. Defaults to 0.

# 💡 Usage Examples
mcpm share "uvx mcp-server-fetch"
mcpm share "npx mcp-server" --port 5000
mcpm share "uv run my-mcp-server" --address myserver.com:7000
mcpm share "npx -y @modelcontextprotocol/server-everything" --retry 3
```

### 🛠️ Utilities (`util`)

```bash
mcpm config clear-cache          # Clear MCPM's registry cache. Cache defaults to refresh every 1 hour.
mcpm config set                  # Set global MCPM configuration, currently only support node_executable 
mcpm config get <name>           # Get global MCPM configuration
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
- [x] MCP Profiles (`mcpm profile`)
- [x] Server copying/moving (`mcpm cp`, `mcpm mv`)
- [x] Server stashing (`mcpm stash`, `mcpm pop`)
- [x] Router remote share (`mcpm router share`) remotely access local router and mcp servers
- [ ] MCP Server Access Monitoring for MCPM Router (local only, absolutely no data leaving local machine)
- [ ] MCPM Router over STDIO (same powerful feature set with profile and monitoring, but single client/tenant)
- [ ] MCP Server for MCPM Router (experimental, allow MCP clients to dynamically switch between profiles, suggest new MCP servers from registry, etc.)
- [ ] Additional client support


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