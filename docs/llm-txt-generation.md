# llm.txt Generation for AI Agents

## Overview

MCPM automatically generates an `llm.txt` file that provides comprehensive documentation for AI agents on how to interact with the MCPM CLI programmatically. This ensures that AI agents always have up-to-date information about command-line interfaces and parameters.

## What is llm.txt?

llm.txt is a markdown-formatted documentation file specifically designed for Large Language Models (AI agents) to understand how to interact with CLI tools. It includes:

- **Complete command reference** with all parameters and options
- **Usage examples** for common scenarios
- **Environment variables** for automation
- **Best practices** for AI agent integration
- **Error codes and troubleshooting** information

## Automatic Generation

The llm.txt file is automatically generated using the `scripts/generate_llm_txt.py` script, which:

1. **Introspects the CLI structure** using Click's command hierarchy
2. **Extracts parameter information** including types, defaults, and help text
3. **Generates relevant examples** based on command patterns
4. **Includes environment variables** and automation patterns
5. **Formats everything** in a structured, AI-agent friendly format

## Generation Triggers

The llm.txt file is regenerated automatically in these scenarios:

### 1. GitHub Actions (CI/CD)

- **On releases**: When a new version is published
- **On main branch commits**: When CLI-related files change
- **Manual trigger**: Via GitHub Actions workflow dispatch

### 2. Local Development

Developers can manually regenerate the file:

```bash
# Using the generation script directly
python scripts/generate_llm_txt.py

# Using the convenience script
./scripts/update-llm-txt.sh
```

## File Structure

The generated llm.txt follows this structure:

```
# MCPM - AI Agent Guide

## Overview
- Tool description
- Key concepts

## Environment Variables for AI Agents
- MCPM_NON_INTERACTIVE
- MCPM_FORCE
- MCPM_JSON_OUTPUT
- Server-specific variables

## Command Reference
- Each command with parameters
- Usage examples
- Subcommands recursively

## Best Practices for AI Agents
- Automation patterns
- Error handling
- Common workflows

## Troubleshooting
- Common issues and solutions
```

## Customization

### Adding New Examples

To add examples for new commands, edit the `example_map` in `scripts/generate_llm_txt.py`:

```python
example_map = {
    'mcpm new': [
        '# Create a stdio server',
        'mcpm new myserver --type stdio --command "python -m myserver"',
    ],
    'mcpm your-new-command': [
        '# Your example here',
        'mcpm your-new-command --param value',
    ]
}
```

### Modifying Sections

The script generates several predefined sections. To modify content:

1. Edit the `generate_llm_txt()` function
2. Update the `lines` list with your changes
3. Test locally: `python scripts/generate_llm_txt.py`

## Integration with CI/CD

The GitHub Actions workflow (`.github/workflows/generate-llm-txt.yml`) handles:

1. **Automatic updates** when CLI changes are detected
2. **Pull request creation** for releases
3. **Version tracking** in the generated file
4. **Error handling** if generation fails

### Workflow Configuration

Key configuration options in the GitHub Actions workflow:

- **Trigger paths**: Only runs when CLI-related files change
- **Commit behavior**: Auto-commits changes with `[skip ci]`
- **Release behavior**: Creates PRs for manual review
- **Dependencies**: Installs MCPM before generation

## Benefits for AI Agents

1. **Always Up-to-Date**: Automatically reflects CLI changes
2. **Comprehensive**: Covers all commands, parameters, and options
3. **Structured**: Consistent format for parsing
4. **Practical**: Includes real-world usage examples
5. **Complete**: Covers automation, error handling, and troubleshooting

## Maintenance

### Updating the Generator

When adding new CLI commands or options:

1. The generator automatically detects new commands via Click introspection
2. Add specific examples to the `example_map` if needed
3. Update environment variable documentation if new variables are added
4. Test locally before committing

### Version Compatibility

The generator is designed to be compatible with:

- **Click framework**: Uses standard Click command introspection
- **Python 3.8+**: Compatible with the MCPM runtime requirements
- **Cross-platform**: Works on Linux, macOS, and Windows

### Troubleshooting Generation

If the generation fails:

1. **Check imports**: Ensure all MCPM modules can be imported
2. **Verify CLI structure**: Ensure commands are properly decorated
3. **Test locally**: Run `python scripts/generate_llm_txt.py`
4. **Check dependencies**: Ensure Click and other deps are installed

## Contributing

When contributing new CLI features:

1. **Add examples** to the example map for new commands
2. **Document environment variables** if you add new ones
3. **Test generation** locally before submitting PR
4. **Update this documentation** if you modify the generation process

## Future Enhancements

Potential improvements to the generation system:

- **JSON Schema generation** for structured API documentation
- **Interactive examples** with expected outputs
- **Multi-language examples** for different automation contexts
- **Plugin system** for custom documentation sections
- **Integration testing** to verify examples work correctly