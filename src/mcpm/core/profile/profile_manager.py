from profile import Profile

from mcpm.core.schema import ServerConfig


class AbstractProfileManager:
    def __init__(self):
        pass

    def get_profile(self, name: str) -> Profile | None:
        raise NotImplementedError

    def validate_api_key(self, profile_name: str, api_key: str) -> bool:
        raise NotImplementedError

    def create_profile(self, profile_name: str) -> None:
        raise NotImplementedError

    def delete_profile(self, profile_name: str) -> None:
        raise NotImplementedError

    def list_profiles(self) -> list[Profile]:
        raise NotImplementedError

    def rename_profile(self, old_name: str, new_name: str) -> None:
        raise NotImplementedError

    def add_server(self, profile_name: str, server_config: ServerConfig) -> None:
        raise NotImplementedError

    def remove_server(self, profile_name: str, server_name: str) -> None:
        raise NotImplementedError

    def update_server(self, profile_name: str, server_config: ServerConfig) -> None:
        raise NotImplementedError

    async def activate_profile(self, profile_name: str) -> None:
        raise NotImplementedError

    async def deactivate_profile(self, profile_name: str) -> None:
        raise NotImplementedError
