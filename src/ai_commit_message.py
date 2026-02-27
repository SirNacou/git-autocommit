from __future__ import annotations

import time
from typing import Optional

import requests


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def build_prompt(repo_name: str, changed_files: list[str], diff_text: str) -> str:
    files_preview = "\n".join(changed_files[:50])
    return (
        "You are a senior engineer writing concise, conventional commit messages.\n"
        "Return only the commit title line, max 72 chars, no quotes.\n"
        f"Repository: {repo_name}\n"
        f"Changed files ({len(changed_files)}):\n{files_preview}\n\n"
        f"Diff summary:\n{diff_text}\n"
    )


def fallback_message(repo_name: str, changed_files: list[str]) -> str:
    return f"chore: update files in {repo_name} ({len(changed_files)} files)"


def normalize_message(text: str) -> str:
    first_line = (text or "").strip().splitlines()[0] if text.strip() else ""
    first_line = first_line.strip().strip("\"'")
    if not first_line:
        return "chore: automated update"
    return first_line[:72]


def generate_commit_message(
    *,
    api_key: str,
    model: str,
    prompt: str,
    timeout: int = 25,
    retries: int = 3,
) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    backoff = 1.0
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=timeout)
        except requests.RequestException:
            if attempt == retries:
                return None
            time.sleep(backoff)
            backoff *= 2
            continue

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt == retries:
                return None
            time.sleep(backoff)
            backoff *= 2
            continue

        if response.status_code >= 400:
            return None

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            return None

    return None
