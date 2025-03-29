# Contributing to mcpm.sh

Thank you for considering contributing to mcpm.sh! This document outlines the process for adding or updating MCP servers in the registry.

## Adding a New Server

1. Fork this repository
2. Create a new JSON file named after your server under `mcp-registry/servers/` (use kebab-case, e.g., `github.json` or `time-converter.json`)
3. Ensure your server JSON file adheres to the [server schema](/mcp-registry/schema/server-schema.json)

### Server JSON Requirements

Your server JSON file must include the following required fields:

```json
{
  "name": "your-server-name",
  "display_name": "Your Server Display Name",
  "description": "Brief description of the server's functionality",
  "repository": {
    "type": "git",
    "url": "https://github.com/your-username/your-repo"
  },
  "author": {
    "name": "Your Name"
  },
  "license": "MIT",
  "categories": ["category1", "category2"],
  "tags": ["tag1", "tag2"],
  "arguments": {
    "EXAMPLE_ARG": {
      "description": "Description of this argument",
      "required": false
    }
  },
  "commands": {
    "npm": {
      "type": "npm",
      "command": "npx",
      "args": ["your-server-package"],
      "env": {
        "EXAMPLE_ARG": "${EXAMPLE_ARG}"
      }
    }
  },
  "examples": [
    {
      "title": "Example usage",
      "description": "Brief description of example",
      "prompt": "Example prompt to demonstrate server functionality"
    }
  ]
}
```

For a complete reference of all available fields, see the [server schema](/mcp-registry/schema/server-schema.json).

## Schema Validation

All server JSON files are automatically validated against the schema during the CI process. You can also validate your server JSON locally using the prepare.py script:

```bash
# From the repository root
python scripts/prepare.py mcp-registry pages --validate-only
```

## Updating an Existing Server

1. Fork this repository
2. Update the relevant server JSON file in the `mcp-registry/servers/` directory
3. Submit a pull request with a clear description of your changes

## Website Development

If you want to contribute to the mcpm.sh website itself:

1. Fork and clone the repository
2. Run the development server:

```bash
./dev.sh
```

3. Access the site at http://localhost:4000
4. Make your changes to the files in the `pages/` directory
5. Submit a pull request with a clear description of your changes

## Design Guidelines

mcpm.sh follows a minimal, clean design philosophy:

- Stick to a minimal black and white color scheme
- Focus on functionality and readability
- Follow modern web design patterns
- Keep UI elements simple and focused on content

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project, you agree to abide by its terms.

## License

By contributing to this repository, you agree to license your contributions under the same license as this repository.
