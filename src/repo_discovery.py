from __future__ import annotations

from pathlib import Path


def discover_git_repos(root: str) -> list[str]:
    root_path = Path(root)
    if not root_path.exists() or not root_path.is_dir():
        return []

    repos: list[str] = []
    for git_dir in root_path.rglob(".git"):
        if git_dir.is_dir():
            repos.append(str(git_dir.parent.resolve()))
    repos.sort()
    return repos
