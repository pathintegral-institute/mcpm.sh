# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Development Commands

### Testing and Linting
```bash
pytest tests/                    # Run all tests
pytest tests/test_specific.py    # Run specific test file
ruff check                       # Run linting
ruff check --fix                 # Auto-fix linting issues
```

### Development CLI Testing
```bash
./test_cli.py --help            # Test CLI without installation
./test_cli.py <command>         # Run any CLI command in development
```

### Environment Setup
```bash
uv venv --seed                  # Create virtual environment
source .venv/bin/activate       # Activate environment (Unix/Mac)
uv pip install -e .             # Install in development mode
```

### Version Management
```bash
./bump_version.sh 1.2.3         # Bump version to 1.2.3
git push && git push --tags     # Push version changes
```

### Website Development
```bash
./dev.sh                        # Start Jekyll development server with file watching
```

## Architecture Overview

MCPM is a Python CLI tool for managing Model Context Protocol (MCP) servers across different AI clients. The architecture consists of several key components:

### Core Architecture

**Client Management System**: The `src/mcpm/clients/` directory contains the abstraction layer for different MCP clients (Claude Desktop, Cursor, Windsurf, etc.). Each client has its own manager that handles configuration file formats and locations.

**Profile System**: MCPM supports grouping server configurations into named profiles (`src/mcpm/profile/`). This allows users to switch between different sets of MCP servers easily.

**Router Component**: The `src/mcpm/router/` module implements a sophisticated HTTP router that aggregates multiple MCP servers behind a single endpoint. Key features:
- Maintains persistent connections to MCP servers
- Enables session sharing between multiple clients
- Provides namespacing to prevent conflicts
- Supports real-time configuration changes

**Registry Integration**: MCPM includes an internal registry (`mcp-registry/`) with curated MCP servers. The registry data is processed by Python scripts in `scripts/` to generate API endpoints.

**Monitor System**: The `src/mcpm/monitor/` directory contains access monitoring capabilities using DuckDB for local analytics.

### Key Design Patterns

**Target System**: MCPM uses a "target" concept where commands operate on either a specific client (`@client_name`) or profile (`%profile_name`). The active target is managed by `ClientConfigManager`.

**Scope Modifiers**: Commands support scope syntax like `@CLIENT_NAME/SERVER_NAME` or `%PROFILE_NAME/SERVER_NAME` for precise targeting across the system.

**Configuration Management**: All client configurations are abstracted through the `clients/base.py` interface, allowing uniform operations across different client types.

## Project Structure Highlights

- `src/mcpm/cli.py`: Main CLI entry point with Click framework
- `src/mcpm/commands/`: Individual CLI command implementations
- `src/mcpm/clients/managers/`: Client-specific configuration handlers
- `src/mcpm/router/`: HTTP router for MCP server aggregation
- `src/mcpm/schemas/`: Pydantic models for configuration validation
- `mcp-registry/`: Internal registry of curated MCP servers
- `scripts/`: Registry processing and website generation tools

## Development Guidelines

### Commit Messages
Follow conventional commit format:
- `feat: add new feature`
- `fix: resolve bug issue`
- `docs: update documentation`
- `chore: maintenance tasks`

### Code Quality
- Always run `ruff check --fix` after code changes
- Always run `pytest` after major changes
- Use the development CLI script `./test_cli.py` for testing commands

### Version Management
- Version is managed in `src/mcpm/version.py` as single source of truth
- Use `./bump_version.sh` script for version updates
- `pyproject.toml` uses dynamic versioning to read from version.py

## Testing Strategy

The test suite covers:
- CLI command functionality (`tests/test_cli.py`)
- Client manager operations (`tests/test_client.py`)
- Router functionality (`tests/test_router.py`)
- Profile management (`tests/test_profile.py`) 
- Server operations (add/remove/stash/pop)

Tests use pytest with configuration in `pyproject.toml`. Individual test files can be run independently for targeted testing.