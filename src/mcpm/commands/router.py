"""
Router command for managing the MCPRouter daemon process
"""

import logging
import os
import secrets
import signal
import socket
import subprocess
import sys

import click
import psutil
from rich.console import Console
from rich.prompt import Confirm

from mcpm.clients.client_registry import ClientRegistry
from mcpm.core.utils.log_manager import get_log_directory
from mcpm.router.share import Tunnel
from mcpm.utils.config import MCPM_AUTH_HEADER, MCPM_PROFILE_HEADER, ConfigManager
from mcpm.utils.platform import get_pid_directory

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
console = Console()

APP_SUPPORT_DIR = get_pid_directory("mcpm")
APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE = APP_SUPPORT_DIR / "router.pid"
SHARE_CONFIG = APP_SUPPORT_DIR / "share.json"

LOG_DIR = get_log_directory("mcpm")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def is_process_running(pid):
    """check if the process is running"""
    try:
        return psutil.pid_exists(pid)
    except Exception:
        return False


def is_port_listening(host, port) -> bool:
    """
    Check if the specified (host, port) is being listened on.

    Args:
        host: The host to check
        port: The port to check

    Returns:
        True if the (host, port) is being listened on
    """
    sock = None
    try:
        # Try to connect to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        connected_host = "127.0.0.1" if host == "0.0.0.0" else host
        result = sock.connect_ex((connected_host, port))
        # result == 0 means connection successful, which means port is in use
        # result != 0 means connection failed, which means port is not in use
        # result == 61 means ECONNREFUSED
        return result == 0
    except Exception as e:
        logger.error(f"Error checking host {host} and port {port}: {e}")
        return False
    finally:
        if sock:
            sock.close()


def read_pid_file():
    """read the pid file and return the process id, if the file does not exist or the process is not running, return None"""
    if not PID_FILE.exists():
        return None

    try:
        pid = int(PID_FILE.read_text().strip())
        if is_process_running(pid):
            return pid
        else:
            # if the process is not running, delete the pid file
            remove_pid_file()
            return None
    except (ValueError, IOError) as e:
        logger.error(f"Error reading PID file: {e}")
        return None


def write_pid_file(pid):
    """write the process id to the pid file"""
    try:
        PID_FILE.write_text(str(pid))
        logger.debug(f"PID {pid} written to {PID_FILE}")
    except IOError as e:
        logger.error(f"Error writing PID file: {e}")
        sys.exit(1)


def remove_pid_file():
    """remove the pid file"""
    try:
        PID_FILE.unlink(missing_ok=True)
    except IOError as e:
        logger.error(f"Error removing PID file: {e}")


@click.group(name="router")
@click.help_option("-h", "--help")
def router():
    """Manage MCP router service."""
    pass


