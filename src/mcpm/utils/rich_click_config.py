"""
Rich-click configuration for MCPM CLI.
"""

import rich_click as click
from rich.text import Text
from rich_gradient import Gradient
from rich.align import Align
from rich.panel import Panel
from rich import box

# Configure rich-click globally for beautiful CLI formatting
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.SHOW_METAVARS_COLUMN = False
click.rich_click.APPEND_METAVARS_HELP = True

# Get version dynamically
from mcpm import __version__

# ASCII art logo - simplified with light shades
ASCII_ART = """
 ███░   ███░  ██████░ ██████░ ███░   ███░
 ████░ ████░ ██░░░░░░ ██░░░██░████░ ████░
 ██░████░██░ ██░      ██████░░██░████░██░
 ██░░██░░██░ ██░      ██░░░░░ ██░░██░░██░
 ██░ ░░░ ██░ ░██████░ ██░     ██░ ░░░ ██░
 ░░░     ░░░  ░░░░░░░ ░░░     ░░░     ░░░

"""

# Create an elegant logo with ocean-to-sunset gradient using rich.text.Text
header_text = Text()

# Create gradient ASCII art using rich-gradient with purple-to-pink colors
gradient_colors = ["#8F87F1", "#C68EFD", "#E9A5F1", "#FED2E2"]

# Create a console with narrower width to force gradient calculation over ASCII width
from rich.console import Console
temp_console = Console(width=50)  # Close to ASCII art width

# Create gradient and render it with the narrow console
ascii_gradient = Gradient(ASCII_ART, colors=gradient_colors)

# Capture the rendered gradient
with temp_console.capture() as capture:
    temp_console.print(ascii_gradient, justify="center")
rendered_ascii = capture.get()

# Add to header text
header_text = Text.from_ansi(rendered_ascii)

header_text.append("\n")

# Add solid color text for title and tagline - harmonized with gradient
header_text.append("Model Context Protocol Manager", style="#8F87F1 bold")
header_text.append(" v", style="#C68EFD")
header_text.append(__version__, style="#E9A5F1 bold")
header_text.append("\n")
header_text.append("Open Source with ", style="#FED2E2")
header_text.append("♥", style="#E9A5F1")
header_text.append(" by Path Integral Institute", style="#FED2E2")

footer_text = Text()
footer_text.append("\n")
footer_text.append("◈ Feedback and Support:", style="#8F87F1 bold")
footer_text.append("\n  ")
footer_text.append("🐛 Report a bug:", style="#C68EFD bold")
footer_text.append(" https://github.com/pathintegral-institute/mcpm.sh/issues", style="#E9A5F1")
footer_text.append("\n  ")
footer_text.append("💬 Join discussion:", style="#E9A5F1 bold")
footer_text.append(" https://github.com/pathintegral-institute/mcpm.sh/discussions", style="#FED2E2")

click.rich_click.HEADER_TEXT = header_text
click.rich_click.FOOTER_TEXT = footer_text

# Enable custom formatting 
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
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

# Command groups for organized help
# Rich-click uses the context name, which can vary
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
    ]
}

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
