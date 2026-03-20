"""
Tests for the mcpm update command.
"""

from unittest.mock import Mock

from click.testing import CliRunner

from mcpm.commands.new import new
from mcpm.commands.uninstall import uninstall
from mcpm.commands.update import update
from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig
from mcpm.core.source import GitSource, NpxSource, RemoteSource, SourcesManager, UnknownSource

# --- CLI tests ---


class TestUpdateCommand:
    """Test the update command CLI interface."""

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(update, ["--help"])
        assert result.exit_code == 0
        assert "Check for and apply updates" in result.output
        assert "--check" in result.output
        assert "--rebase" in result.output
        assert "--init" in result.output

    def test_no_servers(self, monkeypatch):
        mock_global = Mock()
        mock_global.list_servers.return_value = {}
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: Mock(list_all=Mock(return_value={})))

        runner = CliRunner()
        result = runner.invoke(update, [])
        assert "No servers found" in result.output

    def test_server_not_found(self, monkeypatch):
        mock_global = Mock()
        mock_global.list_servers.return_value = {"other-server": Mock()}
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        runner = CliRunner()
        result = runner.invoke(update, ["nonexistent"])
        assert "not found" in result.output

    def test_check_npx_servers(self, monkeypatch, tmp_path):
        """Test that npx servers show informational message."""
        sources_path = tmp_path / "sources.json"

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "context7": STDIOServerConfig(name="context7", command="npx", args=["-y", "@upstash/context7-mcp"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        # Pre-populate sources
        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("context7", NpxSource(package="@upstash/context7-mcp"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        runner = CliRunner()
        result = runner.invoke(update, ["--check"])
        assert "auto-updates via npx" in result.output

    def test_check_remote_servers(self, monkeypatch, tmp_path):
        """Test that remote servers are skipped."""
        sources_path = tmp_path / "sources.json"

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "clickup": RemoteServerConfig(name="clickup", url="https://mcp.clickup.com/mcp"),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("clickup", RemoteSource())
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        runner = CliRunner()
        result = runner.invoke(update, ["--check"])
        assert "skipped" in result.output

    def test_check_no_source_metadata(self, monkeypatch, tmp_path):
        """Test warning when source metadata is missing."""
        sources_path = tmp_path / "sources.json"

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "mystery": STDIOServerConfig(name="mystery", command="some-cmd"),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        runner = CliRunner()
        result = runner.invoke(update, ["--check"])
        assert "mcpm update" in result.output and "init" in result.output

    def test_check_git_up_to_date(self, monkeypatch, tmp_path):
        """Test git server that is up to date."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "my-server": STDIOServerConfig(name="my-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("my-server", GitSource(path=str(repo_dir), branch="main"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        # Mock git operations
        from mcpm.utils.git import GitResult, GitStatus

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: False)
        monkeypatch.setattr("mcpm.commands.update.git_utils.fetch", lambda p: GitResult(success=True))
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.check_status",
            lambda p, branch=None: GitStatus(commits_behind=0),
        )

        runner = CliRunner()
        result = runner.invoke(update, ["--check"])
        assert "up to date" in result.output

    def test_check_git_has_updates(self, monkeypatch, tmp_path):
        """Test git server with available updates."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "my-server": STDIOServerConfig(name="my-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("my-server", GitSource(path=str(repo_dir), branch="main"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        from mcpm.utils.git import GitResult, GitStatus

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: False)
        monkeypatch.setattr("mcpm.commands.update.git_utils.fetch", lambda p: GitResult(success=True))
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.check_status",
            lambda p, branch=None: GitStatus(
                commits_behind=2,
                commit_summaries=["abc123 fix bug", "def456 add feature"],
                remote_branch="origin/main",
            ),
        )

        runner = CliRunner()
        result = runner.invoke(update, ["--check", "--verbose"])
        assert "2 commits behind" in result.output
        assert "fix bug" in result.output
        assert "add feature" in result.output
        assert "1 server(s) have updates available" in result.output

    def test_check_git_dirty_skipped(self, monkeypatch, tmp_path):
        """Test that dirty git repos are skipped."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "dirty-server": STDIOServerConfig(name="dirty-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("dirty-server", GitSource(path=str(repo_dir), branch="main"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: True)

        runner = CliRunner()
        result = runner.invoke(update, ["--check"])
        assert "uncommitted changes" in result.output

    def test_check_git_fetch_fails(self, monkeypatch, tmp_path):
        """Test that fetch failures are handled gracefully."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "ssh-server": STDIOServerConfig(name="ssh-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("ssh-server", GitSource(path=str(repo_dir), branch="main"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        from mcpm.utils.git import GitResult

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: False)
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.fetch",
            lambda p: GitResult(success=False, error="SSH auth failed — is your SSH agent running?"),
        )

        runner = CliRunner()
        result = runner.invoke(update, ["--check"])
        assert "SSH auth failed" in result.output

    def test_check_git_path_not_found(self, monkeypatch, tmp_path):
        """Test that missing paths are reported."""
        sources_path = tmp_path / "sources.json"

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "gone-server": STDIOServerConfig(name="gone-server", command="node", args=["/gone/dist/index.js"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("gone-server", GitSource(path="/nonexistent/path"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        runner = CliRunner()
        result = runner.invoke(update, ["--check"])
        assert "path not found" in result.output


# --- Init tests ---


class TestUpdateInit:
    """Test the --init flag."""

    def test_init_detects_servers(self, monkeypatch, tmp_path):
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        (repo_dir / "pyproject.toml").touch()
        (repo_dir / "uv.lock").touch()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "npx-server": STDIOServerConfig(name="npx-server", command="npx", args=["@test/mcp"]),
            "remote-server": RemoteServerConfig(name="remote-server", url="https://example.com"),
            "git-server": STDIOServerConfig(name="git-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "test"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: SourcesManager(sources_path=sources_path))

        # Mock git operations for the git server
        monkeypatch.setattr("mcpm.commands.update.git_utils.is_git_repo", lambda p: True)
        monkeypatch.setattr("mcpm.commands.update.git_utils.get_remote_url", lambda p: "git@github.com:test/repo.git")
        monkeypatch.setattr("mcpm.commands.update.git_utils.get_default_branch", lambda p: "main")

        # Force non-interactive
        monkeypatch.setattr("mcpm.commands.update.is_non_interactive", lambda: True)

        runner = CliRunner()
        result = runner.invoke(update, ["--init"])
        assert "3 created" in result.output

        # Verify saved data
        mgr = SourcesManager(sources_path=sources_path)
        assert isinstance(mgr.get("npx-server"), NpxSource)
        assert isinstance(mgr.get("remote-server"), RemoteSource)

        git_source = mgr.get("git-server")
        assert isinstance(git_source, GitSource)
        assert git_source.path == str(repo_dir)
        assert git_source.post_update == "uv sync"

    def test_init_skips_existing(self, monkeypatch, tmp_path):
        sources_path = tmp_path / "sources.json"

        # Pre-populate
        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("existing", NpxSource(package="@test/existing"))

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "existing": STDIOServerConfig(name="existing", command="npx", args=["@test/existing"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: SourcesManager(sources_path=sources_path))

        runner = CliRunner()
        result = runner.invoke(update, ["--init"])
        assert "0 created" in result.output
        assert "1 skipped" in result.output

    def test_init_force_overwrites(self, monkeypatch, tmp_path):
        sources_path = tmp_path / "sources.json"

        # Pre-populate
        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("existing", UnknownSource(reason="was broken"))

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "existing": STDIOServerConfig(name="existing", command="npx", args=["@test/existing"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: SourcesManager(sources_path=sources_path))

        runner = CliRunner()
        result = runner.invoke(update, ["--init", "--force"])
        assert "1 updated" in result.output

        mgr2 = SourcesManager(sources_path=sources_path)
        assert isinstance(mgr2.get("existing"), NpxSource)


# --- Apply (full pull) tests ---


class TestUpdateApply:
    """Test the full update apply flow (pull + post_update)."""

    def test_apply_git_ff_only(self, monkeypatch, tmp_path):
        """Test applying a git update with --ff-only (default)."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "my-server": STDIOServerConfig(name="my-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("my-server", GitSource(path=str(repo_dir), branch="main"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        from mcpm.utils.git import GitResult, GitStatus

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: False)
        monkeypatch.setattr("mcpm.commands.update.git_utils.fetch", lambda p: GitResult(success=True))
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.check_status",
            lambda p, branch=None: GitStatus(commits_behind=2, commit_summaries=["a fix", "b feat"], remote_branch="origin/main"),
        )
        monkeypatch.setattr("mcpm.commands.update.git_utils.pull_ff_only", lambda p: GitResult(success=True, message="ok"))

        runner = CliRunner()
        result = runner.invoke(update, ["--force"])
        assert "2 new commits" in result.output
        assert "1 server(s) updated" in result.output

    def test_apply_git_rebase(self, monkeypatch, tmp_path):
        """Test applying a git update with --rebase."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "my-server": STDIOServerConfig(name="my-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("my-server", GitSource(path=str(repo_dir), branch="main"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        from mcpm.utils.git import GitResult, GitStatus

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: False)
        monkeypatch.setattr("mcpm.commands.update.git_utils.fetch", lambda p: GitResult(success=True))
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.check_status",
            lambda p, branch=None: GitStatus(commits_behind=1, commit_summaries=["a fix"], remote_branch="origin/main"),
        )
        monkeypatch.setattr("mcpm.commands.update.git_utils.pull_rebase", lambda p: GitResult(success=True, message="ok"))

        runner = CliRunner()
        result = runner.invoke(update, ["--rebase", "--force"])
        assert "1 new commit" in result.output
        assert "1 server(s) updated" in result.output

    def test_apply_with_post_update_success(self, monkeypatch, tmp_path):
        """Test that post_update command runs after pull."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "my-server": STDIOServerConfig(name="my-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("my-server", GitSource(path=str(repo_dir), branch="main", post_update="echo done"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        from mcpm.utils.git import GitResult, GitStatus

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: False)
        monkeypatch.setattr("mcpm.commands.update.git_utils.fetch", lambda p: GitResult(success=True))
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.check_status",
            lambda p, branch=None: GitStatus(commits_behind=1, commit_summaries=["fix"], remote_branch="origin/main"),
        )
        monkeypatch.setattr("mcpm.commands.update.git_utils.pull_ff_only", lambda p: GitResult(success=True))

        runner = CliRunner()
        result = runner.invoke(update, ["--force"])
        assert "echo done" in result.output
        assert "1 server(s) updated" in result.output

    def test_apply_with_post_update_failure(self, monkeypatch, tmp_path):
        """Test that post_update failure prevents counting as successful update."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "my-server": STDIOServerConfig(name="my-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("my-server", GitSource(path=str(repo_dir), branch="main", post_update="false"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        from mcpm.utils.git import GitResult, GitStatus

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: False)
        monkeypatch.setattr("mcpm.commands.update.git_utils.fetch", lambda p: GitResult(success=True))
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.check_status",
            lambda p, branch=None: GitStatus(commits_behind=1, commit_summaries=["fix"], remote_branch="origin/main"),
        )
        monkeypatch.setattr("mcpm.commands.update.git_utils.pull_ff_only", lambda p: GitResult(success=True))

        runner = CliRunner()
        result = runner.invoke(update, ["--force"])
        # Post-update failed — not counted as successful update
        assert "0 server(s) updated" in result.output

    def test_apply_pull_fails(self, monkeypatch, tmp_path):
        """Test that a failed pull is reported and not counted."""
        sources_path = tmp_path / "sources.json"
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        mock_global = Mock()
        mock_global.list_servers.return_value = {
            "my-server": STDIOServerConfig(name="my-server", command="uv", args=["run", "--directory", str(repo_dir), "python", "-m", "server"]),
        }
        monkeypatch.setattr("mcpm.commands.update.GlobalConfigManager", lambda: mock_global)

        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("my-server", GitSource(path=str(repo_dir), branch="main"))
        monkeypatch.setattr("mcpm.commands.update.SourcesManager", lambda: mgr)

        from mcpm.utils.git import GitResult, GitStatus

        monkeypatch.setattr("mcpm.commands.update.git_utils.is_dirty", lambda p: False)
        monkeypatch.setattr("mcpm.commands.update.git_utils.fetch", lambda p: GitResult(success=True))
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.check_status",
            lambda p, branch=None: GitStatus(commits_behind=1, commit_summaries=["fix"], remote_branch="origin/main"),
        )
        monkeypatch.setattr(
            "mcpm.commands.update.git_utils.pull_ff_only",
            lambda p: GitResult(success=False, error="cannot fast-forward — local and remote have diverged"),
        )

        runner = CliRunner()
        result = runner.invoke(update, ["--force"])
        assert "cannot fast-forward" in result.output
        assert "0 server(s) updated" in result.output


# --- Hook tests (mcpm new / mcpm uninstall) ---


class TestSourceHooks:
    """Test that mcpm new and mcpm uninstall manage source metadata."""

    def test_new_populates_source(self, monkeypatch, tmp_path):
        """Test that mcpm new auto-populates source metadata."""
        sources_path = tmp_path / "sources.json"

        mock_global = Mock()
        mock_global.get_server.return_value = None
        mock_global.add_server.return_value = None
        monkeypatch.setattr("mcpm.commands.new.global_config_manager", mock_global)
        monkeypatch.setattr("mcpm.commands.new.is_non_interactive", lambda: True)
        monkeypatch.setattr("mcpm.commands.new.SourcesManager", lambda: SourcesManager(sources_path=sources_path))

        runner = CliRunner()
        result = runner.invoke(new, [
            "test-npx",
            "--type", "stdio",
            "--command", "npx",
            "--args", "@test/mcp-server",
        ])

        assert result.exit_code == 0
        mgr = SourcesManager(sources_path=sources_path)
        source = mgr.get("test-npx")
        assert isinstance(source, NpxSource)
        assert source.package == "@test/mcp-server"

    def test_new_populates_remote_source(self, monkeypatch, tmp_path):
        """Test that mcpm new for a remote server populates source metadata."""
        sources_path = tmp_path / "sources.json"

        mock_global = Mock()
        mock_global.get_server.return_value = None
        mock_global.add_server.return_value = None
        monkeypatch.setattr("mcpm.commands.new.global_config_manager", mock_global)
        monkeypatch.setattr("mcpm.commands.new.is_non_interactive", lambda: True)
        monkeypatch.setattr("mcpm.commands.new.SourcesManager", lambda: SourcesManager(sources_path=sources_path))

        runner = CliRunner()
        result = runner.invoke(new, [
            "test-remote",
            "--type", "remote",
            "--url", "https://example.com/mcp",
        ])

        assert result.exit_code == 0
        mgr = SourcesManager(sources_path=sources_path)
        source = mgr.get("test-remote")
        assert isinstance(source, RemoteSource)

    def test_uninstall_cleans_source(self, monkeypatch, tmp_path):
        """Test that mcpm uninstall removes source metadata."""
        sources_path = tmp_path / "sources.json"

        # Pre-populate source
        mgr = SourcesManager(sources_path=sources_path)
        mgr.set("doomed-server", NpxSource(package="@test/doomed"))

        # Mock global config
        mock_server = Mock()
        mock_server.name = "doomed-server"

        mock_global = Mock()
        mock_global.get_server.return_value = mock_server
        mock_global.server_exists.return_value = True
        mock_global.remove_server.return_value = True
        monkeypatch.setattr("mcpm.commands.uninstall.global_config_manager", mock_global)
        monkeypatch.setattr("mcpm.commands.uninstall.SourcesManager", lambda: SourcesManager(sources_path=sources_path))

        runner = CliRunner()
        result = runner.invoke(uninstall, ["doomed-server", "--force"])

        assert "Successfully removed" in result.output

        # Source metadata should be gone
        mgr2 = SourcesManager(sources_path=sources_path)
        assert mgr2.get("doomed-server") is None