@router.command(name="on")
@click.help_option("-h", "--help")
@click.option("--sse", "-s", is_flag=True, help="Use SSE endpoint(deprecated)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def start_router(sse, verbose):
    """Start MCPRouter as a daemon process.

    Example:

    \b
        mcpm router on
    """
    # check if there is a router already running
    existing_pid = read_pid_file()
    if existing_pid:
        console.print(f"[bold red]Error:[/] MCPRouter is already running (PID: {existing_pid})")
        console.print("Use 'mcpm router off' to stop the running instance.")
        return

    # get router config
    config_manager = ConfigManager()
    config = config_manager.get_router_config()
    host = config["host"]
    port = config["port"]
    auth_enabled = config.get("auth_enabled", False)
    api_key = config.get("api_key")

    if sse:
        app_path = "mcpm.router.sse_app:app"
    else:
        app_path = "mcpm.router.app:app"

    # prepare uvicorn command
    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        app_path,
        "--host",
        host,
        "--port",
        str(port),
        "--timeout-graceful-shutdown",
        "5",
    ]

    # start process
    try:
        # create log file
        log_file = LOG_DIR / "router_access.log"

        # open log file, prepare to redirect stdout and stderr
        with open(log_file, "a") as log:
            # use subprocess.Popen to start uvicorn
            start = log.tell()
            process = subprocess.Popen(
                uvicorn_cmd,
                stdout=log,
                stderr=log,
                env=os.environ.copy(),
                start_new_session=True,  # create new session, so the process won't be affected by terminal closing
            )
        if verbose:
            console.rule("verbose log start")
            with open(log_file, "r") as log:
                # print log before startup complete
                log.seek(start)
                while True:
                    line = log.readline()
                    if not line:
                        continue
                    console.print(line.strip())
                    if "Application startup complete." in line:
                        break
            console.rule("verbose log end")

        # record PID
        pid = process.pid
        write_pid_file(pid)

        # Display router started information
        console.print(f"[bold green]MCPRouter started[/] at http://{host}:{port} (PID: {pid})")
        console.print(f"Log file: {log_file}")

        # Display connection instructions
        console.print("\n[bold cyan]Connection Information:[/]")

        api_key = api_key if auth_enabled else None

        if sse:
            console.print("\n[bold yellow]SSE router is not recommended[/]")
            console.print(f"Remote Server URL: [green]http://{host}:{port}/sse[/]")
            if api_key:
                console.print("\n[bold cyan]To use a specific profile with authentication:[/]")
                console.print(
                    f"Remote Server URL with authentication: [green]http://{host}:{port}/sse?s={api_key}&profile=<profile_name>[/]"
                )
            else:
                console.print("\n[bold cyan]To use a specific profile:[/]")
                console.print(
                    f"Remote Server URL with authentication: [green]http://{host}:{port}/sse?profile=<profile_name>[/]"
                )
        else:
            console.print(f"Remote Server URL: [green]http://{host}:{port}/mcp/[/]")
            if api_key:
                console.print("\n[bold cyan]To use a specific profile with authentication:[/]")
                console.print("[bold]Request headers:[/]")
                console.print(f"{MCPM_AUTH_HEADER}: {api_key}")
            else:
                console.print("\n[bold cyan]To use a specific profile:[/]")
                console.print("[bold]Request headers:[/]")
            console.print(f"{MCPM_PROFILE_HEADER}: <profile_name>")

        console.print("\n[yellow]Use 'mcpm router off' to stop the router.[/]")

    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to start MCPRouter: {e}")


