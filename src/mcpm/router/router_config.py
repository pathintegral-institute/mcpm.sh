from typing import Optional

from pydantic import BaseModel, field_validator


class RouterConfig(BaseModel):
    """
    Router configuration model for MCPRouter
    """

    strict: bool = False
    api_key: Optional[str] = None
    auth_enabled: bool = False

    @field_validator("api_key", mode="after")
    def check_api_key(cls, v, info):
        # info is ValidationInfo in pydantic v2; info.data is the dict of parsed values
        if info.data.get("auth_enabled") and v is None:
            raise ValueError("api_key must be provided when auth_enabled is True")
        return v
