from __future__ import annotations

import hashlib
import os

from src.git_ops import GitCommandError, run_git
from src.models import RepoChanges


def _parse_porcelain(status_text: str) -> list[str]:
    files: list[str] = []
    for line in status_text.splitlines():
        if not line.strip():
            continue
        # porcelain line format: XY <path>
        raw = line[3:] if len(line) >= 4 else line
        if " -> " in raw:
            raw = raw.split(" -> ", maxsplit=1)[1]
        files.append(raw.strip())
    return sorted(set(files))


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def detect_repo_changes(repo_path: str, max_diff_chars: int) -> RepoChanges | None:
    status_text = run_git(repo_path, ["status", "--porcelain"], timeout=20)
    changed_files = _parse_porcelain(status_text)
    if not changed_files:
        return None

    unstaged = run_git(repo_path, ["diff", "--no-color"], timeout=20)
    staged = run_git(repo_path, ["diff", "--no-color", "--cached"], timeout=20)
    untracked = run_git(repo_path, ["ls-files", "--others", "--exclude-standard"], timeout=20)

    diff_text = (
        "Changed files:\n"
        + "\n".join(changed_files)
        + "\n\nUnstaged diff:\n"
        + unstaged
        + "\n\nStaged diff:\n"
        + staged
        + "\n\nUntracked files:\n"
        + untracked
    )
    diff_text = _truncate(diff_text, max_diff_chars)

    hash_input = f"{status_text}\n{unstaged}\n{staged}\n{untracked}"
    change_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    return RepoChanges(changed_files=changed_files, diff_text=diff_text, change_hash=change_hash)


def get_repo_name(repo_path: str) -> str:
    return os.path.basename(repo_path.rstrip("/")) or repo_path


def has_changes(repo_path: str) -> bool:
    try:
        return bool(run_git(repo_path, ["status", "--porcelain"], timeout=20).strip())
    except GitCommandError:
        return False
