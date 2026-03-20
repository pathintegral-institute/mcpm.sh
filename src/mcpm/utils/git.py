"""
Git operations for mcpm update.

All git interactions go through subprocess with timeouts and proper error handling.
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

GIT_TIMEOUT = 30  # seconds


@dataclass
class GitStatus:
    """Result of checking a git repo's update status."""

    is_dirty: bool = False
    commits_behind: int = 0
    commit_summaries: List[str] = None  # One-line summaries of commits we're behind
    current_branch: str = ""
    remote_branch: str = ""
    error: Optional[str] = None

    def __post_init__(self):
        if self.commit_summaries is None:
            self.commit_summaries = []


@dataclass
class GitResult:
    """Result of a git operation."""

    success: bool
    message: str = ""
    error: Optional[str] = None


def _run_git(repo_path: Path, args: List[str], timeout: int = GIT_TIMEOUT) -> subprocess.CompletedProcess:
    """Run a git command in the given repo path."""
    cmd = ["git", "-C", str(repo_path)] + args
    logger.debug(f"Running: {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def is_git_repo(path: Path) -> bool:
    """Check if a path is inside a git repository."""
    try:
        result = _run_git(path, ["rev-parse", "--is-inside-work-tree"], timeout=5)
        return result.returncode == 0 and result.stdout.strip() == "true"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_remote_url(repo_path: Path, remote: str = "origin") -> Optional[str]:
    """Get the URL of a git remote."""
    try:
        result = _run_git(repo_path, ["remote", "get-url", remote], timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_default_branch(repo_path: Path, remote: str = "origin") -> Optional[str]:
    """Get the default branch name for a remote."""
    try:
        # Try to get from remote HEAD reference
        result = _run_git(repo_path, ["symbolic-ref", f"refs/remotes/{remote}/HEAD", "--short"], timeout=5)
        if result.returncode == 0:
            # Returns e.g. "origin/main" — strip the remote prefix
            ref = result.stdout.strip()
            return ref.replace(f"{remote}/", "", 1)

        # Fallback: check current branch
        result = _run_git(repo_path, ["branch", "--show-current"], timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def is_dirty(repo_path: Path) -> bool:
    """Check if the working tree has uncommitted changes."""
    try:
        result = _run_git(repo_path, ["status", "--porcelain"], timeout=5)
        return result.returncode != 0 or bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True  # Assume dirty if we can't check


def fetch(repo_path: Path, remote: str = "origin") -> GitResult:
    """Fetch from remote. Returns result with error details if it fails."""
    try:
        result = _run_git(repo_path, ["fetch", remote], timeout=GIT_TIMEOUT)
        if result.returncode == 0:
            return GitResult(success=True)

        stderr = result.stderr.strip()
        # Detect common SSH auth failures
        if any(phrase in stderr.lower() for phrase in ["permission denied", "could not read from remote", "host key"]):
            return GitResult(success=False, error="SSH auth failed — is your SSH agent running?")
        return GitResult(success=False, error=f"git fetch failed: {stderr}")

    except subprocess.TimeoutExpired:
        return GitResult(success=False, error=f"git fetch timed out after {GIT_TIMEOUT}s")
    except FileNotFoundError:
        return GitResult(success=False, error="git not found on PATH")


def check_status(repo_path: Path, branch: Optional[str] = None, remote: str = "origin") -> GitStatus:
    """Check how many commits behind we are from the remote."""
    if not branch:
        branch = get_default_branch(repo_path, remote) or "main"

    status = GitStatus(current_branch=branch, remote_branch=f"{remote}/{branch}")

    # Check dirty
    status.is_dirty = is_dirty(repo_path)

    # Count commits behind
    try:
        result = _run_git(repo_path, ["rev-list", "--count", f"HEAD..{remote}/{branch}"], timeout=5)
        if result.returncode == 0:
            status.commits_behind = int(result.stdout.strip())
        else:
            status.error = f"Could not compare with {remote}/{branch}: {result.stderr.strip()}"
            return status
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
        status.error = str(e)
        return status

    # Get commit summaries if behind
    if status.commits_behind > 0:
        try:
            result = _run_git(
                repo_path, ["log", "--oneline", f"HEAD..{remote}/{branch}", "--reverse"], timeout=5
            )
            if result.returncode == 0:
                status.commit_summaries = [line for line in result.stdout.strip().split("\n") if line]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return status


def pull_ff_only(repo_path: Path) -> GitResult:
    """Pull with --ff-only. Safe — either succeeds cleanly or fails explicitly."""
    try:
        result = _run_git(repo_path, ["pull", "--ff-only"], timeout=GIT_TIMEOUT)
        if result.returncode == 0:
            return GitResult(success=True, message=result.stdout.strip())

        stderr = result.stderr.strip()
        if "not possible to fast-forward" in stderr.lower() or "fatal: not possible" in stderr.lower():
            return GitResult(
                success=False,
                error="cannot fast-forward — local and remote have diverged",
            )
        return GitResult(success=False, error=f"git pull --ff-only failed: {stderr}")

    except subprocess.TimeoutExpired:
        return GitResult(success=False, error=f"git pull timed out after {GIT_TIMEOUT}s")
    except FileNotFoundError:
        return GitResult(success=False, error="git not found on PATH")


def pull_rebase(repo_path: Path) -> GitResult:
    """Pull with --rebase. Rewrites local commits on top of upstream."""
    try:
        result = _run_git(repo_path, ["pull", "--rebase"], timeout=GIT_TIMEOUT)
        if result.returncode == 0:
            return GitResult(success=True, message=result.stdout.strip())

        stderr = result.stderr.strip()
        # If rebase fails with conflicts, abort it to leave the repo clean
        if "conflict" in stderr.lower() or "could not apply" in stderr.lower():
            _run_git(repo_path, ["rebase", "--abort"], timeout=5)
            return GitResult(
                success=False,
                error="rebase failed due to conflicts (aborted automatically)",
            )
        return GitResult(success=False, error=f"git pull --rebase failed: {stderr}")

    except subprocess.TimeoutExpired:
        # Try to abort any in-progress rebase
        try:
            _run_git(repo_path, ["rebase", "--abort"], timeout=5)
        except Exception:
            pass
        return GitResult(success=False, error=f"git pull --rebase timed out after {GIT_TIMEOUT}s")
    except FileNotFoundError:
        return GitResult(success=False, error="git not found on PATH")
