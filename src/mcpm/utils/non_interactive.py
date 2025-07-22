"""
Non-interactive utility functions for AI agent friendly CLI operations.
"""

import os
import sys
from typing import Dict, List, Optional


def is_non_interactive() -> bool:
    """
    Check if running in non-interactive mode.

    Returns True if any of the following conditions are met:
    - MCPM_NON_INTERACTIVE environment variable is set to 'true'
    - Not connected to a TTY (stdin is not a terminal)
    - Running in a CI environment
    """
    # Check explicit non-interactive flag
    if os.getenv("MCPM_NON_INTERACTIVE", "").lower() == "true":
        return True

    # Check if not connected to a TTY
    if not sys.stdin.isatty():
        return True

    # Check for common CI environment variables
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS"]
    if any(os.getenv(var) for var in ci_vars):
        return True

    return False


def should_force_operation() -> bool:
    """
    Check if operations should be forced (skip confirmations).

    Returns True if MCPM_FORCE environment variable is set to 'true'.
    """
    return os.getenv("MCPM_FORCE", "").lower() == "true"


def should_output_json() -> bool:
    """
    Check if output should be in JSON format.

    Returns True if MCPM_JSON_OUTPUT environment variable is set to 'true'.
    """
    return os.getenv("MCPM_JSON_OUTPUT", "").lower() == "true"


def parse_key_value_pairs(pairs: str) -> Dict[str, str]:
    """
    Parse comma-separated key=value pairs.

    Args:
        pairs: String like "key1=value1,key2=value2"

    Returns:
        Dictionary of key-value pairs

    Raises:
        ValueError: If format is invalid
    """
    if not pairs or not pairs.strip():
        return {}

    result = {}
    for pair in pairs.split(","):
        pair = pair.strip()
        if not pair:
            continue

        if "=" not in pair:
            raise ValueError(f"Invalid key-value pair format: '{pair}'. Expected format: key=value")

        key, value = pair.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise ValueError(f"Empty key in pair: '{pair}'")

        result[key] = value

    return result


def parse_server_list(servers: str) -> List[str]:
    """
    Parse comma-separated server list.

    Args:
        servers: String like "server1,server2,server3"

    Returns:
        List of server names
    """
    if not servers or not servers.strip():
        return []

    return [server.strip() for server in servers.split(",") if server.strip()]


def parse_header_pairs(headers: str) -> Dict[str, str]:
    """
    Parse comma-separated header pairs.

    Args:
        headers: String like "Authorization=Bearer token,Content-Type=application/json"

    Returns:
        Dictionary of header key-value pairs

    Raises:
        ValueError: If format is invalid
    """
    return parse_key_value_pairs(headers)


def validate_server_type(server_type: str) -> str:
    """
    Validate server type parameter.

    Args:
        server_type: Server type string

    Returns:
        Validated server type

    Raises:
        ValueError: If server type is invalid
    """
    valid_types = ["stdio", "remote"]
    if server_type not in valid_types:
        raise ValueError(f"Invalid server type: '{server_type}'. Must be one of: {', '.join(valid_types)}")

    return server_type


def validate_required_for_type(server_type: str, **kwargs) -> None:
    """
    Validate required parameters for specific server types.

    Args:
        server_type: Server type ("stdio" or "remote")
        **kwargs: Parameters to validate

    Raises:
        ValueError: If required parameters are missing
    """
    if server_type == "stdio":
        if not kwargs.get("command"):
            raise ValueError("--command is required for stdio servers")
    elif server_type == "remote":
        if not kwargs.get("url"):
            raise ValueError("--url is required for remote servers")


def format_validation_error(param_name: str, value: str, error: str) -> str:
    """
    Format a parameter validation error message.

    Args:
        param_name: Parameter name
        value: Parameter value
        error: Error description

    Returns:
        Formatted error message
    """
    return f"Invalid value for {param_name}: '{value}'. {error}"


def get_env_var_for_server_arg(server_name: str, arg_name: str) -> Optional[str]:
    """
    Get environment variable value for a server argument.

    Args:
        server_name: Server name
        arg_name: Argument name

    Returns:
        Environment variable value or None
    """
    # Try server-specific env var first: MCPM_SERVER_{SERVER_NAME}_{ARG_NAME}
    server_env_var = f"MCPM_SERVER_{server_name.upper().replace('-', '_')}_{arg_name.upper().replace('-', '_')}"
    value = os.getenv(server_env_var)
    if value:
        return value

    # Try generic env var: MCPM_ARG_{ARG_NAME}
    generic_env_var = f"MCPM_ARG_{arg_name.upper().replace('-', '_')}"
    return os.getenv(generic_env_var)


def create_server_config_from_params(
    name: str,
    server_type: str,
    command: Optional[str] = None,
    args: Optional[str] = None,
    env: Optional[str] = None,
    url: Optional[str] = None,
    headers: Optional[str] = None,
) -> Dict:
    """
    Create a server configuration dictionary from CLI parameters.

    Args:
        name: Server name
        server_type: Server type ("stdio" or "remote")
        command: Command for stdio servers
        args: Command arguments
        env: Environment variables
        url: URL for remote servers
        headers: HTTP headers for remote servers

    Returns:
        Server configuration dictionary

    Raises:
        ValueError: If parameters are invalid
    """
    # Validate server type
    server_type = validate_server_type(server_type)

    # Validate required parameters
    validate_required_for_type(server_type, command=command, url=url)

    # Base configuration
    config = {
        "name": name,
        "type": server_type,
    }

    if server_type == "stdio":
        config["command"] = command
        if args:
            config["args"] = args.split()
        # Add environment variables if provided (stdio servers only)
        if env:
            config["env"] = parse_key_value_pairs(env)
    elif server_type == "remote":
        config["url"] = url
        if headers:
            config["headers"] = parse_header_pairs(headers)
        # Remote servers don't support environment variables
        if env:
            raise ValueError("Environment variables are not supported for remote servers")

    return config


def merge_server_config_updates(
    current_config: Dict,
    name: Optional[str] = None,
    command: Optional[str] = None,
    args: Optional[str] = None,
    env: Optional[str] = None,
    url: Optional[str] = None,
    headers: Optional[str] = None,
) -> Dict:
    """
    Merge server configuration updates with existing configuration.

    Args:
        current_config: Current server configuration
        name: New server name
        command: New command for stdio servers
        args: New command arguments
        env: New environment variables
        url: New URL for remote servers
        headers: New HTTP headers for remote servers

    Returns:
        Updated server configuration dictionary
    """
    updated_config = current_config.copy()

    # Update basic fields
    if name:
        updated_config["name"] = name
    if command:
        updated_config["command"] = command
    if args:
        updated_config["args"] = args.split()
    if url:
        updated_config["url"] = url

    # Update environment variables
    if env:
        new_env = parse_key_value_pairs(env)
        if "env" in updated_config:
            updated_config["env"].update(new_env)
        else:
            updated_config["env"] = new_env

    # Update headers
    if headers:
        new_headers = parse_header_pairs(headers)
        if "headers" in updated_config:
            updated_config["headers"].update(new_headers)
        else:
            updated_config["headers"] = new_headers

    return updated_config
