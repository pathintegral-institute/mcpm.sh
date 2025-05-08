from enum import Enum


class ResourceType(str, Enum):
    TOOL = "tool"
    PROMPT = "prompt"
    RESOURCE = "resource"
    RESOURCE_TEMPLATE = "resource_template"
