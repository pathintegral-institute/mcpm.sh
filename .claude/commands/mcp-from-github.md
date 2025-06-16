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

**Required JSON Structure:**
- Follow the exact schema from `mcp-registry/schema/server-schema.json`
- Include all required fields: name, display_name, description, repository, license, installations
- Generate kebab-case name from repository name
- Extract or infer categories and tags
- Parse installation instructions into proper installation objects
- Extract tool schemas from code or documentation
- Include realistic examples based on the server's functionality

**Validation:**
- Ensure the generated JSON is valid according to the schema
- Check that installation commands are correct for the detected package type
- Verify that argument descriptions match the actual requirements

**Output:**
Create the JSON file and confirm successful generation with the file path and basic server information.