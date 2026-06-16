#!/usr/bin/env bash
# Deploy CareGap Trust Planner to Databricks Apps.
#
# Uses verified Databricks CLI v1.x syntax. NOTE: this script has been written
# against the CLI help but not yet run against a live workspace (no auth was
# available at authoring time) — run it once and adjust if your workspace
# layout differs.
#
# One-time auth (opens a browser OAuth flow):
#   databricks auth login --host https://<your-workspace>.cloud.databricks.com
#
# Then:
#   WS_USER=you@example.com ./deploy_databricks.sh
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

APP_NAME="${APP_NAME:-caregap-trust-planner}"
: "${WS_USER:?Set WS_USER to your Databricks login email, e.g. WS_USER=you@example.com}"
WS_PATH="/Workspace/Users/${WS_USER}/${APP_NAME}"

echo "==> who am I?"; databricks current-user me | grep -i userName || true

echo "==> 1/3 create app compute (idempotent)"
databricks apps create "$APP_NAME" \
  --description "Evidence-backed healthcare planning: medical deserts vs data deserts" \
  || echo "    (app may already exist — continuing)"

echo "==> 2/3 sync source to ${WS_PATH} (.gitignore-aware: skips .venv/.git/app_state.db)"
databricks sync --full . "$WS_PATH" \
  --exclude ".venv/**" --exclude "tests/**" --exclude "assets/**" --exclude ".seeds/**"

echo "==> 3/3 deploy"
databricks apps deploy "$APP_NAME" --source-code-path "$WS_PATH" --mode SNAPSHOT

echo "==> done — app details (look for the url):"
databricks apps get "$APP_NAME"

# Free Edition note: Lakebase database instances are not available there. The app
# detects no LAKEBASE_DSN and falls back to a local SQLite store automatically,
# so it still runs end-to-end (planner actions persist for the app's lifetime).
