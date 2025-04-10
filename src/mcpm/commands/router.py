"""
Router command for managing the MCPRouter daemon process
"""

import logging
import os
import signal
import subprocess
import sys

import click
import psutil
from rich.console import Console

from mcpm.utils.platform import get_log_directory, get_pid_directory

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
console = Console()

APP_SUPPORT_DIR = get_pid_directory("mcpm")
APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE = APP_SUPPORT_DIR / "router.pid"

LOG_DIR = get_log_directory("mcpm")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def is_process_running(pid):
    """check if the process is running"""
    try:
        return psutil.pid_exists(pid)
    except Exception:
        return False


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
        logger.info(f"PID {pid} written to {PID_FILE}")
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
def router():
    """Manage MCP router service."""
    pass


@router.command(name="on")
@click.option("--host", type=str, default="0.0.0.0", help="Host to bind the SSE server to")
@click.option("--port", type=int, default=8080, help="Port to bind the SSE server to")
@click.option("--cors", type=str, help="Comma-separated list of allowed origins for CORS")
def start_router(host, port, cors):
    """Start MCPRouter as a daemon process.

    Example:
        mcpm router on
        mcpm router on --port 8888
        mcpm router on --host 0.0.0.0 --port 9000
    """
    # check if there is a router already running
    existing_pid = read_pid_file()
    if existing_pid:
        console.print(f"[bold red]Error:[/] MCPRouter is already running (PID: {existing_pid})")
        console.print("Use 'mcpm router off' to stop the running instance.")
        return

    # prepare environment variables
    env = os.environ.copy()
    if cors:
        env["MCPM_ROUTER_CORS"] = cors

    # prepare uvicorn command
    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "mcpm.router.app:app",
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
            process = subprocess.Popen(
                uvicorn_cmd,
                stdout=log,
                stderr=log,
                env=env,
                start_new_session=True,  # create new session, so the process won't be affected by terminal closing
            )

        # record PID
        pid = process.pid
        write_pid_file(pid)

        console.print(f"[bold green]MCPRouter started[/] at http://{host}:{port} (PID: {pid})")
        console.print(f"Log file: {log_file}")
        console.print("Use 'mcpm router off' to stop the router.")

    except Exception as e:
        console.print(f"[bold red]Error:[/] Failed to start MCPRouter: {e}")


@router.command(name="off")
def stop_router():
    """Stop the running MCPRouter daemon process.

    Example:
        mcpm router off
    """
    # check if there is a router already running
    pid = read_pid_file()
    if not pid:
        console.print("[yellow]MCPRouter is not running.[/]")
        return

    # send termination signal
    try:
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
def router_status():
    """Check the status of the MCPRouter daemon process.

    Example:
        mcpm router status
    """
    pid = read_pid_file()
    if pid:
        console.print(f"[bold green]MCPRouter is running[/] (PID: {pid})")
    else:
        console.print("[yellow]MCPRouter is not running.[/]")
