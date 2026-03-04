from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Config:
    openrouter_api_key: str
    openrouter_model: str
    repos_root: str
    scan_interval_minutes: int
    branch_allowlist: list[str]
    git_author_name: str
    git_author_email: str
    commit_policy: str
    run_tests_cmd: str
    max_diff_chars: int
    state_db_path: str
    log_level: str
    health_port: int
    repo_timeout_seconds: int


@dataclass(frozen=True)
class RepoChanges:
    changed_files: list[str]
    diff_text: str
    change_hash: str


@dataclass(frozen=True)
class RepoResult:
    repo_path: str
    branch: str
    change_hash: str
    action: str
    status: str
    commit_sha: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class RunSummary:
    started_at: datetime
    finished_at: datetime
    status: str
    repos_scanned: int
    repos_committed: int
    repos_failed: int
