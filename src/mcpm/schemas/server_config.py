from typing import Any, Dict, List, Union

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

        # Filter out empty environment variables
        non_empty_env = {}
        for key, value in self.env.items():
            # For environment variable references like ${VAR_NAME}, check if the variable exists
            # and has a non-empty value. If it doesn't exist or is empty, exclude it.
            if value is not None and isinstance(value, str):
                if value.startswith("${") and value.endswith("}"):
                    # Extract the variable name from ${VAR_NAME}
                    env_var_name = value[2:-1]
                    env_value = environment.get(env_var_name, "")
                    # Only include if the variable has a value in the environment
                    if env_value.strip() != "":
                        non_empty_env[key] = value
                # For regular values, only include if they're not empty
                elif value.strip() != "":
                    non_empty_env[key] = value

        return non_empty_env


class SSEServerConfig(BaseServerConfig):
    url: str
    headers: Dict[str, Any] = {}


ServerConfig = Union[STDIOServerConfig, SSEServerConfig]
