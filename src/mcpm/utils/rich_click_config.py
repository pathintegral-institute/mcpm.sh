"""
Rich-click configuration for MCPM CLI.
"""

import rich_click as click
from rich.console import Console
from rich.text import Text
from rich_gradient import Gradient

from mcpm import __version__

# Configure rich-click globally for beautiful CLI formatting
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.SHOW_METAVARS_COLUMN = False
click.rich_click.APPEND_METAVARS_HELP = True

# Get version dynamically


# Export header and footer for use in main command
def get_header_text():
    # ASCII art logo - simplified with light shades
    ASCII_ART = """
    ███░   ███░  ██████░ ██████░  ███░   ███░
    ████░ ████░ ██░░░░░░ ██░░░██░ ████░ ████░
    ██░████░██░ ██░      ██████░░ ██░████░██░
    ██░░██░░██░ ██░      ██░░░░░  ██░░██░░██░
    ██░ ░░░ ██░ ░██████░ ██░      ██░ ░░░ ██░
    ░░░     ░░░  ░░░░░░░ ░░░      ░░░     ░░░

    """

    # Create an elegant logo with ocean-to-sunset gradient using rich.text.Text
    header_text = Text()

    # Create gradient ASCII art using rich-gradient with purple-to-pink colors
    gradient_colors = ["#8F87F1", "#C68EFD", "#E9A5F1", "#FED2E2"]

    # Create a console with narrower width to force gradient calculation over ASCII width
    temp_console = Console(width=80)  # Close to ASCII art width

    # Create gradient and render it with the narrow console
    ascii_gradient = Gradient(ASCII_ART, colors=gradient_colors)  # type: ignore

    # Capture the rendered gradient
    with temp_console.capture() as capture:
        temp_console.print(ascii_gradient, justify="center")
    rendered_ascii = capture.get()

    # Add to header text
    header_text = Text.from_ansi(rendered_ascii)

    header_text.append("\n")

    # Add solid color text for title and tagline - harmonized with gradient
    prose = Text()
    prose.append("Model Context Protocol Manager", style="#8F87F1 bold")
    prose.append(" v", style="#C68EFD")
    prose.append(__version__, style="#E9A5F1 bold")
    prose.append("\n")
    prose.append("Open Source with ", style="#FED2E2")
    prose.append("♥", style="#E9A5F1")
    prose.append(" by Path Integral Institute", style="#FED2E2")

    with temp_console.capture() as capture:
        temp_console.print(prose, justify="center")
    rendered_text = capture.get().rstrip()

    header_text.append(Text.from_ansi(rendered_text))
    return header_text


# Add subtle footer to all commands using Text object to avoid literal markup
global_footer_text = Text()
global_footer_text.append("💬 Report bugs or request features: ", style="#8B7DB8")
global_footer_text.append("https://github.com/pathintegral-institute/mcpm.sh/issues", style="#8B7DB8")

click.rich_click.FOOTER_TEXT = global_footer_text

# Enable custom formatting
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.SHOW_METAVARS_COLUMN = False
click.rich_click.APPEND_METAVARS_HELP = True
click.rich_click.SHOW_ARGUMENTS = True
# click.rich_click.SHOW_HELP_FOR_ORPHAN_COMMAND = False
# click.rich_click.GROUP_COMMANDS_BEFORE_USAGE = True

# Command groups for organized help
click.rich_click.COMMAND_GROUPS = {
    "main": [  # This matches the function name
        {
            "name": "Server Management",
            "commands": ["search", "info", "install", "uninstall", "ls", "edit", "inspect"],
        },
        {
            "name": "Server Execution",
            "commands": ["run", "share", "inspect", "usage"],
        },
        {
            "name": "Client",
            "commands": ["client"],
        },
        {
            "name": "Profile",
            "commands": ["profile"],
        },
        {
            "name": "System & Configuration",
            "commands": ["doctor", "config", "migrate"],
        },
    ],
    "mcpm": [  # Also support this context name
        {
            "name": "Server Management",
            "commands": ["search", "info", "install", "uninstall", "ls", "edit", "inspect"],
        },
        {
            "name": "Server Execution",
            "commands": ["run", "share", "inspect", "usage"],
        },
        {
            "name": "Client",
            "commands": ["client"],
        },
        {
            "name": "Profile",
            "commands": ["profile"],
        },
        {
            "name": "System & Configuration",
            "commands": ["doctor", "config", "migrate"],
        },
    ],
}

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
# click.rich_click.STYLE_METAVAR_BRACKET = "dim"
click.rich_click.STYLE_HELPTEXT = ""
click.rich_click.STYLE_HELPTEXT_FIRST_LINE = "bold"
click.rich_click.STYLE_OPTION_HELP = ""
click.rich_click.STYLE_USAGE = "bold"
click.rich_click.STYLE_USAGE_COMMAND = "bold cyan"

# Layout
# click.rich_click.ALIGN_ERRORS_LEFT = True
click.rich_click.WIDTH = None  # Use terminal width
click.rich_click.MAX_WIDTH = 100  # Maximum width for better readability

# Command groups for organized help

# Option groupings for subcommands
click.rich_click.OPTION_GROUPS = {
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
