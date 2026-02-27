from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models import RepoResult, RunSummary


class StateStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    repos_scanned INTEGER NOT NULL DEFAULT 0,
                    repos_committed INTEGER NOT NULL DEFAULT 0,
                    repos_failed INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS repo_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    repo_path TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    change_hash TEXT,
                    action TEXT NOT NULL,
                    commit_sha TEXT,
                    status TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );

                CREATE TABLE IF NOT EXISTS repo_state (
                    repo_path TEXT PRIMARY KEY,
                    last_change_hash TEXT,
                    last_commit_sha TEXT,
                    last_success_at TEXT
                );
                """
            )

    def start_run(self, started_at: datetime) -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO runs (started_at, status, repos_scanned, repos_committed, repos_failed)
                VALUES (?, ?, 0, 0, 0)
                """,
                (started_at.isoformat(), "running"),
            )
            return int(cur.lastrowid)

    def finish_run(self, run_id: int, summary: RunSummary) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET finished_at = ?, status = ?, repos_scanned = ?, repos_committed = ?, repos_failed = ?
                WHERE id = ?
                """,
                (
                    summary.finished_at.isoformat(),
                    summary.status,
                    summary.repos_scanned,
                    summary.repos_committed,
                    summary.repos_failed,
                    run_id,
                ),
            )

    def record_repo_result(self, run_id: int, result: RepoResult) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO repo_runs (run_id, repo_path, branch, change_hash, action, commit_sha, status, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    result.repo_path,
                    result.branch,
                    result.change_hash,
                    result.action,
                    result.commit_sha,
                    result.status,
                    result.error,
                ),
            )
            if result.status == "success" and result.action == "committed":
                conn.execute(
                    """
                    INSERT INTO repo_state (repo_path, last_change_hash, last_commit_sha, last_success_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(repo_path) DO UPDATE SET
                        last_change_hash = excluded.last_change_hash,
                        last_commit_sha = excluded.last_commit_sha,
                        last_success_at = excluded.last_success_at
                    """,
                    (
                        result.repo_path,
                        result.change_hash,
                        result.commit_sha,
                        datetime.utcnow().isoformat(),
                    ),
                )

    def last_change_hash(self, repo_path: str) -> Optional[str]:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT last_change_hash FROM repo_state WHERE repo_path = ?",
                (repo_path,),
            )
            row = cur.fetchone()
            return row[0] if row else None
