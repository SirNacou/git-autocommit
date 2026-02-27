from __future__ import annotations

import fnmatch
import subprocess

from src.git_ops import GitCommandError, get_current_branch, has_merge_conflicts, has_upstream


def branch_allowed(branch: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    for pattern in patterns:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False


def check_safe_mode(repo_path: str, branch_patterns: list[str], run_tests_cmd: str) -> tuple[bool, str]:
    try:
        branch = get_current_branch(repo_path)
    except GitCommandError:
        return False, "detached HEAD"

    if not branch_allowed(branch, branch_patterns):
        return False, f"branch '{branch}' not allowed"

    if has_merge_conflicts(repo_path):
        return False, "merge conflicts detected"

    if not has_upstream(repo_path):
        return False, "missing upstream tracking branch"

    if run_tests_cmd.strip():
        try:
            result = subprocess.run(
                run_tests_cmd,
                cwd=repo_path,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "test command timed out"
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            return False, f"test command failed: {stderr[:400]}"

    return True, "ok"
