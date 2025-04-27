"""
Repository utilities for MCPM - handles server discovery and installation
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

# Import ConfigManager to get the config directory
from mcpm.utils.config import DEFAULT_CONFIG_DIR

logger = logging.getLogger(__name__)

# Default repository URL
DEFAULT_REPO_URL = "https://mcpm.sh/api/servers.json"

# Default cache file path
DEFAULT_CACHE_FILE = os.path.join(DEFAULT_CONFIG_DIR, "servers_cache.json")


class RepositoryManager:
    """Manages server repository operations"""

    def __init__(self, repo_url: str = DEFAULT_REPO_URL, cache_file: str = DEFAULT_CACHE_FILE):
        self.repo_url = repo_url
        self.cache_file = cache_file
        self.servers_cache = None
        self.last_refresh = None

        # Ensure cache directory exists
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

        # Load cache from file if available
        self._load_cache_from_file()

    def _load_cache_from_file(self) -> None:
        """
        Load servers cache from file if it exists
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self.servers_cache = cache_data.get("servers")

                    # Parse the last_refresh timestamp if it exists
                    last_refresh_str = cache_data.get("last_refresh")
                    if last_refresh_str:
                        self.last_refresh = datetime.fromisoformat(last_refresh_str)

                    logger.debug(f"Loaded servers cache from {self.cache_file}")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing cache file: {self.cache_file}: {e}")
                self.servers_cache = None
                self.last_refresh = None

    def _save_cache_to_file(self) -> None:
        """
        Save servers cache to file
        """
        if self.servers_cache and self.last_refresh:
            try:
                cache_data = {"servers": self.servers_cache, "last_refresh": self.last_refresh.isoformat()}

                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, indent=2)

                logger.debug(f"Saved servers cache to {self.cache_file}")
            except Exception as e:
                logger.error(f"Failed to save cache to {self.cache_file}: {e}")

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

            # Save the updated cache to file
            self._save_cache_to_file()

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
                if (
                    query in server["name"].lower()
                    or query in server.get("description", "").lower()
                    or query in server.get("display_name", "").lower()
                ):
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
