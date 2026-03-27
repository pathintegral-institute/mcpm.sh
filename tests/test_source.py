"""
Tests for source metadata detection and management.
"""

import json

from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig
from mcpm.core.source import (
    GitSource,
    NpxSource,
    RemoteSource,
    SourcesManager,
    UnknownSource,
    UvxSource,
    detect_source,
)

# --- Detection tests ---


class TestDetectSource:
    """Test auto-detection of source types from server configs."""

    def test_detect_npx_server(self):
        config = STDIOServerConfig(name="context7", command="npx", args=["-y", "@upstash/context7-mcp"])
        source = detect_source(config)
        assert isinstance(source, NpxSource)
        assert source.package == "@upstash/context7-mcp"

    def test_detect_npx_server_with_latest(self):
        config = STDIOServerConfig(name="playwright", command="npx", args=["@playwright/mcp@latest"])
        source = detect_source(config)
        assert isinstance(source, NpxSource)
        assert source.package == "@playwright/mcp"

    def test_detect_npx_server_no_flags(self):
        config = STDIOServerConfig(name="drawio", command="npx", args=["@drawio/mcp"])
        source = detect_source(config)
        assert isinstance(source, NpxSource)
        assert source.package == "@drawio/mcp"

    def test_detect_npx_server_with_version(self):
        config = STDIOServerConfig(name="scoped", command="npx", args=["-y", "@scope/pkg@1.2.3"])
        source = detect_source(config)
        assert isinstance(source, NpxSource)
        assert source.package == "@scope/pkg"

    def test_detect_npx_server_unscoped_with_version(self):
        config = STDIOServerConfig(name="unscoped", command="npx", args=["some-package@2.0.0"])
        source = detect_source(config)
        assert isinstance(source, NpxSource)
        assert source.package == "some-package"

    def test_detect_uvx_server(self):
        config = STDIOServerConfig(name="test", command="uvx", args=["some-mcp-server"])
        source = detect_source(config)
        assert isinstance(source, UvxSource)
        assert source.package == "some-mcp-server"

    def test_detect_remote_server(self):
        config = RemoteServerConfig(name="clickup", url="https://mcp.clickup.com/mcp")
        source = detect_source(config)
        assert isinstance(source, RemoteSource)

    def test_detect_uv_run_with_git_repo(self, tmp_path):
        """Test detection of uv run --directory pointing to a git repo."""
        # Create a fake git repo
        repo_dir = tmp_path / "my-server"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        config = STDIOServerConfig(
            name="my-server",
            command="uv",
            args=["run", "--directory", str(repo_dir), "python", "-m", "my_server"],
        )
        source = detect_source(config)
        assert isinstance(source, GitSource)
        assert source.path == str(repo_dir)

    def test_detect_uv_run_with_equals_syntax(self, tmp_path):
        """Test detection of uv run --directory=/path syntax."""
        repo_dir = tmp_path / "my-server"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        config = STDIOServerConfig(
            name="my-server",
            command="uv",
            args=["run", f"--directory={repo_dir}", "python", "-m", "my_server"],
        )
        source = detect_source(config)
        assert isinstance(source, GitSource)
        assert source.path == str(repo_dir)

    def test_detect_uv_run_no_directory(self):
        """Test uv run without --directory returns unknown."""
        config = STDIOServerConfig(name="test", command="uv", args=["run", "my-server"])
        source = detect_source(config)
        assert isinstance(source, UnknownSource)

    def test_detect_node_with_git_repo(self, tmp_path):
        """Test detection of node pointing to a file inside a git repo."""
        repo_dir = tmp_path / "my-mcp"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        dist_dir = repo_dir / "dist"
        dist_dir.mkdir()
        index_file = dist_dir / "index.js"
        index_file.touch()

        config = STDIOServerConfig(name="my-mcp", command="node", args=[str(index_file)])
        source = detect_source(config)
        assert isinstance(source, GitSource)
        assert source.path == str(repo_dir)

    def test_detect_absolute_binary_in_git_repo(self, tmp_path):
        """Test detection of a binary inside a git repo."""
        repo_dir = tmp_path / "my-server"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        binary = repo_dir / "my-binary"
        binary.touch()

        config = STDIOServerConfig(name="my-server", command=str(binary), args=["mcp"])
        source = detect_source(config)
        assert isinstance(source, GitSource)
        assert source.path == str(repo_dir)

    def test_detect_absolute_binary_no_git(self, tmp_path):
        """Test detection of a binary not inside a git repo."""
        binary = tmp_path / "my-binary"
        binary.touch()

        config = STDIOServerConfig(name="my-server", command=str(binary), args=["mcp"])
        source = detect_source(config)
        assert isinstance(source, UnknownSource)

    def test_detect_python_script_in_git_repo(self, tmp_path):
        """Test detection of python /path/to/script.py where script is in a git repo."""
        repo_dir = tmp_path / "my-server"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        venv_dir = repo_dir / ".venv" / "bin"
        venv_dir.mkdir(parents=True)
        python_bin = venv_dir / "python"
        python_bin.touch()
        script = repo_dir / "server.py"
        script.touch()

        config = STDIOServerConfig(name="my-server", command=str(python_bin), args=[str(script)])
        source = detect_source(config)
        assert isinstance(source, GitSource)
        assert source.path == str(repo_dir)

    def test_detect_npx_without_package(self):
        """Test npx with no recognizable package."""
        config = STDIOServerConfig(name="broken", command="npx", args=["-y"])
        source = detect_source(config)
        # -y is a flag, no package found
        assert isinstance(source, UnknownSource)


