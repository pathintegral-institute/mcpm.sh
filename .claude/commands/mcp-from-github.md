Generate a new MCP server configuration JSON file based on a GitHub repository.

**Instructions:**
1. Analyze the provided GitHub repository URL or owner/repo format: $ARGUMENTS
2. Fetch the repository information using GitHub API tools
3. Read the repository's README.md, package.json, pyproject.toml, or other relevant files to understand:
   - Server name and description
   - Installation methods (npm, python, docker, etc.)
   - Required arguments/environment variables
   - Available tools and their schemas
   - Resources provided by the server
   - Usage examples
4. Generate a complete JSON configuration following the schema in `mcp-registry/schema/server-schema.json`
5. Save the generated configuration to `mcp-registry/servers/{server-name}.json`

**Special Handling for Melio Organization:**
- If the GitHub repository belongs to the "melio" organization (github.com/melio/*), use the `clone-install-run.sh` installation method
- Structure the installation as a custom type with `clone-install-run.sh` command
- Set environment variables: `MCP_REPO_URL`, `MCP_SETUP_COMMAND`, `MCP_RUN_COMMAND`
- Include any required environment variables for the specific MCP server
- Reference examples: `mcp-registry/servers/figma.json` and `mcp-registry/servers/jira.json`

**Required JSON Structure:**
- Follow the exact schema from `mcp-registry/schema/server-schema.json`
- Include all required fields: name, display_name, description, repository, license, installations
- Generate kebab-case name from repository name
- Extract or infer categories and tags
- For Melio repos: Use custom installation type with `clone-install-run.sh`
- For other repos: Parse installation instructions into proper installation objects
- Extract tool schemas from code or documentation
- Include realistic examples based on the server's functionality

**Installation Method Detection:**
- Melio organization repos → Use `clone-install-run.sh` with custom installation type
- Node.js projects (package.json) → Use npm installation
- Python projects (pyproject.toml, setup.py) → Use python/pip installation
- Docker projects (Dockerfile) → Use docker installation

**Validation:**
- Ensure the generated JSON is valid according to the schema
- Check that installation commands are correct for the detected package type
- For Melio repos: Verify MCP_SETUP_COMMAND and MCP_RUN_COMMAND match the project's build/run instructions
- Verify that argument descriptions match the actual requirements

**Output:**
Create the JSON file and confirm successful generation with the file path and basic server information.