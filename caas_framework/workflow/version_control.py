"""
Version Control Integration

Integrates workflow state with Git for version tracking and collaboration.
"""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import ConfigLoader for timeout configuration
try:
    from caas_framework.config.loader import get_config_loader

    _has_config_loader = True
except ImportError:
    _has_config_loader = False


@dataclass
class GitCommit:
    """Git commit information"""

    commit_hash: str
    author: str
    date: datetime
    message: str
    files_changed: List[str] = field(default_factory=list)


@dataclass
class GitStatus:
    """Git repository status"""

    branch: str
    is_clean: bool
    modified_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    staged_files: List[str] = field(default_factory=list)


class GitIntegration:
    """
    Git Integration

    Features:
    - Auto-commit checkpoints
    - Branch-based workflow versioning
    - Diff generation
    - Rollback via Git
    - Collaboration support
    """

    def __init__(
        self,
        repo_path: str = ".",
        auto_commit: bool = False,
        commit_prefix: str = "[CAAS]",
    ):
        """
        Initialize Git integration.

        Args:
            repo_path: Path to Git repository
            auto_commit: Auto-commit on checkpoints
            commit_prefix: Prefix for auto-generated commits
        """
        self.repo_path = Path(repo_path)
        self.auto_commit = auto_commit
        self.commit_prefix = commit_prefix

        # Initialize config loader for timeouts
        self._config_loader = get_config_loader() if _has_config_loader else None

        # Check if Git is available
        self.git_available = self._check_git_available()

    def _get_timeout(self, timeout_type: str, default: float) -> float:
        """
        Get timeout value from config or use default

        Args:
            timeout_type: Type of timeout (git, commit, push, etc.)
            default: Default value if config not available

        Returns:
            Timeout in seconds
        """
        if self._config_loader:
            return self._config_loader.get_timeout(
                f"version_control_{timeout_type}", default=default
            )
        return default

        # Check if repo is initialized
        self.repo_initialized = self._check_repo_initialized()

    # ========== Git Availability ==========

    def _check_git_available(self) -> bool:
        """Check if Git is available"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=self._get_timeout("git", 5),
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # Git not found or timeout
            return False

    def _check_repo_initialized(self) -> bool:
        """Check if Git repo is initialized"""
        if not self.git_available:
            return False

        try:
            result = subprocess.run(
                ["git", "status"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("git", 5),
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # Repository not initialized or not accessible
            return False

    # ========== Repository Initialization ==========

    def init_repo(self) -> bool:
        """
        Initialize Git repository.

        Returns:
            bool: Success
        """
        if not self.git_available:
            return False

        if self.repo_initialized:
            return True  # Already initialized

        try:
            result = subprocess.run(
                ["git", "init"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("commit", 10),
            )

            if result.returncode == 0:
                self.repo_initialized = True

                # Create initial .gitignore for CAAS
                gitignore_path = self.repo_path / ".gitignore"
                if not gitignore_path.exists():
                    with open(gitignore_path, "w") as f:
                        f.write("# CAAS Framework\n")
                        f.write(".caas/cache/\n")
                        f.write("*.pyc\n")
                        f.write("__pycache__/\n")
                        f.write(".env\n")

                    # Add and commit .gitignore
                    self.commit_file(".gitignore", "Initialize CAAS repository")

                return True

            return False

        except (subprocess.TimeoutExpired, IOError, OSError):
            # Failed to initialize repository or create .gitignore
            return False

    # ========== Status & Info ==========

    def get_status(self) -> Optional[GitStatus]:
        """
        Get Git repository status.

        Returns:
            Optional[GitStatus]: Repository status
        """
        if not self.repo_initialized:
            return None

        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("git", 5),
            )
            branch = (
                branch_result.stdout.strip()
                if branch_result.returncode == 0
                else "unknown"
            )

            # Get status
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("commit", 10),
            )

            if status_result.returncode != 0:
                return None

            # Parse status output
            modified_files = []
            untracked_files = []
            staged_files = []

            for line in status_result.stdout.strip().split("\n"):
                if not line:
                    continue

                status_code = line[:2]
                filename = line[3:]

                if status_code[0] in ["M", "A", "D", "R", "C"]:
                    staged_files.append(filename)
                if status_code[1] == "M":
                    modified_files.append(filename)
                if status_code == "??":
                    untracked_files.append(filename)

            is_clean = not (modified_files or untracked_files or staged_files)

            return GitStatus(
                branch=branch,
                is_clean=is_clean,
                modified_files=modified_files,
                untracked_files=untracked_files,
                staged_files=staged_files,
            )

        except (subprocess.TimeoutExpired, OSError, ValueError):
            # Failed to get repository status or parse output
            return None

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash"""
        if not self.repo_initialized:
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("git", 5),
            )

            if result.returncode == 0:
                return result.stdout.strip()

            return None

        except (subprocess.TimeoutExpired, OSError):
            # Failed to get current commit
            return None

    def get_commit_history(self, max_count: int = 10) -> List[GitCommit]:
        """
        Get commit history.

        Args:
            max_count: Maximum number of commits to retrieve

        Returns:
            List[GitCommit]: Commit history
        """
        if not self.repo_initialized:
            return []

        try:
            result = subprocess.run(
                ["git", "log", f"-{max_count}", "--pretty=format:%H|%an|%ai|%s"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("commit", 10),
            )

            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) >= 4:
                    commit = GitCommit(
                        commit_hash=parts[0],
                        author=parts[1],
                        date=datetime.fromisoformat(parts[2].replace(" ", "T", 1)),
                        message=parts[3],
                    )
                    commits.append(commit)

            return commits

        except (subprocess.TimeoutExpired, OSError, ValueError):
            # Failed to get commit history or parse output
            return []

    # ========== Commit Operations ==========

    def commit_file(
        self, file_path: str, message: str, author: Optional[str] = None
    ) -> Optional[str]:
        """
        Commit a single file.

        Args:
            file_path: File to commit
            message: Commit message
            author: Commit author (optional)

        Returns:
            Optional[str]: Commit hash
        """
        if not self.repo_initialized:
            return None

        try:
            # Add file
            subprocess.run(
                ["git", "add", file_path],
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("commit", 10),
            )

            # Commit
            commit_cmd = ["git", "commit", "-m", f"{self.commit_prefix} {message}"]
            if author:
                commit_cmd.extend(["--author", author])

            result = subprocess.run(
                commit_cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("commit", 10),
            )

            if result.returncode == 0:
                return self.get_current_commit()

            return None

        except (subprocess.TimeoutExpired, OSError):
            # Failed to commit file
            return None

    def commit_all(
        self, message: str, include_untracked: bool = False
    ) -> Optional[str]:
        """
        Commit all changes.

        Args:
            message: Commit message
            include_untracked: Include untracked files

        Returns:
            Optional[str]: Commit hash
        """
        if not self.repo_initialized:
            return None

        try:
            # Add all files
            add_cmd = (
                ["git", "add", "-A"] if include_untracked else ["git", "add", "-u"]
            )
            subprocess.run(
                add_cmd,
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("commit", 10),
            )

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", f"{self.commit_prefix} {message}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("commit", 10),
            )

            if result.returncode == 0:
                return self.get_current_commit()

            return None

        except (subprocess.TimeoutExpired, OSError):
            # Failed to commit all changes
            return None

    def commit_checkpoint(
        self, checkpoint_id: str, phase: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Commit a checkpoint to Git.

        Args:
            checkpoint_id: Checkpoint ID
            phase: Workflow phase
            metadata: Additional metadata

        Returns:
            Optional[str]: Commit hash
        """
        message = f"Checkpoint: {checkpoint_id} (Phase: {phase})"

        if metadata:
            message += f" - {metadata}"

        return self.commit_all(message, include_untracked=True)

    # ========== Branch Operations ==========

    def create_branch(
        self, branch_name: str, from_commit: Optional[str] = None
    ) -> bool:
        """
        Create a new branch.

        Args:
            branch_name: Branch name
            from_commit: Commit to branch from (optional, defaults to HEAD)

        Returns:
            bool: Success
        """
        if not self.repo_initialized:
            return False

        try:
            cmd = ["git", "branch", branch_name]
            if from_commit:
                cmd.append(from_commit)

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("commit", 10),
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, OSError):
            # Failed to create branch
            return False

    def switch_branch(self, branch_name: str, create_if_missing: bool = False) -> bool:
        """
        Switch to a different branch.

        Args:
            branch_name: Branch to switch to
            create_if_missing: Create branch if it doesn't exist

        Returns:
            bool: Success
        """
        if not self.repo_initialized:
            return False

        try:
            cmd = ["git", "checkout"]
            if create_if_missing:
                cmd.append("-b")
            cmd.append(branch_name)

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("commit", 10),
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, OSError):
            # Failed to switch branch
            return False

    def list_branches(self) -> List[str]:
        """List all branches"""
        if not self.repo_initialized:
            return []

        try:
            result = subprocess.run(
                ["git", "branch", "--list"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("git", 5),
            )

            if result.returncode != 0:
                return []

            branches = []
            for line in result.stdout.strip().split("\n"):
                # Remove * for current branch
                branch = line.strip().lstrip("* ")
                if branch:
                    branches.append(branch)

            return branches

        except (subprocess.TimeoutExpired, OSError):
            # Failed to list branches
            return []

    # ========== Rollback Operations ==========

    def rollback_to_commit(self, commit_hash: str, hard: bool = False) -> bool:
        """
        Rollback to a specific commit.

        Args:
            commit_hash: Commit to rollback to
            hard: Hard reset (destroys uncommitted changes)

        Returns:
            bool: Success
        """
        if not self.repo_initialized:
            return False

        try:
            reset_type = "--hard" if hard else "--soft"

            result = subprocess.run(
                ["git", "reset", reset_type, commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("commit", 10),
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, OSError):
            # Failed to rollback to commit
            return False

    def get_diff(
        self,
        from_commit: Optional[str] = None,
        to_commit: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get diff between commits.

        Args:
            from_commit: Source commit (default: HEAD)
            to_commit: Target commit (default: working tree)
            file_path: Specific file to diff

        Returns:
            Optional[str]: Diff output
        """
        if not self.repo_initialized:
            return None

        try:
            cmd = ["git", "diff"]

            if from_commit:
                cmd.append(from_commit)
            if to_commit:
                cmd.append(to_commit)
            if file_path:
                cmd.extend(["--", file_path])

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("commit", 15),
            )

            if result.returncode == 0:
                return result.stdout

            return None

        except (subprocess.TimeoutExpired, OSError):
            # Failed to get diff
            return None

    # ========== Tag Operations ==========

    def create_tag(
        self, tag_name: str, message: Optional[str] = None, commit: Optional[str] = None
    ) -> bool:
        """
        Create a Git tag.

        Args:
            tag_name: Tag name
            message: Tag message (creates annotated tag)
            commit: Commit to tag (default: HEAD)

        Returns:
            bool: Success
        """
        if not self.repo_initialized:
            return False

        try:
            cmd = ["git", "tag"]

            if message:
                cmd.extend(["-a", tag_name, "-m", message])
            else:
                cmd.append(tag_name)

            if commit:
                cmd.append(commit)

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("commit", 10),
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, OSError):
            # Failed to create tag
            return False

    def list_tags(self) -> List[str]:
        """List all tags"""
        if not self.repo_initialized:
            return []

        try:
            result = subprocess.run(
                ["git", "tag", "--list"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self._get_timeout("git", 5),
            )

            if result.returncode != 0:
                return []

            return [
                tag.strip() for tag in result.stdout.strip().split("\n") if tag.strip()
            ]

        except (subprocess.TimeoutExpired, OSError):
            # Failed to list tags
            return []

    # ========== Remote Operations ==========

    def add_remote(self, name: str, url: str) -> bool:
        """Add a remote repository"""
        if not self.repo_initialized:
            return False

        try:
            result = subprocess.run(
                ["git", "remote", "add", name, url],
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("commit", 10),
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, OSError):
            # Failed to add remote
            return False

    def push(
        self, remote: str = "origin", branch: Optional[str] = None, tags: bool = False
    ) -> bool:
        """
        Push to remote repository.

        Args:
            remote: Remote name
            branch: Branch to push (default: current)
            tags: Push tags

        Returns:
            bool: Success
        """
        if not self.repo_initialized:
            return False

        try:
            cmd = ["git", "push", remote]

            if branch:
                cmd.append(branch)

            if tags:
                cmd.append("--tags")

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("push", 30),
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, OSError):
            # Failed to push to remote
            return False

    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """
        Pull from remote repository.

        Args:
            remote: Remote name
            branch: Branch to pull (default: current)

        Returns:
            bool: Success
        """
        if not self.repo_initialized:
            return False

        try:
            cmd = ["git", "pull", remote]

            if branch:
                cmd.append(branch)

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                timeout=self._get_timeout("push", 30),
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, OSError):
            # Failed to pull from remote
            return False

    # ========== Utilities ==========

    def is_clean(self) -> bool:
        """Check if working tree is clean"""
        status = self.get_status()
        return status.is_clean if status else False

    def get_repository_info(self) -> Dict[str, Any]:
        """Get comprehensive repository information"""
        if not self.repo_initialized:
            return {"initialized": False, "git_available": self.git_available}

        status = self.get_status()
        current_commit = self.get_current_commit()
        branches = self.list_branches()
        tags = self.list_tags()

        return {
            "initialized": True,
            "git_available": self.git_available,
            "branch": status.branch if status else None,
            "is_clean": status.is_clean if status else False,
            "current_commit": current_commit,
            "branches": branches,
            "tags": tags,
            "modified_files": status.modified_files if status else [],
            "untracked_files": status.untracked_files if status else [],
        }
