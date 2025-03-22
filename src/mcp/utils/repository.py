"""
Repository utilities for MCP - handles server discovery and installation
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Default repository URL
DEFAULT_REPO_URL = "https://getmcp.sh/api/servers"

class RepositoryManager:
    """Manages server repository operations"""
    
    def __init__(self, repo_url: str = DEFAULT_REPO_URL):
        self.repo_url = repo_url
    
    def search_servers(self, query: Optional[str] = None, tags: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for available MCP servers
        
        Args:
            query: Optional search query
            tags: Optional tag to filter by
            
        Returns:
            List of matching server metadata
        """
        # In a real implementation, this would make API calls to the repository
        # For now, we'll return mock data
        
        # Mock repository data
        mock_servers = [
            {
                "name": "filesystem",
                "display_name": "Filesystem",
                "description": "Access to local files and directories",
                "version": "1.0.0",
                "author": "MCP Team",
                "tags": ["files", "local", "essential"],
                "clients": ["claude-desktop", "cursor", "windsurf"]
            },
            {
                "name": "browser",
                "display_name": "Web Browser",
                "description": "Control and interact with web browser",
                "version": "0.9.2",
                "author": "MCP Team",
                "tags": ["web", "browser", "internet"],
                "clients": ["claude-desktop", "windsurf"]
            },
            {
                "name": "database",
                "display_name": "Database Access",
                "description": "Access SQL and NoSQL databases",
                "version": "0.8.5",
                "author": "MCP Team",
                "tags": ["database", "sql", "nosql"],
                "clients": ["claude-desktop", "cursor"]
            }
        ]
        
        # Filter by query if provided
        results = mock_servers
        if query:
            query = query.lower()
            results = [
                server for server in results
                if query in server["name"].lower() or
                   query in server["description"].lower() or
                   query in server["display_name"].lower()
            ]
        
        # Filter by tag if provided
        if tags:
            tags = tags.lower()
            results = [
                server for server in results
                if tags in [tag.lower() for tag in server["tags"]]
            ]
        
        return results
    
    def get_server_metadata(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server metadata or None if not found
        """
        # In a real implementation, this would make an API call
        # For now, we search in our mock data
        for server in self.search_servers():
            if server["name"] == server_name:
                return server
        return None
    
    def download_server(self, server_name: str, version: Optional[str] = None, 
                       dest_dir: str = None) -> Optional[Dict[str, Any]]:
        """
        Download an MCP server
        
        Args:
            server_name: Name of the server to download
            version: Optional specific version to download
            dest_dir: Directory to download to
            
        Returns:
            Server metadata if successful, None otherwise
        """
        # In a real implementation, this would download the server package
        # For now, we'll just return the metadata
        
        metadata = self.get_server_metadata(server_name)
        if not metadata:
            logger.error(f"Server not found: {server_name}")
            return None
            
        if version and metadata["version"] != version:
            logger.error(f"Version {version} not found for server {server_name}")
            return None
            
        logger.info(f"Downloaded server {server_name} v{metadata['version']}")
        return metadata
