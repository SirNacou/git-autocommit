from datetime import datetime
from pathlib import Path

from src.models import RepoResult, RunSummary
from src.state_store import StateStore


def test_state_store_tracks_last_change_hash(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    store = StateStore(str(db))

    run_id = store.start_run(datetime.utcnow())
    result = RepoResult(
        repo_path="/tmp/repo-a",
        branch="main",
        change_hash="abc123",
        action="committed",
        status="success",
        commit_sha="deadbeef",
    )
    store.record_repo_result(run_id, result)
    store.finish_run(
        run_id,
        RunSummary(
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            status="success",
            repos_scanned=1,
            repos_committed=1,
            repos_failed=0,
        ),
    )

    assert store.last_change_hash("/tmp/repo-a") == "abc123"
