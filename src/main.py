from __future__ import annotations

import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.models import Config
from src.scheduler import AutoCommitScheduler
from src.state_store import StateStore


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def load_config() -> Config:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")

    repos_root = os.getenv("REPOS_ROOT", "/repos").strip()
    if not repos_root:
        raise RuntimeError("REPOS_ROOT is required")

    branch_allowlist = [
        item.strip()
        for item in os.getenv("BRANCH_ALLOWLIST", "main,develop,feature/*").split(",")
        if item.strip()
    ]

    return Config(
        openrouter_api_key=api_key,
        # Using OpenRouter's free endpoint - routes to available free models
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openrouter/free").strip(),
        repos_root=repos_root,
        scan_interval_minutes=_read_int("SCAN_INTERVAL_MINUTES", 15),
        branch_allowlist=branch_allowlist,
        git_author_name=os.getenv("GIT_AUTHOR_NAME", "autocommit-bot").strip(),
        git_author_email=os.getenv("GIT_AUTHOR_EMAIL", "bot@example.com").strip(),
        commit_policy=os.getenv("COMMIT_POLICY", "safe").strip(),
        run_tests_cmd=os.getenv("RUN_TESTS_CMD", "").strip(),
        max_diff_chars=_read_int("MAX_DIFF_CHARS", 12000),
        state_db_path=os.getenv("STATE_DB_PATH", "/data/state.db").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        health_port=_read_int("HEALTH_PORT", 8080),
        repo_timeout_seconds=_read_int("REPO_TIMEOUT_SECONDS", 120),
    )


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/healthz":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        return


def start_health_server(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> None:
    config = load_config()
    configure_logging(config.log_level)
    start_health_server(config.health_port)

    logger = logging.getLogger(__name__)
    logger.info(
        "Starting auto-commit worker; scan interval=%s minutes",
        config.scan_interval_minutes,
    )

    state_store = StateStore(config.state_db_path)
    scheduler = AutoCommitScheduler(config, state_store)
    scheduler.start()


if __name__ == "__main__":
    main()
