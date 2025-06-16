Create a new MCP server configuration JSON file through an interactive guided process.

**Instructions:**
Start an interactive session to gather information for creating a complete MCP server configuration. Use the optional arguments as initial context: $ARGUMENTS

**Interactive Prompts - Ask the user for:**

1. **Basic Information:**
   - Server name (will be converted to kebab-case)
   - Display name (human-readable)  
   - Description of the server's functionality
   - Repository URL (GitHub, GitLab, etc.)
   - License type
   - Author name and optional email/URL

2. **Categorization:**
   - Primary category from: Databases, Dev Tools, Productivity, Media Creation, Web Services, Knowledge Base, AI Systems, System Tools, Messaging, Finance, Analytics, Professional Apps, MCP Tools
   - Additional tags (comma-separated)

3. **Installation Methods:**
   - Preferred installation method (npm, python, docker, cli, uvx, custom)
   - Package name (if applicable)
   - Installation command and arguments
   - Required environment variables
   - Any additional installation methods

4. **Configuration:**
   - Required arguments/environment variables with descriptions and examples
   - Optional configuration parameters

5. **Capabilities:**
   - Tools provided by the server (name and brief description for each)
   - Resources offered (if any)
   - Prompts available (if any)

6. **Examples:**
   - Provide 3-5 example usage scenarios with titles, descriptions, and prompts

**Process:**
1. Present questions in a clear, organized manner
2. Validate responses and ask for clarification when needed
3. Provide helpful examples and suggestions
4. Show a preview of the generated configuration before saving
5. Generate the complete JSON following the schema in `mcp-registry/schema/server-schema.json`
6. Save to `mcp-registry/servers/{server-name}.json`

**Validation:**
- Ensure all required schema fields are populated
- Validate that the server name is unique in the registry
- Check that installation commands are syntactically correct
- Verify that examples are realistic and useful

**Output:**
Create the JSON file with proper formatting and confirm successful generation with the file path and a summary of the server configuration created.