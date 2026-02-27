import subprocess
from pathlib import Path

from src.ai_commit_message import build_prompt
from src.change_detector import detect_repo_changes


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def test_diff_truncation_and_prompt_assembly(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)

    file_path = repo / "big.txt"
    file_path.write_text("a\n" * 4000, encoding="utf-8")

    changes = detect_repo_changes(str(repo), max_diff_chars=500)
    assert changes is not None
    assert "big.txt" in changes.changed_files
    assert len(changes.diff_text) <= 520
    assert changes.change_hash

    prompt = build_prompt("repo", changes.changed_files, changes.diff_text)
    assert "Repository: repo" in prompt
    assert "big.txt" in prompt
