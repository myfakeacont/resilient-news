#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "Starting 30-minute Go news engine run..."

# 1. Execute Go Engine
if [ -f "./news_engine" ]; then
    ./news_engine
else
    echo "[WARN] ./news_engine binary not found, compiling..."
    (cd go-engine && go build -ldflags="-s -w" -o ../news_engine main.go)
    ./news_engine
fi

# 2. Git Staging, Unified Commit, and Push via GitHub CLI (gh)
if [ -d ".git" ]; then
    git add articles/ news/ media/ index.md public/ state.json go-engine/

    if git diff --staged --quiet; then
        echo "[INFO] No new articles, media, or digests to commit in this 30-min window."
    else
        NOW_DATE=$(date -u +%Y-%m-%d_%H:%M)
        COMMIT_MSG="chore(digest): sync updates ${NOW_DATE} [Go Engine]"
        echo "[INFO] Committing staged changes: ${COMMIT_MSG}"
        git commit -m "${COMMIT_MSG}"

        if command -v gh &>/dev/null && gh auth status &>/dev/null; then
            gh auth setup-git
        fi

        if git remote get-url origin &>/dev/null; then
            CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD || echo "main")
            echo "[INFO] Syncing with remote branch: ${CURRENT_BRANCH}..."
            git pull --rebase origin "${CURRENT_BRANCH}" || true
            git push origin "${CURRENT_BRANCH}" || echo "[WARN] Git push failed. Will retry next run."
        fi
    fi
fi

echo "30-minute news & media sync completed successfully."
