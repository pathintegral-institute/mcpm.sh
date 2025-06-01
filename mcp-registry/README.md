# 🔧 Internal MCP Installer

This is an internal MCP (Model Context Protocol) installer containing a curated set of 9 supported MCP servers. This installer provides reliable, tested MCP servers for use with clients like Claude Desktop, Cursor, and Windsurf.

<div align="center">
<img src="https://img.shields.io/badge/Status-Internal-orange" alt="Status: Internal">
<img src="https://img.shields.io/badge/Servers-9-blue" alt="Servers: 9">
</div>

## 🤔 What is MCP?

Model Context Protocol (MCP) is a standard for building LLM-powered tools. It enables language models to use external tools, resources, and capabilities in a standardized way.

- 🔄 **Standard Interface**: Common protocol for LLMs to interact with tools
- 🧩 **Composable**: Mix and match tools from different providers
- 🚀 **Portable**: Works across different clients and environments

## 📦 Supported MCP Servers

This internal installer includes the following 9 curated MCP servers:

### Internal Servers (Melio)
- **atlassian.json** - Atlassian/Jira integration tools
- **figma.json** - Figma design tool integration
- **mysql.json** - MySQL database operations

### External Servers (Verified)
- **aws.json** - AWS cloud services integration (awslabs)
- **circleci.json** - CircleCI CI/CD pipeline integration (CircleCI-Public)
- **github.json** - GitHub repository and issue management (github)
- **notion-mcp.json** - Notion workspace integration (makenotion)
- **playwright-mcp.json** - Browser automation and testing (microsoft)
- **serverless.json** - Serverless framework operations (serverless)

## 🧰 How to Use This Installer

### 🔍 Browsing Available Servers

Browse the `servers/` directory to find the 9 supported MCP servers. Each server configuration file (`*.json`) contains:

- 📄 Server metadata and configuration details
- 🔗 Installation endpoints and version information
- 🏷️ Categorization and capability descriptions

### ⬇️ Installing Servers

Install servers using [MCPM](https://github.com/pathintegral-institute/mcpm.sh):

```bash
# Install a server by name
mcpm add server-name

# Examples:
mcpm add atlassian
mcpm add github
mcpm add playwright-mcp
```

Alternatively, you can manually configure servers using the URLs and settings from the JSON files.

## 🏗️ Server Categories

Our 9 supported servers are organized by functionality:

- **Development Tools**: github, circleci, playwright-mcp, serverless
- **Design & Productivity**: figma, notion-mcp
- **Infrastructure**: aws, mysql
- **Project Management**: atlassian

## 📂 Registry Structure

```
mcp-registry/
├── README.md               # This file - overview and usage
├── servers/                # 9 supported MCP server configurations
│   ├── atlassian.json      # Atlassian/Jira integration
│   ├── aws.json           # AWS cloud services
│   ├── circleci.json      # CircleCI CI/CD
│   ├── figma.json         # Figma design tools
│   ├── github.json        # GitHub integration
│   ├── mysql.json         # MySQL database
│   ├── notion-mcp.json    # Notion workspace
│   ├── playwright-mcp.json # Browser automation
│   └── serverless.json    # Serverless framework
└── schema/                 # Schema definitions
    └── server-schema.json  # JSON Schema for server validation
```

## 🔄 Updates and Maintenance

This internal installer is maintained with a fixed set of 9 verified MCP servers. Updates to server configurations are applied through controlled releases to ensure compatibility and reliability.

## 📜 License

This internal installer is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
