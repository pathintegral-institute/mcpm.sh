from typing import Optional

from pydantic import BaseModel

from mcpm.utils.config import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_SHARE_ADDRESS


class RouterConfig(BaseModel):
    """
    Router configuration model for MCPRouter
    """

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    share_address: str = DEFAULT_SHARE_ADDRESS
    api_key: Optional[str] = None
    strict: bool = False
