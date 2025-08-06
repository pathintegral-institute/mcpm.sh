#!/usr/bin/env python3
"""
Generate LLM.txt documentation for AI agents from MCPM CLI structure.

This script automatically generates comprehensive documentation for AI agents
by introspecting the MCPM CLI commands and their options.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path so we can import mcpm modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import click

from mcpm.cli import main as mcpm_cli

# Try to import version, fallback to a default if not available
try:
    from mcpm.version import __version__
except ImportError:
    __version__ = "development"


def extract_command_info(cmd, parent_name=""):
    """Extract information from a Click command."""
    info = {
        "name": cmd.name,
        "full_name": f"{parent_name} {cmd.name}".strip(),
        "help": cmd.help or "No description available",
        "params": [],
        "subcommands": {}
    }

    # Extract parameters
    for param in cmd.params:
        param_info = {
            "name": param.name,
            "opts": getattr(param, "opts", None) or [param.name],
            "type": str(param.type),
            "help": getattr(param, "help", "") or "",
            "required": getattr(param, "required", False),
            "is_flag": isinstance(param, click.Option) and param.is_flag,
            "default": getattr(param, "default", None)
        }
        info["params"].append(param_info)

    # Extract subcommands if this is a group
    if isinstance(cmd, click.Group):
        for subcommand_name, subcommand in cmd.commands.items():
            info["subcommands"][subcommand_name] = extract_command_info(
                subcommand,
                info["full_name"]
            )

    return info


def format_command_section(cmd_info, level=2):
    """Format a command's information for the LLM.txt file."""
    lines = []

    # Command header
    header = "#" * level + f" {cmd_info['full_name']}"
    lines.append(header)
    lines.append("")

    # Description
    lines.append(cmd_info["help"])
    lines.append("")

    # Parameters
    if cmd_info["params"]:
        lines.append("**Parameters:**")
        lines.append("")

        # Separate arguments from options
        args = [p for p in cmd_info["params"] if not p["opts"][0].startswith("-")]
        opts = [p for p in cmd_info["params"] if p["opts"][0].startswith("-")]

        if args:
            for param in args:
                req = "REQUIRED" if param["required"] else "OPTIONAL"
                lines.append(f"- `{param['name']}` ({req}): {param['help']}")
            lines.append("")

        if opts:
            for param in opts:
                opt_str = ", ".join(f"`{opt}`" for opt in param["opts"])
                if param["is_flag"]:
                    lines.append(f"- {opt_str}: {param['help']} (flag)")
                else:
                    default_str = f" (default: {param['default']})" if param["default"] is not None else ""
                    lines.append(f"- {opt_str}: {param['help']}{default_str}")
            lines.append("")

    # Examples section
    examples = generate_examples_for_command(cmd_info)
    if examples:
        lines.append("**Examples:**")
        lines.append("")
        lines.append("```bash")
        lines.extend(examples)
        lines.append("```")
        lines.append("")

    # Subcommands
    for subcmd_info in cmd_info["subcommands"].values():
        lines.extend(format_command_section(subcmd_info, level + 1))

    return lines


