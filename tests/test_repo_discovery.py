from pathlib import Path

from src.repo_discovery import discover_git_repos


def test_discover_git_repos_finds_only_git_dirs(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "nested" / "repo-b"
    non_repo = tmp_path / "plain-folder"
    repo_a.mkdir(parents=True)
    repo_b.mkdir(parents=True)
    non_repo.mkdir(parents=True)
    (repo_a / ".git").mkdir()
    (repo_b / ".git").mkdir()

    repos = discover_git_repos(str(tmp_path))

    assert str(repo_a.resolve()) in repos
    assert str(repo_b.resolve()) in repos
    assert str(non_repo.resolve()) not in repos
