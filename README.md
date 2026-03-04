# Git Auto-Commit (OpenRouter Free Tier)

Dockerized Python worker that scans mounted git repositories every 15 minutes, generates commit messages with OpenRouter free models, safely commits and pushes, and lets your CI/CD deploy on push.

## Features
- Scans multiple repos under a single mounted root directory
- Safe policy checks (branch allowlist, detached HEAD, conflicts, missing upstream)
- AI commit message generation with retry/backoff and fallback message
- Dedup using content hash + SQLite state
- Structured run logs in SQLite
- Optional health endpoint at `/healthz`

## Quick Start
1. Copy environment file:
```bash
cp .env.example .env
```
2. Edit `.env` with your `OPENROUTER_API_KEY`.
3. Put repositories under `./watched-repos` (or set `REPOS_HOST_PATH` in `.env`).
4. Start dev mode:
```bash
docker compose -f docker-compose.dev.yml up -d --build
```
5. Follow logs:
```bash
docker compose -f docker-compose.dev.yml logs -f autocommit
```

## Docker Compose Modes
- `docker-compose.dev.yml`: local build + `./src:/app/src` bind mount for fast iteration.
- `docker-compose.prod.yml`: pulls `ghcr.io/<owner>/git-autocommit:${IMAGE_TAG}` for immutable deploys.
- `docker-compose.yml`: dev-compatible default for convenience (same behavior as dev mode).

### Development
```bash
docker compose -f docker-compose.dev.yml up -d --build
```

### Production
Set these in `.env`:
- `GHCR_OWNER` (GitHub user/org that publishes the package)
- `IMAGE_TAG` (for example `latest` or `v1.2.3`)
- `REPOS_HOST_PATH` (host path containing repositories to scan)

Then run:
```bash
IMAGE_TAG=latest docker compose -f docker-compose.prod.yml up -d
```

## Publish Docker Image to GHCR
This repo includes `.github/workflows/docker-publish.yml` which publishes on:
- push to `main`
- push of tags matching `v*`
- manual `workflow_dispatch`

Published tags:
- `ghcr.io/<owner>/git-autocommit:sha-<shortsha>`
- `ghcr.io/<owner>/git-autocommit:latest` (main branch only)
- `ghcr.io/<owner>/git-autocommit:vX.Y.Z` (tag builds)

Notes:
- Workflow auth uses `GITHUB_TOKEN` with `packages: write`.
- For private packages, production hosts must authenticate to GHCR before pull.
- For public packages, no pull login is needed.

## How It Works
For each scan cycle:
1. Discover git repos under `REPOS_ROOT`.
2. Skip repos with no changes or disallowed branch.
3. Skip unsafe repos (detached head, conflicts, missing upstream).
4. Generate diff summary and change hash.
5. Request commit message from OpenRouter.
6. `git add -A`, commit with bot identity, push current branch.
7. Record run/repo results in SQLite.

## Config
See `.env.example` for all variables.

Important ones:
- `OPENROUTER_API_KEY` required. Get one free at https://openrouter.ai (no payment required for free tier).
- `OPENROUTER_MODEL` defaults to `deepseek/deepseek-chat-v3-0324:free` (completely free, no charges).
- `BRANCH_ALLOWLIST` supports glob patterns (`feature/*`).
- `RUN_TESTS_CMD` optional command executed per repo before commit.
- `PUSH_ENABLED=false` allows local commit-only mode.

## Notes
- This service never force-resets, force-checkouts, or cleans repositories.
- Deployments should consume a pinned GHCR image tag in production.

## Testing
### Unit Tests
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

### CLI Testing (Quick Validation)
Test your setup immediately without waiting 15 minutes:

**Test API key validity:**
```bash
docker compose exec autocommit python cli.py test-api -v
```
Expected output if valid:
```
✓ API key is valid!
Response: test successful
```

**Test commit message generation for a repository:**
```bash
docker compose exec autocommit python cli.py test-repo /repos/your-repo -v
```
This will:
1. Detect uncommitted changes in the repo
2. Generate an AI commit message
3. Show you exactly what would be committed
4. Display full debug logs with `-v`
