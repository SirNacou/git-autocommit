#!/usr/bin/env python3
"""
CLI tool to test AI commit message generation immediately.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from src.ai_commit_message import (
    generate_commit_message,
    normalize_message,
    build_prompt,
)
from src.change_detector import detect_repo_changes, get_repo_name


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with appropriate level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def test_api_key(api_key: str, model: str) -> bool:
    """Test if the API key is valid by making a simple request."""
    logger = logging.getLogger(__name__)
    logger.info("Testing API key with model: %s", model)

    # Create a minimal test prompt
    test_message = generate_commit_message(
        api_key=api_key,
        model=model,
        prompt="Return exactly this text: 'test successful'",
        timeout=10,
        retries=1,
    )

    if test_message:
        logger.info("✓ API key is valid!")
        logger.info("Response: %s", test_message[:100])
        return True
    else:
        logger.error("✗ API key test failed - check your OPENROUTER_API_KEY")
        return False


def test_repo(
    repo_path: str, api_key: str, model: str, max_diff_chars: int = 12000
) -> bool:
    """Test commit message generation for a specific repo."""
    logger = logging.getLogger(__name__)

    repo_path = os.path.abspath(repo_path)
    logger.info("Testing repo: %s", repo_path)

    if not os.path.isdir(repo_path):
        logger.error("✗ Directory not found: %s", repo_path)
        return False

    # Detect changes
    logger.info("Detecting changes...")
    changes = detect_repo_changes(repo_path, max_diff_chars)

    if changes is None:
        logger.warning("⚠ No changes detected in repo")
        return True

    logger.info("Found %d changed files", len(changes.changed_files))
    logger.info("Diff size: %d chars", len(changes.diff_text))

    # Build prompt
    repo_name = get_repo_name(repo_path)
    prompt = build_prompt(repo_name, changes.changed_files, changes.diff_text)

    logger.info("Generating commit message...")
    ai_message = generate_commit_message(
        api_key=api_key,
        model=model,
        prompt=prompt,
        timeout=25,
        retries=3,
    )

    if ai_message:
        message = normalize_message(ai_message)
        logger.info("✓ AI-generated message:")
        logger.info("  %s", message)
        return True
    else:
        logger.error("✗ Failed to generate AI message")
        return False


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Test AI commit message generation")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Test API key command
    test_api_parser = subparsers.add_parser(
        "test-api", help="Test if OPENROUTER_API_KEY is valid"
    )
    test_api_parser.add_argument(
        "--api-key",
        default=os.getenv("OPENROUTER_API_KEY", "").strip(),
        help="OpenRouter API key (or set OPENROUTER_API_KEY env var)",
    )
    test_api_parser.add_argument(
        "--model",
        default=os.getenv(
            "OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free"
        ).strip(),
        help="Model to test (default: deepseek free tier)",
    )
    test_api_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )

    # Test repo command
    test_repo_parser = subparsers.add_parser(
        "test-repo", help="Test commit message generation for a repo"
    )
    test_repo_parser.add_argument("repo", help="Path to git repository")
    test_repo_parser.add_argument(
        "--api-key",
        default=os.getenv("OPENROUTER_API_KEY", "").strip(),
        help="OpenRouter API key (or set OPENROUTER_API_KEY env var)",
    )
    test_repo_parser.add_argument(
        "--model",
        default=os.getenv(
            "OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free"
        ).strip(),
        help="Model to use (default: deepseek free tier)",
    )
    test_repo_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )
    test_repo_parser.add_argument(
        "--max-diff", type=int, default=12000, help="Max diff chars (default: 12000)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if args.command == "test-api":
        if not args.api_key:
            logger.error("✗ OPENROUTER_API_KEY not set")
            return 1
        success = test_api_key(args.api_key, args.model)
        return 0 if success else 1

    elif args.command == "test-repo":
        if not args.api_key:
            logger.error("✗ OPENROUTER_API_KEY not set")
            return 1
        success = test_repo(args.repo, args.api_key, args.model, args.max_diff)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
