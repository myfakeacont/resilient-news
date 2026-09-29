#!/usr/bin/env bash
# ==============================================================================
# 30-Minute Media-Rich News Aggregator & GitHub Sync Runner (Server 2 - ARM64)
# Schedule via crontab: */30 * * * * /home/ubuntu/resilient-news-aggregator/run_local.sh
# Or via systemd: news-aggregator.timer
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

TIMESTAMP_LOG=$(date -u +'%Y-%m-%d %H:%M:%S UTC')
echo "[${TIMESTAMP_LOG}] Starting 30-minute media news aggregator run..."

# 1. Ensure Python 3 is available
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found in PATH." >&2
    exit 1
fi

# 2. Run Python aggregator with low RAM footprint and strict timeout
python3 aggregator.py

# 3. Git Staging, Unified Commit, and Push via GitHub CLI (gh)
if [ -d ".git" ]; then
    # Track news, media images, web assets, root index, and deduplication state
    git add news/ media/ index.md public/ state.json

    if git diff --staged --quiet; then
        echo "[INFO] No new articles, media, or digests to commit in this 30-min window."
    else
        TIMESTAMP_COMMIT=$(date -u +"%Y-%m-%d %H:%M")
        COMMIT_MSG="chore(digest): sync updates ${TIMESTAMP_COMMIT}"
        echo "[INFO] Committing staged changes: ${COMMIT_MSG}"
        git commit -m "${COMMIT_MSG}"

        # Setup gh CLI git credentials if available
        if command -v gh &>/dev/null; then
            if gh auth status &>/dev/null; then
                gh auth setup-git
            fi
        fi

        # Push to remote repository if origin is configured
        if git remote get-url origin &>/dev/null; then
            CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD || echo "main")
            echo "[INFO] Syncing with remote branch: ${CURRENT_BRANCH}..."

            # Pull rebase to prevent non-fast-forward push rejections
            git pull --rebase origin "${CURRENT_BRANCH}" || {
                echo "[WARN] Rebase pull encountered issues, proceeding to attempt push..."
            }

            if command -v gh &>/dev/null && gh auth status &>/dev/null; then
                echo "[INFO] Pushing updates to GitHub via gh CLI credential helper..."
                git push origin "${CURRENT_BRANCH}" || echo "[WARN] Git push failed. Will retry next 30-min run."
            else
                git push origin "${CURRENT_BRANCH}" || echo "[WARN] Git push failed or gh unauthenticated. Changes preserved locally."
            fi
        else
            echo "[INFO] No git remote origin configured. Changes committed locally."
        fi
    fi
fi

echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] 30-minute news & media sync completed successfully."
