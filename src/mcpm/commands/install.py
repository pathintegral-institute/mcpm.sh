"""
Install command for adding MCP servers to the global configuration
"""

import json
import os
import re
from enum import Enum

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from mcpm.core.schema import ServerConfig, STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.schemas.full_server_config import FullServerConfig
from mcpm.utils.config import NODE_EXECUTABLES, ConfigManager
from mcpm.utils.repository import RepositoryManager
from mcpm.utils.rich_click_config import click

console = Console()
repo_manager = RepositoryManager()
profile_config_manager = ProfileConfigManager()
global_config_manager = GlobalConfigManager()

# Create a prompt session with custom styling
prompt_session = PromptSession()
style = Style.from_dict(
    {
        "prompt": "ansicyan bold",
        "default": "ansiyellow",
        "description": "ansiwhite",
        "required": "ansired",
        "optional": "ansigreen",
    }
)

# Create key bindings
kb = KeyBindings()


def _replace_node_executable(server_config: ServerConfig) -> ServerConfig:
    """Replace node executable with configured alternative if applicable."""
    if not isinstance(server_config, STDIOServerConfig):
        return server_config
    command = server_config.command.strip()
    if command not in NODE_EXECUTABLES:
        return server_config
    config = ConfigManager().get_config()
    config_node_executable = config.get("node_executable")
    if not config_node_executable:
        return server_config
    if config_node_executable != command:
        console.print(f"[bold cyan]Replace node executable {command} with {config_node_executable}[/]")
        server_config.command = config_node_executable
    return server_config


def global_add_server(server_config: ServerConfig, force: bool = False) -> bool:
    """Add a server to the global MCPM configuration."""
    if global_config_manager.server_exists(server_config.name) and not force:
        console.print(f"[bold red]Error:[/] Server '{server_config.name}' already exists in global configuration.")
        console.print("Use --force to override.")
        return False

    server_config = _replace_node_executable(server_config)
    return global_config_manager.add_server(server_config, force)


def prompt_with_default(prompt_text, default="", hide_input=False, required=False):
    """Prompt the user with a default value that can be edited directly.

    Args:
        prompt_text: The prompt text to display
        default: The default value to show in the prompt
        hide_input: Whether to hide the input (for passwords)
        required: Whether this is a required field

    Returns:
        The user's input or the default value if empty
    """
    # if default:
    #     console.print(f"Default: [yellow]{default}[/]")

    # Get user input
    try:
        result = prompt_session.prompt(
            message=HTML(f"<prompt>{prompt_text}</prompt> > "),
            style=style,
            default=default,
            is_password=hide_input,
            key_bindings=kb,
        )

        # Empty result for non-required field means leave it empty
        if not result.strip() and not required:
            return ""

        # Empty result for required field with default should use default
        if not result.strip() and required and default:
            return default

        # Empty result for required field without default is not allowed
        if not result.strip() and required and not default:
            console.print("[yellow]Warning: Required value cannot be empty.[/]")
            return prompt_with_default(prompt_text, default, hide_input, required)

        return result
    except KeyboardInterrupt:
        raise click.Abort()


