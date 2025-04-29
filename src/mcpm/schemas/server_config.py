import warnings

from mcpm.core.schema import ServerConfig, SSEServerConfig, STDIOServerConfig

__all__ = ["ServerConfig", "SSEServerConfig", "STDIOServerConfig"]

warnings.warn("mcpm.schemas.server_config is deprecated, use mcpm.core.schema instead", DeprecationWarning)
