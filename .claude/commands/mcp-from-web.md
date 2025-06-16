Generate a new MCP server configuration JSON file based on a web URL containing MCP server documentation.

**Instructions:**
1. Fetch and analyze the web page content from the provided URL: $ARGUMENTS
2. Extract information about the MCP server including:
   - Server name and description
   - Repository URL (if mentioned)
   - Installation instructions
   - Configuration requirements
   - Available tools and their capabilities
   - Usage examples and documentation
   - Dependencies and prerequisites
3. If the page links to a GitHub repository, also fetch repository metadata
4. Generate a complete JSON configuration following the schema in `mcp-registry/schema/server-schema.json`
5. Save the generated configuration to `mcp-registry/servers/{server-name}.json`

**Information Extraction:**
- Look for installation commands (npm install, pip install, docker run, etc.)
- Identify environment variables and configuration parameters
- Parse API documentation for tool schemas
- Extract code examples and convert them to usage examples
- Determine appropriate categories based on functionality described
- Infer server capabilities from the documentation

**Required JSON Structure:**
- Follow the exact schema from `mcp-registry/schema/server-schema.json`
- Include all required fields: name, display_name, description, repository, license, installations
- Generate appropriate kebab-case name from the documentation
- Map installation instructions to proper installation method objects
- Create tool schemas based on API documentation
- Include realistic examples derived from the documentation

**Fallback Strategy:**
- If repository URL is not found, mark repository type as "git" with the provided URL
- If license is not specified, use "Unknown" or make reasonable inference
- If installation methods are unclear, provide generic installation template
- Include disclaimer in description if information is incomplete

**Output:**
Create the JSON file and confirm successful generation with the file path, basic server information, and any assumptions made during generation.