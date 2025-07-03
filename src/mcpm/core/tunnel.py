"""Simple tunnel functionality for sharing."""

import logging
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


class Tunnel:
    """Simple tunnel for sharing MCP servers."""

    def __init__(
        self,
        remote_host: str,
        remote_port: int,
        local_host: str,
        local_port: int,
        share_token: str,
        http: bool = False,
        share_server_tls_certificate: Optional[str] = None,
    ):
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_host = local_host
        self.local_port = local_port
        self.share_token = share_token
        self.http = http
        self.share_server_tls_certificate = share_server_tls_certificate
        self.process: Optional[subprocess.Popen] = None

    def start_tunnel(self) -> Optional[str]:
        """Start the tunnel and return the public URL."""
        try:
            # Create a temporary config file for frpc
            config_content = f"""[common]
server_addr = {self.remote_host}
server_port = {self.remote_port}

[{self.share_token}]
type = http
local_ip = {self.local_host}
local_port = {self.local_port}
custom_domains = {self.share_token}.{self.remote_host}
"""

            # Write config to temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
                f.write(config_content)
                config_path = f.name

            # Start frpc process
            cmd = ["frpc", "-c", config_path]
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Wait a moment for the tunnel to establish
            import time

            time.sleep(3)

            # Check if process is still running
            if self.process.poll() is not None:
                # Process died, read error
                _, stderr = self.process.communicate()
                logger.error(f"Tunnel process failed: {stderr}")
                return None

            # Return the public URL
            protocol = "http" if self.http else "https"
            public_url = f"{protocol}://{self.share_token}.{self.remote_host}"
            if self.remote_port not in (80, 443):
                public_url += f":{self.remote_port}"

            return public_url

        except Exception as e:
            logger.error(f"Failed to start tunnel: {e}")
            return None

    def kill(self):
        """Kill the tunnel process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"Error killing tunnel process: {e}")
