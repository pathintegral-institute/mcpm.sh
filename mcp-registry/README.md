# MCP Server Registry

The MCP Server Registry is a central repository of [Model Context Protocol](https://modelcontextprotocol.github.io/) servers. This registry enables easy discovery and installation of MCP servers for clients like Claude Desktop, Cursor, and Windsurf.

## What is MCP?

Model Context Protocol (MCP) is a standard for building LLM-powered tools. It enables language models to use external tools, resources, and capabilities in a standardized way.

## How to Use This Registry

### Browsing Servers

Browse the `servers` directory to find MCP servers that match your needs. Each server has its own directory with a `manifest.json` file containing configuration details and a `README.md` with documentation.

### Installing Servers

Various MCP management tools can use this registry to install and configure servers. One such tool is [getmcp.sh](https://mcpm.sh), a Homebrew-like package manager for MCP servers.

## Adding Your Server

To add your server to the registry, see the [Contributing Guidelines](CONTRIBUTING.md).

## Registry Structure

```
mcp-registry/
├── README.md               # Overview, usage instructions
├── CONTRIBUTING.md         # Guidelines for contributing servers
├── servers/                # Directory containing all registered servers
│   ├── [server-name]/      # Directory for each server
│   │   ├── manifest.json   # Server metadata and configuration
│   │   ├── README.md       # Detailed server documentation
│   │   └── examples/       # Optional usage examples
├── schema/                 # Schema definitions
│   └── manifest-schema.json  # JSON Schema for manifest validation
└── tools/                  # Helper scripts for validation, etc.
```

## License

This registry is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
