from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class BaseServerConfig(BaseModel):
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class STDIOServerConfig(BaseServerConfig):
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}

    def get_filtered_env_vars(self, env: Dict[str, str]) -> Dict[str, str]:
        """Get filtered environment variables with empty values removed

        This is a utility for clients to filter out empty environment
        variables, regardless of client-specific formatting.

        Args:
            env: Dictionary of environment variables to use for resolving
                 ${VAR_NAME} references.

        Returns:
            Dictionary of non-empty environment variables
        """
        if not self.env:
            return {}

        # Use provided environment without falling back to os.environ
        environment = env

        # Keep all environment variables, including empty strings
        filtered_env = {}
        for key, value in self.env.items():
            # For environment variable references like ${VAR_NAME}, check if the variable exists
            # and has a non-empty value. If it doesn't exist or is empty, exclude it.
            if value is not None and isinstance(value, str):
                if value.startswith("${") and value.endswith("}"):
                    # Extract the variable name from ${VAR_NAME}
                    env_var_name = value[2:-1]
                    env_value = environment.get(env_var_name, "")
                    # Include all values, even empty ones
                    filtered_env[key] = env_value
                else:
                    # Include all values, even empty ones
                    filtered_env[key] = value

        return filtered_env


class RemoteServerConfig(BaseServerConfig):
    url: str
    headers: Dict[str, Any] = {}

    def to_mcp_proxy_stdio(self) -> STDIOServerConfig:
        proxy_args = [
            "mcp-proxy",
            self.url,
        ]
        if self.headers:
            proxy_args.append("--headers")
            for key, value in self.headers.items():
                proxy_args.append(f"{key}")
                proxy_args.append(f"{value}")

        return STDIOServerConfig(
            name=self.name,
            command="uvx",
            args=proxy_args,
        )


class CustomServerConfig(BaseServerConfig):
    config: Dict[str, Any]


ServerConfig = Union[STDIOServerConfig, RemoteServerConfig, CustomServerConfig]


class Profile(BaseModel):
    name: str
    api_key: Optional[str]
    servers: list[ServerConfig]