@router.command(name="set")
@click.option("-H", "--host", type=str, help="Host to bind the SSE server to")
@click.option("-p", "--port", type=int, help="Port to bind the SSE server to")
@click.option("-a", "--address", type=str, help="Remote address to share the router")
@click.option(
    "--auth/--no-auth", default=True, is_flag=True, help="Enable/disable API key authentication (default: enabled)"
)
@click.option("-s", "--secret", type=str, help="Secret key for authentication")
@click.help_option("-h", "--help")
def set_router_config(host, port, address, auth, secret: str | None = None):
    """Set MCPRouter global configuration.

    Example:
        mcpm router set -H localhost -p 8888
        mcpm router set --host 127.0.0.1 --port 9000
        mcpm router set --no-auth  # disable authentication
        mcpm router set --auth  # enable authentication
    """
    if not host and not port and not address and auth is None:
        console.print(
            "[yellow]No changes were made. Please specify at least one option (--host, --port, --address, --auth/--no-auth)[/]"
        )
        return

    # get current config, make sure all field are filled by default value if not exists
    config_manager = ConfigManager()
    current_config = config_manager.get_router_config()

    # if user does not specify a host, use current config
    host = host or current_config["host"]
    port = port or current_config["port"]
    share_address = address or current_config["share_address"]
    api_key = secret

    if auth:
        # Enable authentication
        if api_key is None:
            # Generate a new API key if authentication is enabled but no key exists
            api_key = secrets.token_urlsafe(32)
            console.print("[bold green]API key authentication enabled.[/] Generated new API key.")
        else:
            console.print("[bold green]API key authentication enabled.[/] Using provided API key.")
    else:
        # Disable authentication by clearing the API key
        api_key = None
        console.print("[bold yellow]API key authentication disabled.[/]")

    # save router config
    if config_manager.save_router_config(host, port, share_address, api_key=api_key, auth_enabled=auth):
        console.print(
            f"[bold green]Router configuration updated:[/] host={host}, port={port}, share_address={share_address}"
        )
        console.print("The new configuration will be used next time you start the router.")

        # if router is running, prompt user to restart
        pid = read_pid_file()
        if pid:
            console.print("[yellow]Note: Router is currently running. Restart it to apply new settings:[/]")
            console.print("    mcpm router off")
            console.print("    mcpm router on")
    else:
        console.print("[bold red]Error:[/] Failed to save router configuration.")
        return

    if Confirm.ask("Do you want to update router for all clients now?"):
        active_profile = ClientRegistry.get_active_profile()
        if not active_profile:
            console.print("[yellow]No active profile found, skipped.[/]")
            return
        installed_clients = ClientRegistry.detect_installed_clients()
        for client, installed in installed_clients.items():
            if not installed:
                continue
            client_manager = ClientRegistry.get_client_manager(client)
            if client_manager is None:
                console.print(f"[yellow]Client '{client}' not found.[/] Skipping...")
                continue
            if client_manager.get_server(active_profile):
                console.print(f"[cyan]Updating profile router for {client}...[/]")
                client_manager.deactivate_profile(active_profile)
                client_manager.activate_profile(active_profile, config_manager.get_router_config())
                console.print(f"[green]Profile router updated for {client}[/]")
        console.print("[bold green]Success: Profile router updated for all clients[/]")
        if pid:
            console.print("[bold yellow]Restart MCPRouter to apply new settings.[/]\n")


@router.command(name="off")
@click.help_option("-h", "--help")
def stop_router():
    """Stop the running MCPRouter daemon process.

    Example:

    \b
        mcpm router off
    """
    # check if there is a router already running
    pid = read_pid_file()
    if not pid:
        console.print("[yellow]MCPRouter is not running.[/]")
        try_clear_share()
        return

    # send termination signal
    try:
        # stop share link first
        try_clear_share()

        # kill process
        os.kill(pid, signal.SIGTERM)
        console.print(f"[bold green]MCPRouter stopped (PID: {pid})[/]")

        # delete PID file
        remove_pid_file()
    except OSError as e:
        console.print(f"[bold red]Error:[/] Failed to stop MCPRouter: {e}")

        # if process does not exist, clean up PID file
        if e.errno == 3:  # "No such process"
            console.print("[yellow]Process does not exist, cleaning up PID file...[/]")
            remove_pid_file()


@router.command(name="status")
@click.help_option("-h", "--help")
def router_status():
    """Check the status of the MCPRouter daemon process.

    Example:

    \b
        mcpm router status
    """
    # get router config
    config = ConfigManager().get_router_config()
    host = config["host"]
    port = config["port"]

    # check process status
    pid = read_pid_file()
    if pid:
        if not is_port_listening(host, port):
            console.print(
                f"[bold yellow]Notice:[/] [bold cyan]{host}:{port}[/] is not yet accepting connections. The service may still be starting up. Please wait a few seconds and try again."
            )
            console.print(
                f"[yellow]If this message persists after waiting, please check the log for more details.[/] (Log file: {LOG_DIR / 'router_access.log'})"
            )
            return

        console.print(f"[bold green]MCPRouter is running[/] at http://{host}:{port} (PID: {pid})")
        share_config = ConfigManager().read_share_config()
        if share_config.get("pid"):
            if not is_process_running(share_config["pid"]):
                console.print("[yellow]Share link is not active, cleaning.[/]")
                ConfigManager().save_share_config(share_url=None, share_pid=None)
                console.print("[green]Share link cleaned[/]")
            else:
                console.print(
                    f"[bold green]MCPRouter is sharing[/] at {share_config['url']} (PID: {share_config['pid']})"
                )
    else:
        console.print("[yellow]MCPRouter is not running.[/]")


