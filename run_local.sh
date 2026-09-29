#!/usr/bin/env bash
# ==============================================================================
# Local / Standalone VPS News Sync Runner
# Run via crontab: 0 * * * * /home/ubuntu/resilient-news-aggregator/run_local.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] Starting hourly news sync..."

# Ensure python3 is available
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found in PATH." >&2
    exit 1
fi

# Run aggregator
python3 aggregator.py

# Optional: Auto-commit and push to GitHub if inside a git repository
if [ -d ".git" ]; then
    git add news/ index.md README.md public/ state.json
    if git diff --staged --quiet; then
        echo "[INFO] No file modifications to commit."
    else
        TIMESTAMP_UTC=$(date -u +"%Y-%m-%d %H:00 UTC")
        git commit -m "chore(news): sync hourly bulletin - ${TIMESTAMP_UTC} [skip ci]"
        
        # Push to remote branch (if remote is configured)
        if git remote get-url origin &>/dev/null; then
            echo "[INFO] Pushing changes to remote repository..."
            git push origin HEAD || echo "[WARN] Git push failed, will retry next run."
        fi
    fi
fi

echo "[$(date -u +'%Y-%m-%d %H:%M:%S UTC')] Sync completed successfully."
