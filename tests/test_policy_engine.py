from src.policy_engine import branch_allowed


def test_branch_allowlist_patterns() -> None:
    patterns = ["main", "develop", "feature/*"]
    assert branch_allowed("main", patterns)
    assert branch_allowed("develop", patterns)
    assert branch_allowed("feature/new-login", patterns)
    assert not branch_allowed("bugfix/urgent", patterns)
