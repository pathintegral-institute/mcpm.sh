"""
Repository utilities for MCPM - handles server discovery and installation
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

# Default repository URL
DEFAULT_REPO_URL = "https://getmcp.io/api/servers.json"

class RepositoryManager:
    """Manages server repository operations"""
    
    def __init__(self, repo_url: str = DEFAULT_REPO_URL):
        self.repo_url = repo_url
        self.servers_cache = None
        self.last_refresh = None
    
    def _fetch_servers(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Fetch servers data from the repository
        
        Args:
            force_refresh: Force a refresh of the cache
            
        Returns:
            Dictionary of server data indexed by server name
        """
        # Return cached data if available and not forcing refresh
        if self.servers_cache and not force_refresh and self.last_refresh:
            # Cache for 1 hour
            age = (datetime.now() - self.last_refresh).total_seconds()
            if age < 3600:  # 1 hour in seconds
                return self.servers_cache
        
        try:
            response = requests.get(self.repo_url)
            response.raise_for_status()
            self.servers_cache = response.json()
            self.last_refresh = datetime.now()
            return self.servers_cache
        except requests.RequestException as e:
            logger.error(f"Failed to fetch servers from {self.repo_url}: {e}")
            # Return empty dict if we can't fetch and have no cache
            return self.servers_cache or {}
    
    def search_servers(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for available MCP servers
        
        Args:
            query: Optional search query
            
        Returns:
            List of matching server metadata
        """
        servers_dict = self._fetch_servers()
        results = list(servers_dict.values())
        
        # Filter by query if provided
        if query:
            query = query.lower()
            filtered_results = []
            
            for server in results:
                # Check standard fields
                if (query in server["name"].lower() or
                    query in server.get("description", "").lower() or
                    query in server.get("display_name", "").lower()):
                    filtered_results.append(server)
                    continue
                    
                # Check in tags
                if "tags" in server and any(query in tag.lower() for tag in server["tags"]):
                    filtered_results.append(server)
                    continue
                    
                # Check in categories
                if "categories" in server and any(query in cat.lower() for cat in server["categories"]):
                    filtered_results.append(server)
                    continue
                    
            results = filtered_results
        
        # No additional filtering by tags or category in the new simplified architecture
        
        return results
    
    def get_server_metadata(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server metadata or None if not found
        """
        servers_dict = self._fetch_servers()
        return servers_dict.get(server_name)
    
    def get_available_versions(self, server_name: str) -> List[str]:
        """
        Get available versions for a server
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of available versions, currently just returns the current version
        """
        metadata = self.get_server_metadata(server_name)
        if metadata and "version" in metadata:
            return [metadata["version"]]
        return []
    
    def download_server(self, server_name: str, version: Optional[str] = None, 
                       dest_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Download an MCP server package
        
        Args:
            server_name: Name of the server to download
            version: Optional specific version to download
            dest_dir: Directory to download to
            
        Returns:
            Server metadata if successful, None otherwise
        """
        metadata = self.get_server_metadata(server_name)
        if not metadata:
            logger.error(f"Server not found: {server_name}")
            return None
            
        if version and metadata["version"] != version:
            logger.error(f"Version {version} not found for server {server_name}")
            return None
        
        # Use the latest version if none specified
        if not version:
            version = metadata["version"]
            
        # Create the destination directory if needed
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
            
        # Store the metadata in the destination directory
        if dest_dir:
            metadata_path = Path(dest_dir) / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        logger.info(f"Downloaded server {server_name} v{metadata['version']}")
        return metadata
