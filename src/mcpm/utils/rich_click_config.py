"""
Rich-click configuration for MCPM CLI.
"""

import rich_click as click

# Configure rich-click globally for beautiful CLI formatting
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.SHOW_METAVARS_COLUMN = False
click.rich_click.APPEND_METAVARS_HELP = True

# Error styling
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"
click.rich_click.ERRORS_SUGGESTION = "💡 Try running the '--help' flag for more information."
click.rich_click.ERRORS_EPILOGUE = ""

# Color scheme
click.rich_click.STYLE_OPTION = "bold cyan"
click.rich_click.STYLE_ARGUMENT = "bold cyan"
click.rich_click.STYLE_COMMAND = "bold cyan"
click.rich_click.STYLE_SWITCH = "bold green"
click.rich_click.STYLE_METAVAR = "bold yellow"
click.rich_click.STYLE_METAVAR_BRACKET = "dim"
click.rich_click.STYLE_HELPTEXT = ""
click.rich_click.STYLE_HELPTEXT_FIRST_LINE = "bold"
click.rich_click.STYLE_OPTION_HELP = ""
click.rich_click.STYLE_USAGE = "bold"
click.rich_click.STYLE_USAGE_COMMAND = "bold cyan"

# Layout
click.rich_click.ALIGN_ERRORS_LEFT = True
click.rich_click.WIDTH = None  # Use terminal width
click.rich_click.MAX_WIDTH = 100  # Maximum width for better readability

# Disable command groups for main help since we have custom help logic
# Rich-click will still format individual command help beautifully
click.rich_click.COMMAND_GROUPS = {}

# Option groupings for subcommands
click.rich_click.OPTION_GROUPS = {
    "mcpm": [
        {
            "name": "Global Options",
            "options": ["--version", "--help"],
        },
    ],
    "mcpm run": [
        {
            "name": "Execution Mode",
            "options": ["--http", "--port"],
        },
        {
            "name": "Help",
            "options": ["--help"],
        },
    ],
    "mcpm share": [
        {
            "name": "Tunnel Configuration",
            "options": ["--port", "--subdomain", "--auth", "--local-only"],
        },
        {
            "name": "Help",
            "options": ["--help"],
        },
    ],
    "mcpm install": [
        {
            "name": "Installation Source",
            "options": ["--github", "--local", "--source-url"],
        },
        {
            "name": "Configuration",
            "options": ["--name", "--args", "--env"],
        },
        {
            "name": "Help",
            "options": ["--help"],
        },
    ],
}

# Export the configured click module
__all__ = ["click"]
