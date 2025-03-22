"""
Server management utilities for MCP
"""

import logging
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ServerManager:
    """Manages MCP server processes"""
    
    def __init__(self, config_manager):
        """
        Initialize with a ConfigManager instance
        
        Args:
            config_manager: ConfigManager instance to use for configuration
        """
        self.config_manager = config_manager
    
    def start_server(self, server_name: str) -> bool:
        """
        Start an MCP server
        
        Args:
            server_name: Name of the server to start
            
        Returns:
            True if successful, False otherwise
        """
        server_info = self.config_manager.get_server_info(server_name)
        if not server_info:
            logger.error(f"Server not installed: {server_name}")
            return False
        
        # Check if already running
        pid = self._get_server_pid(server_name)
        if pid:
            logger.info(f"Server {server_name} is already running (PID: {pid})")
            return True
        
        # In a real implementation, this would start the server process
        # For now, we'll just update the metadata
        
        # Mock starting a server
        logger.info(f"Starting server: {server_name}")
        
        # Update server info to indicate it's running
        server_info['status'] = 'running'
        server_info['mock_pid'] = 12345  # In a real implementation, this would be the actual PID
        self.config_manager.register_server(server_name, server_info)
        
        return True
    
    def stop_server(self, server_name: str) -> bool:
        """
        Stop an MCP server
        
        Args:
            server_name: Name of the server to stop
            
        Returns:
            True if successful, False otherwise
        """
        server_info = self.config_manager.get_server_info(server_name)
        if not server_info:
            logger.error(f"Server not installed: {server_name}")
            return False
        
        # Check if running
        pid = self._get_server_pid(server_name)
        if not pid:
            logger.info(f"Server {server_name} is not running")
            return True
        
        # In a real implementation, this would stop the server process
        # For now, we'll just update the metadata
        
        # Mock stopping a server
        logger.info(f"Stopping server: {server_name}")
        
        # Update server info to indicate it's stopped
        server_info['status'] = 'stopped'
        if 'mock_pid' in server_info:
            del server_info['mock_pid']
        self.config_manager.register_server(server_name, server_info)
        
        return True
    
    def restart_server(self, server_name: str) -> bool:
        """
        Restart an MCP server
        
        Args:
            server_name: Name of the server to restart
            
        Returns:
            True if successful, False otherwise
        """
        success = self.stop_server(server_name)
        if not success:
            return False
        
        # Small delay to ensure clean shutdown
        time.sleep(0.5)
        
        return self.start_server(server_name)
    
    def get_server_status(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status information for a server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Status information or None if server not found
        """
        server_info = self.config_manager.get_server_info(server_name)
        if not server_info:
            return None
        
        # Check if running
        pid = self._get_server_pid(server_name)
        
        status_info = {
            'name': server_name,
            'installed_version': server_info.get('version', 'unknown'),
            'running': bool(pid),
            'status': server_info.get('status', 'unknown'),
            'pid': pid,
            'clients': []
        }
        
        # Get clients that have this server enabled
        for client_name, client_info in self.config_manager.get_config().get('clients', {}).items():
            if server_name in client_info.get('enabled_servers', []):
                status_info['clients'].append(client_name)
        
        return status_info
    
    def get_all_server_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all servers
        
        Returns:
            Dictionary of server statuses keyed by server name
        """
        result = {}
        for server_name in self.config_manager.get_all_servers():
            status = self.get_server_status(server_name)
            if status:
                result[server_name] = status
        return result
    
    def get_log(self, server_name: str, lines: int = 50) -> List[str]:
        """
        Get log entries for a server
        
        Args:
            server_name: Name of the server
            lines: Number of log lines to return
            
        Returns:
            List of log lines
        """
        server_info = self.config_manager.get_server_info(server_name)
        if not server_info:
            logger.error(f"Server not installed: {server_name}")
            return []
        
        # In a real implementation, this would read from the log file
        # For now, we'll return mock data
        
        return [
            f"[2025-03-22 12:57:00] Server {server_name} started",
            "[2025-03-22 12:57:01] Initialized configuration",
            "[2025-03-22 12:57:01] Listening for client connections",
            "[2025-03-22 12:57:15] Client connected: claude-desktop",
            "[2025-03-22 12:57:16] Processed request from claude-desktop"
        ][-lines:]
    
    def _get_server_pid(self, server_name: str) -> Optional[int]:
        """
        Get process ID for a running server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Process ID if running, None otherwise
        """
        server_info = self.config_manager.get_server_info(server_name)
        if not server_info:
            return None
        
        # In a real implementation, this would check if the process is running
        # For now, we'll just check our mock data
        
        # Check if we have a mock_pid (meaning it's "running")
        return server_info.get('mock_pid')
