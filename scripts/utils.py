import re
from contextlib import AsyncExitStack
from datetime import timedelta
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from mcp.types import ListPromptsResult, ListResourcesResult, ListToolsResult


class McpClient:
    session: ClientSession

    def __init__(self):
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, cmd, args, env):
        command = cmd
        server_params = StdioServerParameters(command=command, args=args, env=env)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write, read_timeout_seconds=timedelta(seconds=60))
        )

        await self.session.initialize()

    async def list_tools(self):
        # List available tools
        try:
            tools_result = await self.session.list_tools()
            return tools_result
        except McpError:
            return ListToolsResult(tools=[])

    async def list_prompts(self):
        # List available prompts
        try:
            prompts_result = await self.session.list_prompts()
            return prompts_result
        except McpError:
            return ListPromptsResult(prompts=[])

    async def list_resources(self):
        # List available resources
        try:
            resources_result = await self.session.list_resources()
            return resources_result
        except McpError:
            return ListResourcesResult(resources=[])

    async def close(self):
        await self.exit_stack.aclose()


def validate_arguments_in_installation(
    installation: dict[str, Any], arguments: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Post process arguments in llm-generated installation to unify the format for later usage
    Standardizes variable placeholders to use the ${KEY} format:

    1. For Docker commands:
       - Only processes KEY=value formats after -e/--env flags
       - "-e KEY=value" -> "-e KEY=${KEY}"

    2. For other commands:
       - "--KEY=value" -> "--KEY=${KEY}"
       - "--KEY value" -> "--KEY ${KEY}"

    3. For env dictionary:
       - All values are converted to ${KEY} format

    Args:
        installation: A dictionary containing installation configuration
        arguments: A dictionary of arguments to validate

    Returns:
        Updated installation dictionary with standardized variable formats
    """
    if not installation or "args" not in installation or not installation["args"]:
        return installation, False

    args = installation["args"].copy()
    is_docker = installation.get("command", "").lower() == "docker"
    replacement = False

    i = 0
    while i < len(args):
        prev_arg = args[i - 1] if i > 0 else ""
        arg = args[i]

        # Skip if not string arguments
        if not isinstance(arg, str):
            i += 1
            continue

        # Case 1: Docker command with -e/--env flags
        if is_docker and (prev_arg == "-e" or prev_arg == "--env"):
            # Process KEY=value format
            env_key_match = re.match(r"^([A-Za-z_-]+)=(.+)$", arg)
            if env_key_match:
                key = env_key_match.group(1)
                if key in arguments:  # assert key is in arguments
                    args[i] = f"{key}=${{{key}}}"  # KEY=${KEY}
                    replacement = True

            i += 1
            continue

        # Case 2: Other commands or Docker args not following env flags
        if not is_docker:
            # Case 2.1: (--)KEY=value format
            if "=" in arg:
                key_value_match = re.match(r"^(-{0,2})([A-Za-z_-]+)=(.+)$", arg)
                if key_value_match:
                    prefix = key_value_match.group(1)
                    key = key_value_match.group(2)
                    if key in arguments:  # assert key is in arguments
                        args[i] = f"{prefix}{key}=${{{key}}}"  # KEY=${KEY}
                        replacement = True

            # Case 2.2: --KEY value format
            if prev_arg.startswith("-") or prev_arg.startswith("--"):
                arg_key = prev_arg.lstrip("-")
                if arg_key in arguments:
                    args[i] = f"${{{arg_key}}}"  # ${KEY}
                    replacement = True

            i += 1
            continue

        i += 1

    installation["args"] = args

    # handle env
    if "env" in installation and installation["env"]:
        env = {}
        for key, value in installation["env"].items():
            if key in arguments:
                env[key] = f"${{{key}}}"  # {"KEY": "${KEY}"}
                replacement = True
            else:
                env[key] = value

        installation["env"] = env

    return installation, replacement
