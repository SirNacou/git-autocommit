from __future__ import annotations

import os
import subprocess
from typing import Optional


class GitCommandError(RuntimeError):
    pass


def add_safe_directory(path: str) -> None:
    # Mounted host repos often have different UID/GID inside containers.
    subprocess.run(
        ["git", "config", "--global", "--add", "safe.directory", path],
        capture_output=True,
        text=True,
        check=False,
    )


def run_git(
    repo_path: str,
    args: list[str],
    *,
    timeout: int = 30,
    env: Optional[dict[str, str]] = None,
) -> str:
    cmd = ["git", *args]
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    result = subprocess.run(
        cmd,
        cwd=repo_path,
        env=merged_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise GitCommandError(f"{' '.join(cmd)} failed: {stderr}")
    return result.stdout.strip()


def is_git_repo(path: str) -> bool:
    try:
        run_git(path, ["rev-parse", "--is-inside-work-tree"], timeout=15)
        return True
    except (GitCommandError, subprocess.TimeoutExpired):
        return False


def get_current_branch(repo_path: str) -> str:
    return run_git(repo_path, ["symbolic-ref", "--short", "-q", "HEAD"], timeout=15)


def has_merge_conflicts(repo_path: str) -> bool:
    out = run_git(repo_path, ["diff", "--name-only", "--diff-filter=U"], timeout=15)
    return bool(out.strip())


def has_upstream(repo_path: str) -> bool:
    try:
        run_git(
            repo_path,
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            timeout=15,
        )
        return True
    except GitCommandError:
        return False


def stage_all(repo_path: str) -> None:
    run_git(repo_path, ["add", "-A"], timeout=30)


def create_commit(
    repo_path: str, message: str, author_name: str, author_email: str
) -> str:
    env = {
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
    }
    run_git(repo_path, ["commit", "-m", message], timeout=30, env=env)
    return run_git(repo_path, ["rev-parse", "HEAD"], timeout=10)
