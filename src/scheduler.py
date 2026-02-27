from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from src.ai_commit_message import (
    build_prompt,
    fallback_message,
    generate_commit_message,
    normalize_message,
)
from src.change_detector import detect_repo_changes, get_repo_name
from src.git_ops import (
    add_safe_directory,
    GitCommandError,
    create_commit,
    get_current_branch,
    is_git_repo,
    push_current_branch,
    stage_all,
)
from src.models import Config, RepoResult, RunSummary
from src.policy_engine import check_safe_mode
from src.repo_discovery import discover_git_repos
from src.state_store import StateStore


class AutoCommitScheduler:
    def __init__(self, config: Config, state_store: StateStore) -> None:
        self.config = config
        self.state_store = state_store
        self.logger = logging.getLogger(__name__)

    def run_cycle(self) -> None:
        started_at = datetime.utcnow()
        run_id = self.state_store.start_run(started_at)
        repos = discover_git_repos(self.config.repos_root)
        repos_committed = 0
        repos_failed = 0

        self.logger.info("Starting run %s over %d repos", run_id, len(repos))

        for repo_path in repos:
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._process_repo, repo_path)
                    result = future.result(timeout=self.config.repo_timeout_seconds)
            except FutureTimeoutError:
                branch = self._safe_branch(repo_path)
                result = RepoResult(
                    repo_path=repo_path,
                    branch=branch,
                    change_hash="",
                    action="failed",
                    status="failed",
                    error=f"repo processing timed out after {self.config.repo_timeout_seconds}s",
                )
            except Exception as exc:
                branch = self._safe_branch(repo_path)
                result = RepoResult(
                    repo_path=repo_path,
                    branch=branch,
                    change_hash="",
                    action="failed",
                    status="failed",
                    error=str(exc),
                )

            if result.action == "committed" and result.status == "success":
                repos_committed += 1
            if result.status == "failed":
                repos_failed += 1
            self.state_store.record_repo_result(run_id, result)

        finished_at = datetime.utcnow()
        summary = RunSummary(
            started_at=started_at,
            finished_at=finished_at,
            status="success" if repos_failed == 0 else "partial_failure",
            repos_scanned=len(repos),
            repos_committed=repos_committed,
            repos_failed=repos_failed,
        )
        self.state_store.finish_run(run_id, summary)
        self.logger.info(
            "Finished run %s scanned=%d committed=%d failed=%d",
            run_id,
            summary.repos_scanned,
            summary.repos_committed,
            summary.repos_failed,
        )

    def start(self) -> None:
        scheduler = BlockingScheduler()
        scheduler.add_job(
            self.run_cycle,
            "interval",
            minutes=self.config.scan_interval_minutes,
            max_instances=1,
            coalesce=True,
            id="autocommit_cycle",
        )

        self.run_cycle()
        scheduler.start()

    def _safe_branch(self, repo_path: str) -> str:
        try:
            return get_current_branch(repo_path)
        except Exception:
            return ""

    def _process_repo(self, repo_path: str) -> RepoResult:
        add_safe_directory(repo_path)

        if not is_git_repo(repo_path):
            return RepoResult(
                repo_path=repo_path,
                branch="",
                change_hash="",
                action="skipped",
                status="skipped",
                error="not a git repository (or blocked by git safe.directory)",
            )

        branch = self._safe_branch(repo_path)

        changes = detect_repo_changes(repo_path, self.config.max_diff_chars)
        if changes is None:
            return RepoResult(
                repo_path=repo_path,
                branch=branch,
                change_hash="",
                action="skipped",
                status="skipped",
                error="no changes",
            )

        last_hash = self.state_store.last_change_hash(repo_path)
        if last_hash and last_hash == changes.change_hash:
            return RepoResult(
                repo_path=repo_path,
                branch=branch,
                change_hash=changes.change_hash,
                action="skipped",
                status="skipped",
                error="already processed same change hash",
            )

        if self.config.commit_policy == "safe":
            ok, reason = check_safe_mode(repo_path, self.config.branch_allowlist, self.config.run_tests_cmd)
        else:
            ok, reason = True, "ok"
        if not ok:
            return RepoResult(
                repo_path=repo_path,
                branch=branch,
                change_hash=changes.change_hash,
                action="skipped",
                status="skipped",
                error=reason,
            )

        repo_name = get_repo_name(repo_path)
        prompt = build_prompt(repo_name, changes.changed_files, changes.diff_text)
        ai_message = generate_commit_message(
            api_key=self.config.openrouter_api_key,
            model=self.config.openrouter_model,
            prompt=prompt,
        )
        message = normalize_message(ai_message) if ai_message else fallback_message(repo_name, changes.changed_files)

        try:
            stage_all(repo_path)
            commit_sha = create_commit(
                repo_path,
                message,
                self.config.git_author_name,
                self.config.git_author_email,
            )
            if self.config.push_enabled:
                push_current_branch(repo_path, branch)
        except GitCommandError as exc:
            return RepoResult(
                repo_path=repo_path,
                branch=branch,
                change_hash=changes.change_hash,
                action="failed",
                status="failed",
                error=str(exc),
            )

        return RepoResult(
            repo_path=repo_path,
            branch=branch,
            change_hash=changes.change_hash,
            action="committed",
            status="success",
            commit_sha=commit_sha,
        )
