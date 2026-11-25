# 📚 MCP Server Registry

The MCP Server Registry is a central repository of [Model Context Protocol](https://modelcontextprotocol.github.io/) servers. This registry enables easy discovery and installation of MCP servers for clients like Claude Desktop, Cursor, and Windsurf.

<div align="center">
<img src="https://img.shields.io/badge/Status-Active-brightgreen" alt="Status: Active">
<img src="https://img.shields.io/badge/Contributions-Welcome-blue" alt="Contributions: Welcome">
</div>

## 🤔 What is MCP?

Model Context Protocol (MCP) is a standard for building LLM-powered tools. It enables language models to use external tools, resources, and capabilities in a standardized way.

- 🔄 **Standard Interface**: Common protocol for LLMs to interact with tools
- 🧩 **Composable**: Mix and match tools from different providers
- 🚀 **Portable**: Works across different clients and environments

## 🧰 How to Use This Registry

### 🔍 Browsing Servers

Browse the `servers` directory to find MCP servers that match your needs. Each server has its own directory with:

- 📄 `[server-name].json` - Configuration details including endpoint, capabilities, and version
- 📝 `README.md` - Documentation with usage examples and requirements
- 🧪 Examples folder (optional)

### ⬇️ Installing Servers

You can install servers from this registry using:

1. **[MCPM](https://github.com/pathintegral-institute/mcpm.sh)**: Our recommended tool
   ```bash
   # Install a server by name
   mcpm add server-name
   ```

2. **Manual Configuration**: Add the server URL directly to your MCP client's configuration

## 🤝 Contributing Your Server

We welcome contributions! There are two ways to add your server to the registry:

### 1. Create a GitHub Issue (Easiest)

Simply create a [new GitHub issue](https://github.com/pathintegral-institute/mcpm.sh/issues/new) with:

- Title: "Add server: [your-server-name]"
- Body: URL to your server details or API documentation
- We'll automatically generate the necessary files and create a PR for you

### 2. Submit a Pull Request

For more control over your submission:

1. Fork this repository
2. Create a JSON file in `mcp-registry/servers/` named `[your-server-name].json`. The JSON should follow our [schema](schema/server-schema.json)
3. Validate locally to ensure correct schema
   ```bash
   python scripts/validate_manifest.py | grep "your-server-name"
   ```
   If validation succeeds, you should see:
   ```
   ✓ your-server-name: Valid
   ```
4. Submit a pull request

For an HTTP installation, set `"transport": "streamablehttp"` when the remote server requires Streamable HTTP, or `"transport": "sse"` for an explicit SSE selection. MCPM preserves this setting through installation and stdio proxy export. Omitting it retains the existing behavior; transport is not inferred from the URL.

## 📂 Registry Structure

```
mcp-registry/
├── README.md               # Overview, usage instructions
├── servers/                # Directory containing all registered servers
│   ├── [server-1-name].json   # Server metadata and configuration
│   ├── [server-2-name].json   
│   └── ...
└── schema/                 # Schema definitions
    └── server-schema.json  # JSON Schema for server validation
```

## 📜 License

This registry is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
