from __future__ import annotations

import logging
import time
from typing import Optional

import requests


logger = logging.getLogger(__name__)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def build_prompt(repo_name: str, changed_files: list[str], diff_text: str) -> str:
    files_preview = "\n".join(changed_files[:50])
    return (
        "You are a senior engineer writing concise, conventional commit messages.\n"
        "Return only the commit title line, no quotes.\n"
        f"Repository: {repo_name}\n"
        f"Changed files ({len(changed_files)}):\n{files_preview}\n\n"
        f"Diff summary:\n{diff_text}\n"
    )


def fallback_message(repo_name: str, changed_files: list[str]) -> str:
    return f"chore: update files in {repo_name} ({len(changed_files)} files)"


def normalize_message(text: str) -> str:
    """
    Extract and normalize the commit message from API response.
    Handles various response formats and edge cases.
    """
    if not text:
        return "chore: automated update"

    # Remove leading/trailing whitespace
    text = text.strip()
    if not text:
        return "chore: automated update"

    # Get the first line
    first_line = text.splitlines()[0] if text else ""
    first_line = first_line.strip()

    # Remove quotes if present (in case API wrapped the response)
    first_line = first_line.strip("\"'`")
    first_line = first_line.strip()

    # Check if we got anything meaningful
    if not first_line:
        logger.warning("normalize_message received empty text after processing")
        return "chore: automated update"

    logger.info("Normalized message to: %s", first_line)
    return first_line


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
            response = requests.post(
                OPENROUTER_URL, json=payload, headers=headers, timeout=timeout
            )
        except requests.RequestException as exc:
            logger.warning(
                "API request failed (attempt %d/%d): %s", attempt, retries, exc
            )
            if attempt == retries:
                logger.error("API request failed after %d retries", retries)
                return None
            time.sleep(backoff)
            backoff *= 2
            continue

        # Retry on transient errors (429, 500-504) and auth errors (401)
        if response.status_code in (401, 429, 500, 502, 503, 504):
            logger.warning(
                "API returned status %d (attempt %d/%d): %s",
                response.status_code,
                attempt,
                retries,
                response.text[:200],
            )
            if attempt == retries:
                logger.error(
                    "API returned status %d after %d attempts. Check your OPENROUTER_API_KEY.",
                    response.status_code,
                    retries,
                )
                return None
            time.sleep(backoff)
            backoff *= 2
            continue

        if response.status_code >= 400:
            logger.error(
                "API returned status %d: %s", response.status_code, response.text[:200]
            )
            return None

        try:
            data = response.json()
            message = data["choices"][0]["message"]["content"]

            # Check if message is empty or just whitespace
            if not message or not message.strip():
                logger.warning(
                    "API returned empty message (attempt %d/%d)", attempt, retries
                )
                if attempt == retries:
                    logger.error(
                        "API returned empty message after %d attempts", retries
                    )
                    return None
                time.sleep(backoff)
                backoff *= 2
                continue

            logger.info("API returned message: %s", message[:100])
            return message
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.error(
                "Failed to parse API response: %s. Response: %s",
                exc,
                response.text[:200],
            )
            return None

    return None
