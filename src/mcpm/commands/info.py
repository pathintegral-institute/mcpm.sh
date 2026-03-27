"""
Info command for MCPM - Show detailed information about a specific MCP server
"""

from rich.console import Console
from rich.markup import escape

from mcpm.utils.display import print_error
from mcpm.utils.repository import RepositoryManager
from mcpm.utils.rich_click_config import click

console = Console()
repo_manager = RepositoryManager()


@click.command()
@click.argument("server_name", required=True)
@click.help_option("-h", "--help")
def info(server_name):
    """Display detailed information about a specific MCP server.

    Provides comprehensive details about a single MCP server, including installation instructions,
    dependencies, environment variables, and examples.

    Examples:

    \b
        mcpm info github            # Show details for the GitHub server
        mcpm info pinecone          # Show details for the Pinecone server
    """
    console.print(f"[bold green]Showing information for MCP server:[/] [bold cyan]{escape(server_name)}[/]")

    try:
        # Get the server information
        server = repo_manager.get_server_metadata(server_name)

        if not server:
            console.print(f"[yellow]Server '[bold]{escape(server_name)}[/]' not found.[/]")
            return

        # Display detailed information for this server
        _display_server_info(server)

    except Exception as e:
        print_error(f"Error retrieving information for server '{server_name}'", str(e))


def _display_server_info(server):
    """Display detailed information about a server"""
    # Get server data
    name = server["name"]
    display_name = server.get("display_name", name)
    description = server.get("description", "No description")
    license_info = server.get("license", "Unknown")
    is_official = server.get("is_official", False)
    is_archived = server.get("is_archived", False)

    # Get author info
    author_info = server.get("author", {})
    author_name = author_info.get("name", "Unknown")
    author_email = author_info.get("email", "")
    author_url = author_info.get("url", "")

    # Build categories and tags
    categories = server.get("categories", [])
    tags = server.get("tags", [])

    # Get installation details
    installations = server.get("installations", {})
    installation = server.get("installation", {})
    package = installation.get("package", "")

    # Print server header
    console.print(f"[bold cyan]{escape(display_name)}[/] [dim]({escape(name)})[/]")
    console.print(f"[italic]{escape(description)}[/]\n")

    # Server information section
    console.print("[bold yellow]Server Information:[/]")
    if categories:
        console.print(f"Categories: {', '.join(escape(str(c)) for c in categories)}")
    if tags:
        console.print(f"Tags: {', '.join(escape(str(t)) for t in tags)}")
    if package:
        console.print(f"Package: {escape(package)}")
    email_part = f" ({escape(author_email)})" if author_email else ""
    console.print(f"Author: {escape(author_name)}{email_part}")
    console.print(f"License: {escape(str(license_info))}")
    console.print(f"Official: {is_official}")
    if is_archived:
        console.print(f"Archived: {is_archived}")
    console.print("")

    # URLs section
    console.print("[bold yellow]URLs:[/]")

    # Repository URL
    if "repository" in server and "url" in server["repository"]:
        repo_url = server["repository"]["url"]
        console.print(f"Repository: [blue underline]{escape(repo_url)}[/]")

    # Homepage URL
    if "homepage" in server:
        homepage_url = server["homepage"]
        console.print(f"Homepage: [blue underline]{escape(homepage_url)}[/]")

    # Documentation URL
    if "documentation" in server:
        doc_url = server["documentation"]
        console.print(f"Documentation: [blue underline]{escape(doc_url)}[/]")

    # Author URL
    if author_url:
        console.print(f"Author URL: [blue underline]{escape(author_url)}[/]")

    console.print("")

    # Installation details section
    if installations:
        console.print("[bold yellow]Installation Details:[/]")
        for method_name, method in installations.items():
            method_type = method.get("type", "unknown")
            description = method.get("description", f"{method_type} installation")
            recommended = " [green](recommended)[/]" if method.get("recommended", False) else ""

            console.print(f"[cyan]{escape(method_type)}[/]: {escape(description)}{recommended}")

            # Show command if available
            if "command" in method:
                cmd = method["command"]
                args = method.get("args", [])
                cmd_str = f"{cmd} {' '.join(args)}" if args else cmd
                console.print(f"Command: [green]{escape(cmd_str)}[/]")

            # Show URL for http installations
            if method_type == "http" and "url" in method:
                console.print(f"URL: [green]{escape(method['url'])}[/]")

            # Show dependencies if available
            dependencies = method.get("dependencies", [])
            if dependencies:
                console.print(f"Dependencies: {', '.join(escape(str(d)) for d in dependencies)}")

            # Show environment variables if available
            env_vars = method.get("env", {})
            if env_vars:
                console.print("Environment Variables:")
                for key, value in env_vars.items():
                    console.print(f'  [bold blue]{escape(str(key))}[/] = [green]"{escape(str(value))}"[/]')
            console.print("")

    # Examples section
    examples = server.get("examples", [])
    if examples:
        console.print("[bold yellow]Examples:[/]")
        for i, example in enumerate(examples):
            if "title" in example:
                console.print(f"[bold]{i + 1}. {escape(str(example['title']))}[/]")
            if "description" in example:
                console.print(f"   {escape(str(example['description']))}")
            if "code" in example:
                console.print(f"   Code: [green]{escape(str(example['code']))}[/]")
            if "prompt" in example:
                console.print(f"   Prompt: [green]{escape(str(example['prompt']))}[/]")
            console.print("")
