"""
Source metadata management for MCP servers.

Tracks where servers came from (git repo, npm package, binary release, etc.)
so that `mcpm update` can check for and apply updates.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, TypeAdapter

from mcpm.core.schema import RemoteServerConfig, ServerConfig, STDIOServerConfig
from mcpm.utils.platform import get_config_directory

DEFAULT_SOURCES_PATH = get_config_directory() / "sources.json"

logger = logging.getLogger(__name__)


# --- Pydantic models ---


class GitSource(BaseModel):
    type: Literal["git"] = "git"
    path: str
    remote_url: Optional[str] = None
    branch: Optional[str] = None
    post_update: Optional[str] = None
    last_checked: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class GithubReleaseSource(BaseModel):
    type: Literal["github-release"] = "github-release"
    path: str
    repo: str
    current_version: Optional[str] = None
    asset_pattern: Optional[str] = None
    last_checked: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class NpxSource(BaseModel):
    type: Literal["npx"] = "npx"
    package: str


class UvxSource(BaseModel):
    type: Literal["uvx"] = "uvx"
    package: str


class RemoteSource(BaseModel):
    type: Literal["remote"] = "remote"


class UnknownSource(BaseModel):
    type: Literal["unknown"] = "unknown"
    reason: Optional[str] = None


SourceMetadata = Union[GitSource, GithubReleaseSource, NpxSource, UvxSource, RemoteSource, UnknownSource]

_source_adapter = TypeAdapter(SourceMetadata)


# --- Path resolution ---


def _find_git_root(start_path: Path) -> Optional[Path]:
    """Walk up from start_path looking for a .git directory."""
    current = start_path if start_path.is_dir() else start_path.parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def _extract_directory_from_args(args: List[str]) -> Optional[str]:
    """Extract --directory value from args list (used by uv run)."""
    for i, arg in enumerate(args):
        if arg == "--directory" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--directory="):
            return arg.split("=", 1)[1]
    return None


def _extract_npx_package(args: List[str]) -> Optional[str]:
    """Extract the npm package name from npx args, stripping flags like -y and @version suffixes."""
    for arg in args:
        if not arg.startswith("-"):
            if arg.startswith("@"):
                # Scoped package: @scope/name or @scope/name@version
                slash_idx = arg.find("/")
                if slash_idx != -1:
                    version_at = arg.find("@", slash_idx)
                    if version_at != -1:
                        return arg[:version_at]
                return arg
            else:
                # Unscoped package: name or name@version
                at_idx = arg.find("@")
                if at_idx > 0:
                    return arg[:at_idx]
                return arg
    return None


def detect_source(server_config: ServerConfig) -> SourceMetadata:
    """Auto-detect the source type for a server based on its configuration."""

    if isinstance(server_config, RemoteServerConfig):
        return RemoteSource()

    if not isinstance(server_config, STDIOServerConfig):
        return UnknownSource(reason="unsupported config type")

    command = server_config.command.strip()
    args = server_config.args

    # NPX-based servers
    if command in ("npx", "npx.cmd"):
        package = _extract_npx_package(args)
        if package:
            return NpxSource(package=package)
        return UnknownSource(reason="npx server but could not determine package name")

    # UVX-based servers
    if command == "uvx":
        package = _extract_npx_package(args)  # Same arg parsing logic works
        if package:
            return UvxSource(package=package)
        return UnknownSource(reason="uvx server but could not determine package name")

    # UV run with --directory (e.g. codeforward-odoo, codeforward-typst)
    if command == "uv" and args and args[0] == "run":
        directory = _extract_directory_from_args(args)
        if directory:
            dir_path = Path(directory)
            if dir_path.exists():
                git_root = _find_git_root(dir_path)
                if git_root:
                    return GitSource(path=str(git_root))
            return GitSource(path=directory)
        return UnknownSource(reason="uv run server but no --directory found")

    # Command is an absolute path (e.g. /path/to/binary or /path/to/.venv/bin/python)
    cmd_path = Path(command)
    if cmd_path.is_absolute() and cmd_path.exists():
        # Check if the command or its args point to a git repo
        git_root = _find_git_root(cmd_path)
        if git_root:
            return GitSource(path=str(git_root))

        # Check first arg too (e.g. python /path/to/script.py)
        if args:
            first_arg_path = Path(args[0])
            if first_arg_path.is_absolute() and first_arg_path.exists():
                git_root = _find_git_root(first_arg_path)
                if git_root:
                    return GitSource(path=str(git_root))

        return UnknownSource(reason=f"absolute path but no git repo found: {command}")

    # Node with absolute path arg (e.g. node /path/to/dist/index.js)
    if command == "node" and args:
        first_arg_path = Path(args[0])
        if first_arg_path.is_absolute():
            if first_arg_path.exists():
                git_root = _find_git_root(first_arg_path)
                if git_root:
                    return GitSource(path=str(git_root))
            return UnknownSource(reason=f"node server but no git repo found at: {args[0]}")

    return UnknownSource(reason=f"could not determine source type for command: {command}")


# --- Sources manager ---


class SourcesManager:
    """Read/write sources.json — tracks where each server came from."""

    def __init__(self, sources_path: Path = DEFAULT_SOURCES_PATH):
        self.sources_path = Path(sources_path)
        self._sources: Dict[str, SourceMetadata] = self._load()

    def _load(self) -> Dict[str, SourceMetadata]:
        if not self.sources_path.exists():
            return {}
        try:
            with open(self.sources_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Error loading sources from {self.sources_path}: {e}")
            return {}

        sources = {}
        for name, source_data in data.items():
            try:
                sources[name] = _source_adapter.validate_python(source_data)
            except Exception as e:
                logger.warning(f"Skipping invalid source entry '{name}': {e}")
        return sources

    def _save(self) -> None:
        try:
            self.sources_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for name, source in self._sources.items():
                data[name] = source.model_dump(mode="json", exclude_none=True)
            with open(self.sources_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Error saving sources to {self.sources_path}: {e}")

    def get(self, name: str) -> Optional[SourceMetadata]:
        return self._sources.get(name)

    def set(self, name: str, source: SourceMetadata) -> None:
        self._sources[name] = source
        self._save()

    def remove(self, name: str) -> bool:
        if name in self._sources:
            del self._sources[name]
            self._save()
            return True
        return False

    def list_all(self) -> Dict[str, SourceMetadata]:
        return dict(self._sources)

    def mark_checked(self, name: str) -> None:
        source = self._sources.get(name)
        if source and hasattr(source, "last_checked"):
            source.last_checked = datetime.now(timezone.utc)
            self._save()

    def mark_updated(self, name: str) -> None:
        source = self._sources.get(name)
        if source and hasattr(source, "last_updated"):
            source.last_updated = datetime.now(timezone.utc)
            source.last_checked = datetime.now(timezone.utc)
            self._save()