# --- SourcesManager tests ---


class TestSourcesManager:
    """Test sources.json read/write/management."""

    def test_empty_init(self, tmp_path):
        path = tmp_path / "sources.json"
        mgr = SourcesManager(sources_path=path)
        assert mgr.list_all() == {}

    def test_set_and_get(self, tmp_path):
        path = tmp_path / "sources.json"
        mgr = SourcesManager(sources_path=path)

        source = NpxSource(package="@test/mcp")
        mgr.set("test-server", source)

        retrieved = mgr.get("test-server")
        assert isinstance(retrieved, NpxSource)
        assert retrieved.package == "@test/mcp"

    def test_persistence(self, tmp_path):
        """Test that sources survive re-instantiation."""
        path = tmp_path / "sources.json"
        mgr1 = SourcesManager(sources_path=path)
        mgr1.set("my-server", GitSource(path="/some/path", branch="main"))

        # Re-instantiate from same file
        mgr2 = SourcesManager(sources_path=path)
        retrieved = mgr2.get("my-server")
        assert isinstance(retrieved, GitSource)
        assert retrieved.path == "/some/path"
        assert retrieved.branch == "main"

    def test_remove(self, tmp_path):
        path = tmp_path / "sources.json"
        mgr = SourcesManager(sources_path=path)
        mgr.set("server1", NpxSource(package="@test/one"))
        mgr.set("server2", NpxSource(package="@test/two"))

        assert mgr.remove("server1") is True
        assert mgr.get("server1") is None
        assert mgr.get("server2") is not None

    def test_remove_nonexistent(self, tmp_path):
        path = tmp_path / "sources.json"
        mgr = SourcesManager(sources_path=path)
        assert mgr.remove("doesnt-exist") is False

    def test_mark_checked(self, tmp_path):
        path = tmp_path / "sources.json"
        mgr = SourcesManager(sources_path=path)
        mgr.set("server1", GitSource(path="/some/path"))

        mgr.mark_checked("server1")
        source = mgr.get("server1")
        assert source.last_checked is not None

    def test_mark_updated(self, tmp_path):
        path = tmp_path / "sources.json"
        mgr = SourcesManager(sources_path=path)
        mgr.set("server1", GitSource(path="/some/path"))

        mgr.mark_updated("server1")
        source = mgr.get("server1")
        assert source.last_updated is not None
        assert source.last_checked is not None

    def test_list_all(self, tmp_path):
        path = tmp_path / "sources.json"
        mgr = SourcesManager(sources_path=path)
        mgr.set("a", NpxSource(package="@test/a"))
        mgr.set("b", RemoteSource())
        mgr.set("c", GitSource(path="/c"))

        all_sources = mgr.list_all()
        assert len(all_sources) == 3
        assert "a" in all_sources
        assert "b" in all_sources
        assert "c" in all_sources

    def test_corrupted_json(self, tmp_path):
        """Test graceful handling of corrupted sources.json."""
        path = tmp_path / "sources.json"
        path.write_text("{invalid json")

        mgr = SourcesManager(sources_path=path)
        assert mgr.list_all() == {}

    def test_invalid_source_entry(self, tmp_path):
        """Test graceful handling of invalid entries in sources.json."""
        path = tmp_path / "sources.json"
        path.write_text(json.dumps({
            "good-server": {"type": "npx", "package": "@test/good"},
            "bad-server": {"type": "nonexistent_type"},
        }))

        mgr = SourcesManager(sources_path=path)
        assert mgr.get("good-server") is not None
        assert mgr.get("bad-server") is None

    def test_all_source_types_roundtrip(self, tmp_path):
        """Test that all source types serialize and deserialize correctly."""
        path = tmp_path / "sources.json"
        mgr = SourcesManager(sources_path=path)

        mgr.set("git-server", GitSource(path="/git", remote_url="git@github.com:test/repo.git", branch="main", post_update="uv sync"))
        mgr.set("npx-server", NpxSource(package="@test/npx"))
        mgr.set("uvx-server", UvxSource(package="test-uvx"))
        mgr.set("remote-server", RemoteSource())
        mgr.set("unknown-server", UnknownSource(reason="test reason"))

        # Re-load
        mgr2 = SourcesManager(sources_path=path)
        assert isinstance(mgr2.get("git-server"), GitSource)
        assert isinstance(mgr2.get("npx-server"), NpxSource)
        assert isinstance(mgr2.get("uvx-server"), UvxSource)
        assert isinstance(mgr2.get("remote-server"), RemoteSource)
        assert isinstance(mgr2.get("unknown-server"), UnknownSource)

        git = mgr2.get("git-server")
        assert git.post_update == "uv sync"
        assert git.remote_url == "git@github.com:test/repo.git"
