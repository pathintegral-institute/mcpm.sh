import json
import os
from typing import Dict, Optional, override

from mcpm.core.mcp.client_connection import ServerConnection
from mcpm.core.profile.profile_manager import AbstractProfileManager
from mcpm.core.schema import Profile, ServerConfig

DEFAULT_PROFILE_PATH = os.path.expanduser("~/.config/mcpm/profiles.json")


class LocalProfileManager(AbstractProfileManager):
    def __init__(self, profile_path: str = DEFAULT_PROFILE_PATH):
        super().__init__()
        self.profile_path = profile_path
        self._profiles = self._load_profiles()
        self.server_connections: Dict[str, Dict[str, ServerConnection]] = {}

    def _load_profiles(self) -> Dict[str, Profile]:
        if not os.path.exists(self.profile_path):
            return {}
        with open(self.profile_path, "r") as f:
            conf = json.load(f)
            return {name: Profile.model_validate(config) for name, config in conf.items()}

    def _save_profiles(self) -> None:
        with open(self.profile_path, "w") as f:
            json.dump(self._profiles, f, indent=2)

    def get_profile(self, name: str) -> Optional[Profile]:
        return self._profiles.get(name)

    def validate_api_key(self, profile_name: str, api_key: str) -> bool:
        profile = self.get_profile(profile_name)
        if not profile:
            return False
        return api_key == profile.api_key

    def create_profile(self, profile_name: str) -> None:
        if profile_name in self._profiles:
            return
        self._profiles[profile_name] = Profile(name=profile_name, servers=[])
        self._save_profiles()

    def delete_profile(self, profile_name: str) -> None:
        if profile_name not in self._profiles:
            return
        del self._profiles[profile_name]
        self._save_profiles()

    def list_profiles(self) -> list[Profile]:
        return list(self._profiles.values())

    def rename_profile(self, old_name: str, new_name: str) -> None:
        if old_name not in self._profiles:
            return
        if new_name in self._profiles:
            return
        self._profiles[new_name] = self._profiles.pop(old_name)
        self._save_profiles()

    def add_server(self, profile_name: str, server_config: ServerConfig) -> None:
        if profile_name not in self._profiles:
            return
        self._profiles[profile_name].servers.append(server_config)
        self._save_profiles()

    def remove_server(self, profile_name: str, server_name: str) -> None:
        if profile_name not in self._profiles:
            return
        self._profiles[profile_name].servers = [
            server for server in self._profiles[profile_name].servers if server.name != server_name
        ]
        self._save_profiles()

    def update_server(self, profile_name: str, server_config: ServerConfig) -> None:
        if profile_name not in self._profiles:
            return
        for idx, server in enumerate(self._profiles[profile_name].servers):
            if server.name == server_config.name:
                self._profiles[profile_name].servers[idx] = server_config
                break
        self._save_profiles()

    @override
    async def activate_profile(self, profile_name: str) -> Dict[str, ServerConnection]:
        if profile_name not in self._profiles:
            return {}
        servers = self._profiles[profile_name].servers
        self.server_connections[profile_name] = {
            server_config.name: ServerConnection(server_config) for server_config in servers
        }
        return self.server_connections[profile_name]

    @override
    async def deactivate_profile(self, profile_name: str) -> None:
        if profile_name not in self._profiles:
            return
        if profile_name not in self.server_connections:
            return
        for _, client in self.server_connections[profile_name].items():
            await client.request_for_shutdown()
        self.server_connections.pop(profile_name)