def generate_examples_for_command(cmd_info):
    """Generate relevant examples for a command based on its name and parameters."""
    cmd = cmd_info["full_name"]

    # Map of command patterns to example sets
    example_map = {
        "mcpm new": [
            "# Create a stdio server",
            'mcpm new myserver --type stdio --command "python -m myserver"',
            "",
            "# Create a remote server",
            'mcpm new apiserver --type remote --url "https://api.example.com"',
            "",
            "# Create server with environment variables",
            'mcpm new myserver --type stdio --command "python server.py" --env "API_KEY=secret,PORT=8080"',
        ],
        "mcpm edit": [
            "# Update server name",
            'mcpm edit myserver --name "new-name"',
            "",
            "# Update command and arguments",
            'mcpm edit myserver --command "python -m updated_server" --args "--port 8080"',
            "",
            "# Update environment variables",
            'mcpm edit myserver --env "API_KEY=new-secret,DEBUG=true"',
        ],
        "mcpm install": [
            "# Install a server",
            "mcpm install sqlite",
            "",
            "# Install with environment variables",
            "ANTHROPIC_API_KEY=sk-ant-... mcpm install claude",
            "",
            "# Force installation",
            "mcpm install filesystem --force",
        ],
        "mcpm profile edit": [
            "# Add server to profile",
            "mcpm profile edit web-dev --add-server sqlite",
            "",
            "# Remove server from profile",
            "mcpm profile edit web-dev --remove-server old-server",
            "",
            "# Set profile servers (replaces all)",
            'mcpm profile edit web-dev --set-servers "sqlite,filesystem,git"',
            "",
            "# Rename profile",
            "mcpm profile edit old-name --name new-name",
        ],
        "mcpm client edit": [
            "# Add server to client",
            "mcpm client edit cursor --add-server sqlite",
            "",
            "# Add profile to client",
            "mcpm client edit cursor --add-profile web-dev",
            "",
            "# Set all servers for client",
            'mcpm client edit claude-desktop --set-servers "sqlite,filesystem"',
            "",
            "# Remove profile from client",
            "mcpm client edit cursor --remove-profile old-profile",
        ],
        "mcpm run": [
            "# Run a server",
            "mcpm run sqlite",
            "",
            "# Run with HTTP transport",
            "mcpm run myserver --http --port 8080",
        ],
        "mcpm profile run": [
            "# Run all servers in a profile",
            "mcpm profile run web-dev",
            "",
            "# Run profile with custom port",
            "mcpm profile run web-dev --port 8080 --http",
        ],
    }

    # Return examples if we have them for this command
    if cmd in example_map:
        return example_map[cmd]

    # Generate basic example if no specific examples
    if cmd_info["params"]:
        return ["# Basic usage", f"{cmd} <arguments>"]

    return []


