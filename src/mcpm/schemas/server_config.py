import warnings

from mcpm.core.schema import RemoteServerConfig, ServerConfig, STDIOServerConfig

__all__ = ["ServerConfig", "RemoteServerConfig", "STDIOServerConfig", "RemoteServerConfig"]

warnings.warn("mcpm.schemas.server_config is deprecated, use mcpm.core.schema instead", DeprecationWarning)