@router.command()
@click.help_option("-h", "--help")
@click.option("-a", "--address", type=str, required=False, help="Remote address to bind the tunnel to")
@click.option("-p", "--profile", type=str, required=False, help="Profile to share")
@click.option("--http", type=bool, flag_value=True, required=False, help="Use HTTP instead of HTTPS")
def share(address, profile, http):
    """Create a share link for the MCPRouter daemon process.

    Example:

    \b
        mcpm router share --address example.com:8877
    """

    # check if there is a router already running
    pid = read_pid_file()
    config_manager = ConfigManager()
    config = config_manager.get_router_config()
    if not pid:
        console.print("[yellow]MCPRouter is not running.[/]")
        return

    if not profile:
        active_profile = ClientRegistry.get_active_profile()
        if not active_profile:
            console.print("[yellow]No active profile found. You need to specify a profile to share.[/]")

        console.print(f"[cyan]Sharing with active profile {active_profile}...[/]")
        profile = active_profile
    else:
        console.print(f"[cyan]Sharing with profile {profile}...[/]")

    # check if share link is already active
    share_config = config_manager.read_share_config()
    if share_config.get("pid"):
        console.print(f"[yellow]Share link is already active at {share_config['url']}.[/]")
        return

    # get share address
    if not address:
        console.print("[cyan]Using share address from config...[/]")
        address = config["share_address"]

    # create share link
    remote_host, remote_port = address.split(":")

    # start tunnel
    tunnel = Tunnel(remote_host, remote_port, config["host"], config["port"], secrets.token_urlsafe(32), http, None)
    share_url = tunnel.start_tunnel()
    share_pid = tunnel.proc.pid if tunnel.proc else None
    api_key = config.get("api_key") if config.get("auth_enabled") else None

    share_url = share_url + "/mcp/"
    # save share pid and link to config
    config_manager.save_share_config(share_url, share_pid)
    profile = profile or "<your_profile>"

    # print share link
    console.print(f"[bold green]Router is sharing at {share_url}[/]")
    console.print(f"[green]Your profile can be accessed with the url {share_url}[/]\n")
    if api_key:
        console.print(f"[green]Authorize with header {MCPM_AUTH_HEADER}: {api_key}[/]")
    console.print(f"[green]Specify profile with header {MCPM_PROFILE_HEADER}: {profile}[/]")
    console.print(
        "[bold yellow]Be careful about the share link, it will be exposed to the public. Make sure to share to trusted users only.[/]"
    )


def try_clear_share():
    console.print("[bold yellow]Clearing share config...[/]")
    config_manager = ConfigManager()
    share_config = config_manager.read_share_config()
    if share_config.get("url"):
        try:
            console.print("[bold yellow]Disabling share link...[/]")
            config_manager.save_share_config(share_url=None, share_pid=None)
            console.print("[bold green]Share link disabled[/]")
            if share_config.get("pid"):
                os.kill(share_config["pid"], signal.SIGTERM)
        except OSError as e:
            if e.errno == 3:  # "No such process"
                console.print("[yellow]Share process does not exist, cleaning up share config...[/]")
                config_manager.save_share_config(share_url=None, share_pid=None)
            else:
                console.print(f"[bold red]Error:[/] Failed to stop share link: {e}")


@router.command("unshare")
@click.help_option("-h", "--help")
def stop_share():
    """Stop the share link for the MCPRouter daemon process."""
    # check if there is a share link already running
    config_manager = ConfigManager()
    share_config = config_manager.read_share_config()
    if not share_config.get("url"):
        console.print("[yellow]No share link is active.[/]")
        return

    pid = share_config.get("pid")
    if not pid:
        console.print("[yellow]No share link is active.[/]")
        return

    # send termination signal
    try_clear_share()
