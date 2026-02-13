#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/plg-lead-sourcer}"
ASSISTANT_DIR="${APP_ROOT}/assistant"
ENV_FILE="${APP_ROOT}/.env"

cd "${ASSISTANT_DIR}"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
  set +a
fi

# If OPENAI_API_KEY is present but empty in .env, let Codex SDK fall back to ~/.codex/auth.json.
if [ -z "${OPENAI_API_KEY:-}" ]; then
  unset OPENAI_API_KEY
fi

POSTGRES_DB="${POSTGRES_DB:-plg_lead_sourcer}"
POSTGRES_USER="${POSTGRES_USER:-plg_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-plg_password}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"

if [ -z "${ASSISTANT_DATABASE_URL:-}" ]; then
  if [ -n "${DATABASE_URL:-}" ] && echo "${DATABASE_URL}" | grep -Eq "@(localhost|127\\.0\\.0\\.1):"; then
    ASSISTANT_DATABASE_URL="${DATABASE_URL}"
  else
    ASSISTANT_DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_PORT}/${POSTGRES_DB}"
  fi
fi

export DATABASE_URL="${ASSISTANT_DATABASE_URL}"
export PROJECT_ROOT="${PROJECT_ROOT:-${APP_ROOT}}"
export PORT="${ASSISTANT_PORT:-3001}"
export NODE_ENV="${NODE_ENV:-production}"

echo "Starting assistant on port ${PORT}"
echo "  PROJECT_ROOT=${PROJECT_ROOT}"
echo "  DATABASE_URL=${DATABASE_URL}"

exec node server.js
