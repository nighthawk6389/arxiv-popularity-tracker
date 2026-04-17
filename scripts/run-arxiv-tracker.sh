#!/usr/bin/env bash
# Host-side wrapper that launches the arxiv-tracker-daily Docker container.
# Intended to be called by a scheduler (systemd timer, cron, etc.).
#
# Override defaults via environment variables:
#   OUTPUT_DIR   — where social_posts.md and logs land (default: ~/arxiv-tracker-output)
#   ENV_FILE     — secrets file with DP_API_KEY etc.     (default: ~/.config/arxiv-tracker/env)
#   IMAGE        — Docker image tag                      (default: arxiv-tracker-daily)

set -euo pipefail

OUTPUT_DIR="${OUTPUT_DIR:-$HOME/arxiv-tracker-output}"
ENV_FILE="${ENV_FILE:-$HOME/.config/arxiv-tracker/env}"
IMAGE="${IMAGE:-arxiv-tracker-daily}"

mkdir -p "$OUTPUT_DIR/logs"
LOG_FILE="$OUTPUT_DIR/logs/$(date +%Y-%m-%d).log"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: env file not found at $ENV_FILE" >&2
  echo "Create it with DP_API_KEY=... (mode 600)" >&2
  exit 1
fi

echo "=== arxiv-tracker run started at $(date -Iseconds) ===" | tee -a "$LOG_FILE"

docker run --rm \
  --env-file "$ENV_FILE" \
  -v "$HOME/.ssh:/root/.ssh:ro" \
  -v "$HOME/.gitconfig:/root/.gitconfig:ro" \
  -v "$OUTPUT_DIR:/output" \
  "$IMAGE" 2>&1 | tee -a "$LOG_FILE"

echo "=== arxiv-tracker run finished at $(date -Iseconds) ===" | tee -a "$LOG_FILE"
