from enum import StrEnum

CLIENT_PREFIX = "@"
PROFILE_PREFIX = "%"


class ScopeType(StrEnum):
    CLIENT = "client"
    PROFILE = "profile"
    GLOBAL = "global"  # v2.0: Global MCPM configuration


def normalize_scope(scope: str):
    if not scope.startswith(CLIENT_PREFIX) and not scope.startswith(PROFILE_PREFIX):
        return f"{CLIENT_PREFIX}{scope}"
    return scope


def extract_from_scope(scope: str):
    scope = normalize_scope(scope)
    if scope.startswith(CLIENT_PREFIX):
        return ScopeType.CLIENT, scope[1:]
    if scope.startswith(PROFILE_PREFIX):
        return ScopeType.PROFILE, scope[1:]
    raise ValueError(f"Invalid scope: {scope}")


def parse_server(server: str):
    """
    Parse a server string into its components.

    Args:
        server (str): The server string to parse.

    Returns:
        tuple: A tuple containing the context type, context name, and server name.
    """
    client_type, server_name = extract_from_scope(server)
    splitted = server_name.split("/", 1)
    if len(splitted) == 1:
        if server.startswith(CLIENT_PREFIX) or server.startswith(PROFILE_PREFIX):
            return client_type, splitted[0], ""
        return ScopeType.CLIENT, "", splitted[0]
    return client_type, splitted[0], splitted[1]


def format_scope(scope_type: ScopeType, scope_name: str):
    if scope_type == ScopeType.CLIENT and not scope_name.startswith(CLIENT_PREFIX):
        return f"{CLIENT_PREFIX}{scope_name}"
    if scope_type == ScopeType.PROFILE and not scope_name.startswith(PROFILE_PREFIX):
        return f"{PROFILE_PREFIX}{scope_name}"
    return scope_name