def generate_llm_txt():
    """Generate the complete LLM.txt file content."""
    lines = [
        "# MCPM (Model Context Protocol Manager) - AI Agent Guide",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Version: {__version__}",
        "",
        "## Overview",
        "",
        "MCPM is a command-line tool for managing Model Context Protocol (MCP) servers. This guide is specifically designed for AI agents to understand how to interact with MCPM programmatically.",
        "",
        "## Key Concepts",
        "",
        "- **Servers**: MCP servers that provide tools, resources, and prompts to AI assistants",
        "- **Profiles**: Named groups of servers that can be run together",
        "- **Clients**: Applications that connect to MCP servers (Claude Desktop, Cursor, etc.)",
        "",
        "## Environment Variables for AI Agents",
        "",
        "```bash",
        "# Force non-interactive mode (no prompts)",
        "export MCPM_NON_INTERACTIVE=true",
        "",
        "# Skip all confirmations",
        "export MCPM_FORCE=true",
        "",
        "# Output in JSON format (where supported)",
        "export MCPM_JSON_OUTPUT=true",
        "",
        "# Server-specific environment variables",
        "export MCPM_SERVER_MYSERVER_API_KEY=secret",
        "export MCPM_ARG_API_KEY=secret  # Generic for all servers",
        "```",
        "",
        "## Command Reference",
        "",
    ]

    # Extract command structure
    cmd_info = extract_command_info(mcpm_cli)

    # Format main commands
    for subcmd_name in sorted(cmd_info["subcommands"].keys()):
        subcmd_info = cmd_info["subcommands"][subcmd_name]
        lines.extend(format_command_section(subcmd_info))

    # Add best practices section
    lines.extend([
        "## Best Practices for AI Agents",
        "",
        "### 1. Always Use Non-Interactive Mode",
        "",
        "```bash",
        "export MCPM_NON_INTERACTIVE=true",
        "export MCPM_FORCE=true",
        "```",
        "",
        "### 2. Error Handling",
        "",
        "- Check exit codes: 0 = success, 1 = error, 2 = validation error",
        "- Parse error messages from stderr",
        "- Implement retry logic for transient failures",
        "",
        "### 3. Server Management Workflow",
        "",
        "```bash",
        "# 1. Search for available servers",
        "mcpm search sqlite",
        "",
        "# 2. Get server information",
        "mcpm info sqlite",
        "",
        "# 3. Install server",
        "mcpm install sqlite --force",
        "",
        "# 4. Create custom server if needed",
        'mcpm new custom-db --type stdio --command "python db_server.py" --force',
        "",
        "# 5. Run server",
        "mcpm run sqlite",
        "```",
        "",
        "### 4. Profile Management Workflow",
        "",
        "```bash",
        "# 1. Create profile",
        "mcpm profile create web-stack --force",
        "",
        "# 2. Add servers to profile",
        "mcpm profile edit web-stack --add-server sqlite,filesystem",
        "",
        "# 3. Run all servers in profile",
        "mcpm profile run web-stack",
        "```",
        "",
        "### 5. Client Configuration Workflow",
        "",
        "```bash",
        "# 1. List available clients",
        "mcpm client ls",
        "",
        "# 2. Configure client with servers",
        "mcpm client edit cursor --add-server sqlite --add-profile web-stack",
        "",
        "# 3. Import existing client configuration",
        "mcpm client import cursor --all",
        "```",
        "",
        "## Common Patterns",
        "",
        "### Batch Operations",
        "",
        "```bash",
        "# Add multiple servers at once",
        'mcpm profile edit myprofile --add-server "server1,server2,server3"',
        "",
        "# Remove multiple servers",
        'mcpm client edit cursor --remove-server "old1,old2"',
        "```",
        "",
        "### Using Environment Variables for Secrets",
        "",
        "```bash",
        "# Set API keys via environment",
        "export ANTHROPIC_API_KEY=sk-ant-...",
        "export OPENAI_API_KEY=sk-...",
        "",
        "# Install servers that will use these keys",
        "mcpm install claude --force",
        "mcpm install openai --force",
        "```",
        "",
        "### Automation-Friendly Commands",
        "",
        "```bash",
        "# List all servers in machine-readable format",
        "mcpm ls --json",
        "",
        "# Get detailed server information",
        "mcpm info myserver --json",
        "",
        "# Check system health",
        "mcpm doctor",
        "```",
        "",
        "## Exit Codes",
        "",
        "- `0`: Success",
        "- `1`: General error",
        "- `2`: Validation error (invalid parameters)",
        "- `130`: Interrupted by user (Ctrl+C)",
        "",
        "## Notes for AI Implementation",
        "",
        "1. **Always specify all required parameters** - Never rely on interactive prompts",
        "2. **Use --force flag** to skip confirmations in automation",
        "3. **Parse JSON output** when available for structured data",
        "4. **Set environment variables** before running commands that need secrets",
        "5. **Check server compatibility** with `mcpm info` before installation",
        "6. **Use profiles** for managing groups of related servers",
        "7. **Validate operations** succeeded by checking exit codes and output",
        "",
        "## Troubleshooting",
        "",
        "- If a command hangs, ensure `MCPM_NON_INTERACTIVE=true` is set",
        "- For permission errors, check file system permissions on config directories",
        "- For server failures, check logs with `mcpm run <server> --verbose`",
        "- Use `mcpm doctor` to diagnose system issues",
        "",
    ])

    return "\n".join(lines)


def main():
    """Generate and save the LLM.txt file."""
    content = generate_llm_txt()

    # Determine output path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_path = project_root / "llm.txt"

    # Write the file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Generated llm.txt at: {output_path}")
    print(f"📄 File size: {len(content):,} bytes")
    print(f"📝 Lines: {content.count(chr(10)):,}")


if __name__ == "__main__":
    main()