@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force reinstall if server is already installed")
@click.option("--alias", help="Alias for the server", required=False)
@click.help_option("-h", "--help")
def install(server_name, force=False, alias=None):
    """Install an MCP server to the global configuration.

    Installs servers to the global MCPM configuration where they can be
    used across all MCP clients and organized into profiles.

    Examples:

    \b
        mcpm install time
        mcpm install everything --force
        mcpm install youtube --alias yt
    """

    config_name = alias or server_name

    # All servers are installed to global configuration
    console.print("[yellow]Installing server to global configuration...[/]")

    # Get server metadata from repository
    server_metadata = repo_manager.get_server_metadata(server_name)
    if not server_metadata:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in registry.")
        console.print(f"Available servers: {', '.join(repo_manager._fetch_servers().keys())}")
        return

    # Display server information
    display_name = server_metadata.get("display_name", server_name)
    description = server_metadata.get("description", "No description available")
    author_info = server_metadata.get("author", {})

    console.print(f"\n[bold]{display_name}[/] ({server_name})")
    console.print(f"[dim]{description}[/]")

    if author_info:
        author_name = author_info.get("name", "Unknown")
        author_url = author_info.get("url", "")
        console.print(f"[dim]Author: {author_name} {author_url}[/]")

    # Confirm addition
    alias_text = f" as '{alias}'" if alias else ""
    if not force and not Confirm.ask(f"Install this server to global configuration{alias_text}?"):
        console.print("[yellow]Operation cancelled.[/]")
        return

    # Create server directory in the MCP directory
    base_dir = os.path.expanduser("~/.mcpm")
    os.makedirs(base_dir, exist_ok=True)

    servers_dir = os.path.join(base_dir, "servers")
    os.makedirs(servers_dir, exist_ok=True)

    server_dir = os.path.join(servers_dir, server_name)
    os.makedirs(server_dir, exist_ok=True)

    # Extract installation information
    installations = server_metadata.get("installations", {})

    # If no installation information is available, create minimal default values
    # This allows us to add the server config without full installation details
    installation_method = "manual"  # Single consolidated concept
    install_command = "echo"
    install_args = [f"Server {server_name} added to configuration"]
    package_name = None
    env_vars = {}
    required_args = {}

    # Process installation information if available
    selected_method = None  # Initialize selected_method to None to avoid UnboundLocalError
    if installations:
        # Find recommended installation method or default to the first one
        method_id = "default"  # ID of the method in the config

        # First check for a recommended method
        for key, method in installations.items():
            if method.get("recommended", False):
                selected_method = method
                method_id = key
                break

        # If no recommended method found, use the first one
        if not selected_method and installations:
            method_id = next(iter(installations))
            selected_method = installations[method_id]

        # If multiple methods are available and not forced, offer selection
        if len(installations) > 1 and not force:
            console.print("\n[bold]Available installation methods:[/]")
            methods_list = []

            for i, (key, method) in enumerate(installations.items(), 1):
                method_type = method.get("type", "unknown")
                description = method.get("description", f"{method_type} installation")
                recommended = " [green](recommended)[/]" if method.get("recommended", False) else ""

                console.print(f"  {i}. [cyan]{key}[/]: {description}{recommended}")
                methods_list.append(key)

            # Ask user to select a method
            try:
                selection = click.prompt(
                    "\nSelect installation method", type=int, default=methods_list.index(method_id) + 1
                )
                if 1 <= selection <= len(methods_list):
                    method_id = methods_list[selection - 1]
                    selected_method = installations[method_id]
            except (ValueError, click.Abort):
                console.print("[yellow]Using default installation method.[/]")

        # Extract installation details
        if selected_method:
            # Use the method's type as the installation method if available, otherwise use the key
            installation_method = selected_method.get("type")
            if not installation_method or installation_method == "unknown":
                installation_method = method_id

            install_command = selected_method.get("command", install_command)
            install_args = selected_method.get("args", install_args)
            package_name = selected_method.get("package", package_name)
            env_vars = selected_method.get("env", env_vars)

        console.print(f"\n[green]Using [bold]{installation_method}[/] installation method[/]")

    # Configure the server
    with Progress(SpinnerColumn(), TextColumn("[bold green]{task.description}[/]"), console=console) as progress:
        # Save metadata to server directory
        progress.add_task("Saving server metadata...", total=None)
        metadata_path = os.path.join(server_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(server_metadata, f, indent=2)

        # Configure the server
        progress.add_task(f"Configuring {server_name}...", total=None)

        # Get all available arguments from the server metadata
        all_arguments = server_metadata.get("arguments", {})

        required_args = {}
        # Process variables to store in config
        processed_variables = {}

        # Extract which arguments are actually referenced in the selected installation method
        referenced_vars = _extract_referenced_variables(selected_method) if selected_method else set()

        # Filter arguments to only those that are referenced
        relevant_arguments = {}
        if all_arguments:
            if referenced_vars:
                # Only include arguments that are referenced
                for arg_name, arg_info in all_arguments.items():
                    if arg_name in referenced_vars:
                        relevant_arguments[arg_name] = arg_info
            elif selected_method:
                # If we have a selected method but no referenced vars, don't prompt for any
                relevant_arguments = {}
            else:
                # No selected method - use all arguments (backward compatibility)
                relevant_arguments = all_arguments

        # First, prompt for relevant arguments
        progress.stop()
        if relevant_arguments:
            console.print("\n[bold]Configure server arguments:[/]")

            for arg_name, arg_info in relevant_arguments.items():
                description = arg_info.get("description", "")
                is_required = arg_info.get("required", False)
                example = arg_info.get("example", "")

                # Add required indicator
                if is_required:
                    required_args[arg_name] = arg_info
                    required_html = "<ansired>(required)</ansired>"
                else:
                    required_html = "<ansigreen>(optional)</ansigreen>"

                # Build clean prompt text for console display and prompt
                html_prompt_text = f"{arg_name} {required_html}"

                # Check if the argument is already set in environment
                env_value = os.environ.get(arg_name, "")

                # Print description if available
                if description:
                    console.print(f"[dim]{description}[/]")

                if env_value:
                    # Show the existing value as default
                    console.print(f"[green]Found in environment: {env_value}[/]")
                    try:
                        user_value = prompt_with_default(
                            html_prompt_text,
                            default=env_value,
                            hide_input=_should_hide_input(arg_name),
                            required=is_required,
                        )
                        if user_value != env_value:
                            # User provided a different value
                            processed_variables[arg_name] = user_value
                        else:
                            # User use environment value
                            processed_variables[arg_name] = env_value
                    except click.Abort:
                        pass
                else:
                    # No environment value
                    try:
                        user_value = prompt_with_default(
                            html_prompt_text,
                            default=example if example else "",
                            hide_input=_should_hide_input(arg_name),
                            required=is_required,
                        )

                        # Only add non-empty values to the environment
                        if user_value and user_value.strip():
                            processed_variables[arg_name] = user_value
                        # Explicitly don't add anything if the user leaves it blank
                    except click.Abort:
                        if is_required:
                            console.print(f"[yellow]Warning: Required argument {arg_name} not provided.[/]")

            # Resume progress display
            progress = Progress(SpinnerColumn(), TextColumn("[bold green]{task.description}[/]"), console=console)
            progress.start()
            progress.add_task(f"Configuring {server_name}...", total=None)

    # replace arguments with values
    processed_args = []
    has_non_standard_argument_define = False
    for i, arg in enumerate(install_args):
        prev_arg = install_args[i - 1] if i > 0 else ""
        # handles arguments with pattern var=${var} | --var=var | --var var
        arg_replaced, replacement_status = _replace_argument_variables(arg, prev_arg, processed_variables)
        processed_args.append(arg_replaced)
        if replacement_status == ReplacementStatus.NON_STANDARD_REPLACE:
            has_non_standard_argument_define = True

    # process environment variables
    processed_env = {}
    for key, value in env_vars.items():
        # just replace the env value regardless of the variable pattern, ${VAR}/YOUR_VAR/VAR
        env_replaced, replacement_status = _replace_variables(value, processed_variables)
        processed_env[key] = env_replaced if env_replaced else processed_variables.get(key, value)
        if key in processed_variables and replacement_status == ReplacementStatus.NON_STANDARD_REPLACE:
            has_non_standard_argument_define = True

    # For HTTP servers, headers should be extracted from the installation method
    # not from processed variables
    processed_headers = {}
    if installation_method == "http" and selected_method:
        # Extract headers from the installation method if defined
        headers_template = selected_method.get("headers", {})
        for key, value in headers_template.items():
            # Replace variables in header values
            header_replaced, _ = _replace_variables(value, processed_variables)
            if header_replaced:
                processed_headers[key] = header_replaced
            else:
                # If no replacement, use the original value
                processed_headers[key] = value

    if has_non_standard_argument_define:
        # no matter in argument / env
        console.print(
            "[bold yellow]WARNING:[/] [bold]Non-standard argument format detected in server configuration.[/]\n"
            "[bold cyan]Future versions of MCPM will standardize all arguments in server configuration to use ${VARIABLE_NAME} format.[/]\n"
            "[bold]Please verify that your input arguments are correctly recognized.[/]\n"
        )

    # Get actual MCP execution command, args, and env from the selected installation method
    # This ensures we use the actual server command information instead of placeholders
    mcp_url = None
    mcp_command = None
    mcp_args = []

    if selected_method:
        # For HTTP servers, extract the URL and don't set command/args
        if installation_method == "http":
            mcp_url = selected_method.get("url")
            # HTTP servers don't have command/args
        else:
            # For non-HTTP servers, get command and args
            mcp_command = selected_method.get("command", install_command)
            mcp_args = processed_args
        # Env vars are already processed above
    else:
        # Fallback for when no selected method
        mcp_command = install_command
        mcp_args = processed_args

    # Create server configuration using FullServerConfig
    full_server_config = FullServerConfig(
        name=config_name,
        display_name=display_name,
        description=description,
        command=mcp_command,  # Use the actual MCP server command
        args=mcp_args,  # Use the actual MCP server arguments
        env=processed_env,
        # Use the simplified installation method
        installation=installation_method,
        url=mcp_url,  # Include URL for HTTP servers
        headers=processed_headers,  # Include headers for HTTP servers
    )

    # Add server to global configuration
    success = global_add_server(full_server_config.to_server_config(), force)

    if success:
        # Server has been successfully added to the global configuration
        console.print(f"[bold green]Successfully installed {display_name} to global configuration![/]")

        # Display usage examples if available
        examples = server_metadata.get("examples", [])
        if examples:
            console.print("\n[bold]Usage Examples:[/]")
            for i, example in enumerate(examples, 1):
                title = example.get("title", f"Example {i}")
                description = example.get("description", "")
                prompt = example.get("prompt", "")

                console.print(f"  [cyan]{title}[/]: {description}")
                if prompt:
                    console.print(f'  Try: [italic]"{prompt}"[/]\n')
    else:
        console.print(f"[bold red]Failed to install {server_name} to global configuration.[/]")


def _should_hide_input(arg_name: str) -> bool:
    """Determine if input should be hidden for a given argument name.

    Args:
        arg_name: The name of the argument to check

    Returns:
        bool: True if input should be hidden, False otherwise
    """
    return "token" in arg_name.lower() or "key" in arg_name.lower() or "secret" in arg_name.lower()


def _extract_referenced_variables(installation_method: dict) -> set:
    """Extract all variable names referenced in an installation method.

    Scans through all fields in the installation method (command, args, env, url, etc.)
    looking for ${VARIABLE_NAME} patterns.

    Args:
        installation_method: The installation method configuration dict

    Returns:
        Set of variable names that are referenced
    """
    referenced = set()

    def extract_from_value(value):
        """Recursively extract variables from a value."""
        if isinstance(value, str):
            # Find all ${VAR_NAME} patterns
            matches = re.findall(r"\$\{([^}]+)\}", value)
            referenced.update(matches)
        elif isinstance(value, list):
            for item in value:
                extract_from_value(item)
        elif isinstance(value, dict):
            for v in value.values():
                extract_from_value(v)

    # Check all fields in the installation method
    for key, value in installation_method.items():
        if key not in ["type", "description", "recommended"]:  # Skip metadata fields
            extract_from_value(value)

    return referenced


class ReplacementStatus(str, Enum):
    NOT_REPLACED = "not_replaced"
    STANDARD_REPLACE = "standard_replace"
    NON_STANDARD_REPLACE = "non_standard_replace"


def _replace_variables(value: str, variables: dict) -> tuple[str, ReplacementStatus]:
    """Replace ${VAR} patterns in a string with values from variables dict.

    Args:
        value: String that may contain ${VAR} patterns
        variables: Dictionary of variable names to values

    Returns:
        String with all variables replaced (empty string for missing variables)
    """
    if not isinstance(value, str):
        return value, ReplacementStatus.NOT_REPLACED

    # check if the value contains a variable
    matched = re.search(r"\$\{([^}]+)\}", value)
    if matched:
        original, var_name = matched.group(0), matched.group(1)
        if var_name in variables:
            return value.replace(original, variables[var_name]), ReplacementStatus.STANDARD_REPLACE

    return "", ReplacementStatus.NON_STANDARD_REPLACE


def _replace_argument_variables(value: str, prev_value: str, variables: dict) -> tuple[str, ReplacementStatus]:
    """Replace variables in command-line arguments with values from variables dictionary.

    Handles four argument formats:
    1. Variable substitution: argument=${VAR_NAME}
    2. Key-value pair: --argument=value
    3. Space-separated pair: --argument value (where prev_value represents --argument)

    Args:
        value: The current argument string that may contain variables
        prev_value: The previous argument string (for space-separated pairs)
        variables: Dictionary mapping variable names to their values

    Returns:
        Tuple[str, bool]:
            String with all variables replaced with their values from the variables dict
            bool: whether the argument formatted as standard format in the ${} pattern

    """
    if not isinstance(value, str):
        return value, ReplacementStatus.NOT_REPLACED

    # arg: VAR=${VAR}
    # check if the value contains a variable
    matched = re.search(r"\$\{([^}]+)\}", value)
    if matched:
        original, var_name = matched.group(0), matched.group(1)
        # Use empty string as default when key not found
        return value.replace(original, variables.get(var_name, "")), ReplacementStatus.STANDARD_REPLACE

    # arg: --VAR=your var value
    key_value_match = re.match(r"^([A-Z_]+)=(.+)$", value)
    if key_value_match:
        arg_key = key_value_match.group(1)
        if arg_key in variables:
            # replace the arg_value with variables[arg_key]
            return f"{arg_key}={variables[arg_key]}", ReplacementStatus.NON_STANDARD_REPLACE
        # if not contains the arg_key then just return the original value
        return value, ReplacementStatus.NOT_REPLACED

    # arg: --VAR your_var_value
    if prev_value.startswith("--") or prev_value.startswith("-"):
        arg_key = prev_value.lstrip("-")
        if arg_key in variables:
            # replace the value with variables[arg_key]
            return variables[arg_key], ReplacementStatus.NON_STANDARD_REPLACE
        # if not contains the arg_key then just return the original value
        return value, ReplacementStatus.NOT_REPLACED

    # nothing to replace
    return value, ReplacementStatus.NOT_REPLACED
