"""
Tests for git utility functions.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcpm.utils.git import (
    check_status,
    fetch,
    get_default_branch,
    get_remote_url,
    is_dirty,
    is_git_repo,
    pull_ff_only,
    pull_rebase,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a real git repo for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), capture_output=True)

    # Create an initial commit
    (repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(repo), capture_output=True)
    return repo


@pytest.fixture
def git_repo_with_remote(tmp_path):
    """Create a git repo with a bare remote for testing fetch/pull."""
    # Create bare remote with explicit default branch to avoid master/main inconsistency across environments
    remote = tmp_path / "remote.git"
    remote.mkdir()
    subprocess.run(["git", "init", "--bare", "-b", "main"], cwd=str(remote), capture_output=True)

    # Create local repo cloned from the bare remote
    local = tmp_path / "local"
    subprocess.run(["git", "clone", str(remote), str(local)], capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(local), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(local), capture_output=True)

    # Create initial commit and push
    (local / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(local), capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(local), capture_output=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=str(local), capture_output=True)

    return local, remote


# --- is_git_repo ---


class TestIsGitRepo:
    def test_real_git_repo(self, git_repo):
        assert is_git_repo(git_repo) is True

    def test_not_a_git_repo(self, tmp_path):
        assert is_git_repo(tmp_path) is False

    def test_nonexistent_path(self, tmp_path):
        assert is_git_repo(tmp_path / "does-not-exist") is False


# --- get_remote_url ---


class TestGetRemoteUrl:
    def test_with_remote(self, git_repo_with_remote):
        local, remote = git_repo_with_remote
        url = get_remote_url(local)
        assert url is not None
        assert str(remote) in url

    def test_no_remote(self, git_repo):
        url = get_remote_url(git_repo)
        assert url is None


# --- get_default_branch ---


class TestGetDefaultBranch:
    def test_default_branch(self, git_repo_with_remote):
        local, _ = git_repo_with_remote
        branch = get_default_branch(local)
        assert branch in ("main", "master")

    def test_fallback_to_current(self, git_repo):
        # No remote, falls back to current branch
        branch = get_default_branch(git_repo)
        assert branch in ("main", "master")


# --- is_dirty ---


class TestIsDirty:
    def test_clean_repo(self, git_repo):
        assert is_dirty(git_repo) is False

    def test_dirty_repo(self, git_repo):
        (git_repo / "new_file.txt").write_text("dirty")
        assert is_dirty(git_repo) is True

    def test_staged_changes(self, git_repo):
        (git_repo / "staged.txt").write_text("staged")
        subprocess.run(["git", "add", "staged.txt"], cwd=str(git_repo), capture_output=True)
        assert is_dirty(git_repo) is True


# --- fetch ---


class TestFetch:
    def test_fetch_success(self, git_repo_with_remote):
        local, _ = git_repo_with_remote
        result = fetch(local)
        assert result.success is True

    def test_fetch_no_remote(self, git_repo):
        result = fetch(git_repo)
        assert result.success is False

    @patch("mcpm.utils.git._run_git")
    def test_fetch_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=30)
        result = fetch(Path("/fake/repo"))
        assert result.success is False
        assert "timed out" in result.error

    @patch("mcpm.utils.git._run_git")
    def test_fetch_ssh_auth_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="Permission denied (publickey).",
        )
        result = fetch(Path("/fake/repo"))
        assert result.success is False
        assert "SSH auth failed" in result.error


# --- check_status ---


class TestCheckStatus:
    def test_up_to_date(self, git_repo_with_remote):
        local, _ = git_repo_with_remote
        # Fetch first
        fetch(local)
        status = check_status(local)
        assert status.commits_behind == 0
        assert status.error is None

    def test_commits_behind(self, git_repo_with_remote):
        local, remote = git_repo_with_remote

        # Create a second clone, make a commit, push
        second = local.parent / "second"
        subprocess.run(["git", "clone", str(remote), str(second)], capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(second), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(second), capture_output=True)
        (second / "new.txt").write_text("new content")
        subprocess.run(["git", "add", "."], cwd=str(second), capture_output=True)
        subprocess.run(["git", "commit", "-m", "new commit"], cwd=str(second), capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(second), capture_output=True)

        # Now check the original local
        fetch(local)
        status = check_status(local)
        assert status.commits_behind == 1
        assert len(status.commit_summaries) == 1
        assert "new commit" in status.commit_summaries[0]


# --- pull_ff_only ---


class TestPullFfOnly:
    def test_pull_success(self, git_repo_with_remote):
        local, remote = git_repo_with_remote

        # Push from a second clone
        second = local.parent / "second"
        subprocess.run(["git", "clone", str(remote), str(second)], capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(second), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(second), capture_output=True)
        (second / "new.txt").write_text("new")
        subprocess.run(["git", "add", "."], cwd=str(second), capture_output=True)
        subprocess.run(["git", "commit", "-m", "new"], cwd=str(second), capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(second), capture_output=True)

        # Pull on the original
        fetch(local)
        result = pull_ff_only(local)
        assert result.success is True

    def test_pull_diverged(self, git_repo_with_remote):
        local, remote = git_repo_with_remote

        # Push from a second clone
        second = local.parent / "second"
        subprocess.run(["git", "clone", str(remote), str(second)], capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(second), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(second), capture_output=True)
        (second / "remote.txt").write_text("from remote")
        subprocess.run(["git", "add", "."], cwd=str(second), capture_output=True)
        subprocess.run(["git", "commit", "-m", "remote commit"], cwd=str(second), capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(second), capture_output=True)

        # Make a local commit (diverge)
        (local / "local.txt").write_text("from local")
        subprocess.run(["git", "add", "."], cwd=str(local), capture_output=True)
        subprocess.run(["git", "commit", "-m", "local commit"], cwd=str(local), capture_output=True)

        # Pull should fail with ff-only
        fetch(local)
        result = pull_ff_only(local)
        assert result.success is False
        assert "cannot fast-forward" in result.error or "pull" in result.error.lower()

    @patch("mcpm.utils.git._run_git")
    def test_pull_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=30)
        result = pull_ff_only(Path("/fake/repo"))
        assert result.success is False
        assert "timed out" in result.error


# --- pull_rebase ---


class TestPullRebase:
    def test_rebase_success(self, git_repo_with_remote):
        local, remote = git_repo_with_remote

        # Push from a second clone
        second = local.parent / "second"
        subprocess.run(["git", "clone", str(remote), str(second)], capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(second), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(second), capture_output=True)
        (second / "new.txt").write_text("new")
        subprocess.run(["git", "add", "."], cwd=str(second), capture_output=True)
        subprocess.run(["git", "commit", "-m", "new"], cwd=str(second), capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(second), capture_output=True)

        fetch(local)
        result = pull_rebase(local)
        assert result.success is True

    @patch("mcpm.utils.git._run_git")
    def test_rebase_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=30)
        result = pull_rebase(Path("/fake/repo"))
        assert result.success is False
        assert "timed out" in result.error
