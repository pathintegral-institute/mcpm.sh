
<b>Pattern 1: When implementing command-line interfaces with Click, use consistent help option patterns and provide clear, structured help text with examples. Include both short (-h) and long (--help) options, and format examples using backslash-escaped blocks for proper display.
</b>

Example code before:
```
@click.command()
def my_command():
    """Command description."""
    pass
```

Example code after:
```
@click.command()
@click.help_option("-h", "--help")
def my_command():
    """Command description.
    
    Example:
    
    \b
        mcpm command example
    """
    pass
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/pathintegral-institute/mcpm.sh/pull/46#discussion_r2038909708
- https://github.com/pathintegral-institute/mcpm.sh/pull/119#discussion_r2059566646
</details>


___

<b>Pattern 2: When handling subprocess output streams, prefer reading from stderr for application logs and status information rather than stdout, as many applications follow the convention of writing logs to stderr while reserving stdout for data output.
</b>

Example code before:
```
# Process both stdout and stderr
if process.stdout:
    line = process.stdout.readline()
if process.stderr:
    line = process.stderr.readline()
```

Example code after:
```
# Focus on stderr for logs and status
if process.stderr:
    line = process.stderr.readline()
    if line:
        console.print(line.rstrip())
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/pathintegral-institute/mcpm.sh/pull/167#discussion_r2128177278
</details>


___

<b>Pattern 3: When implementing async handlers for web frameworks like Starlette, ensure handlers return proper Response objects and handle exceptions appropriately with try-catch blocks and proper cleanup in finally blocks.
</b>

Example code before:
```
async def handle_request(request: Request) -> None:
    async with some_context() as context:
        await process_request(context)
```

Example code after:
```
async def handle_request(request: Request) -> Response:
    try:
        async with some_context() as context:
            await process_request(context)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        return Response()
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/pathintegral-institute/mcpm.sh/pull/156#discussion_r2111437707
</details>


___

<b>Pattern 4: When managing server configurations and capabilities across multiple servers, implement proper conflict resolution strategies for duplicate names by either using strict mode to raise errors or auto-resolving conflicts with server-specific prefixes.
</b>

Example code before:
```
# Direct assignment without conflict checking
self.tools_mapping[tool.name] = tool
```

Example code after:
```
tool_name = tool.name
if tool_name in self.capabilities_to_server_id["tools"]:
    if self.strict:
        raise ValueError(f"Tool {tool_name} already exists")
    else:
        tool_name = f"{server_id}{SEPARATOR}{tool_name}"
self.tools_mapping[tool_name] = tool
self.capabilities_to_server_id["tools"][tool_name] = server_id
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/pathintegral-institute/mcpm.sh/pull/76#discussion_r2050413886
- https://github.com/pathintegral-institute/mcpm.sh/pull/76#discussion_r2050414500
</details>


___
