#!/bin/bash
# Start the assistant service locally (required for chat on macOS)
# The Codex SDK's Rust binary doesn't work inside Docker Desktop on macOS,
# so we run the assistant on the host for local development.

cd "$(dirname "$0")"

export DATABASE_URL="${DATABASE_URL:-postgresql://plg_user:plg_password@localhost:5433/plg_lead_sourcer}"
export PROJECT_ROOT="$(cd .. && pwd)"

# Install deps if needed
if [ ! -d node_modules ]; then
  echo "Installing dependencies..."
  npm install
fi

echo "Starting assistant on port 3001..."
echo "  DATABASE_URL=$DATABASE_URL"
echo "  PROJECT_ROOT=$PROJECT_ROOT"
exec node server.js
