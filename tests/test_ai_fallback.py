import requests

from src.ai_commit_message import fallback_message, generate_commit_message


def test_ai_failure_returns_none_and_uses_fallback(monkeypatch) -> None:
    def _raise(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.RequestException("network down")

    monkeypatch.setattr("src.ai_commit_message.requests.post", _raise)

    message = generate_commit_message(
        api_key="k",
        model="m",
        prompt="p",
        retries=1,
    )
    assert message is None

    fallback = fallback_message("repo-x", ["a.py", "b.py"])
    assert fallback == "chore: update files in repo-x (2 files)"
