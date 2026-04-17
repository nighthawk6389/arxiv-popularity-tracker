#!/usr/bin/env bash
set -euo pipefail

WEBSITE_REPO="git@github.com:nighthawk6389/v0-research-paper-explainer.git"
WEBSITE_DIR="/tmp/website"
OUTPUT_DIR="/app/output"
DATE=$(date +%Y-%m-%d)

# --- SSH setup ---
mkdir -p ~/.ssh
ssh-keyscan -t ed25519,rsa github.com >> ~/.ssh/known_hosts 2>/dev/null

# --- Clone website repo ---
echo "=== Cloning website repo ==="
git clone --depth 1 "$WEBSITE_REPO" "$WEBSITE_DIR"

# --- Run tracker pipeline ---
echo "=== Running arxiv popularity tracker ==="
python -m arxiv_popularity run \
  --categories cs.AI cs.LG cs.CL cs.CV \
  --window 7d \
  --limit 100 \
  --top 3 \
  --share \
  --output-dir "$OUTPUT_DIR"

# --- Copy report to website repo ---
echo "=== Copying report to website repo ==="
mkdir -p "$WEBSITE_DIR/public/reports"
cp "$OUTPUT_DIR/report.html" "$WEBSITE_DIR/public/reports/${DATE}.html"
cp "$OUTPUT_DIR/report.html" "$WEBSITE_DIR/public/reports/latest.html"

# --- Commit and push ---
echo "=== Pushing to website repo ==="
cd "$WEBSITE_DIR"
git add public/reports/
if git diff --cached --quiet; then
  echo "No changes to push"
else
  git commit -m "chore: add trending papers report for ${DATE}"
  git push
  echo "Pushed report for ${DATE}"
fi

# --- Copy social posts to mounted output volume ---
echo "=== Exporting social posts ==="
if [ -f "$OUTPUT_DIR/social_posts.md" ]; then
  cp "$OUTPUT_DIR/social_posts.md" /output/social_posts.md
  echo "Social posts written to /output/social_posts.md"
else
  echo "No social posts generated (--share may have been skipped)"
fi

echo "=== Done ==="
