from enum import Enum


class ConfigType(str, Enum):
    FILE = "file"
    CLOUD = "cloud"
