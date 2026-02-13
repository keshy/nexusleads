#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# PLG Lead Sourcer — Deploy to EC2
# =============================================================================
# Usage:
#   ./deploy.sh <ec2-host> <pem-file> [--env <env-file>]
#
# Examples:
#   ./deploy.sh ec2-user@54.123.45.67 ~/.ssh/my-key.pem
#   ./deploy.sh ubuntu@my-instance.amazonaws.com ~/keys/prod.pem --env .env.production
#
# What this script does:
#   1. Creates a tarball of the project (excluding dev artifacts)
#   2. SCPs the tarball to the EC2 instance
#   3. Extracts it on the remote host
#   4. Optionally copies your .env file
#   5. Builds and starts services with docker-compose.prod.yml
#
# Notes:
#   - Production chat websocket is served by host assistant (/ws/codex) via nginx.
#   - Assistant runs outside Docker for parity with local host-based setup.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="plg-lead-sourcer"
REMOTE_DIR="/opt/${APP_NAME}"
TARBALL="${APP_NAME}.tar.gz"

# --- Parse arguments ---
EC2_HOST=""
PEM_FILE=""
ENV_FILE=""

usage() {
    echo "Usage: $0 <ec2-host> <pem-file> [--env <env-file>]"
    echo ""
    echo "Arguments:"
    echo "  ec2-host    SSH destination (e.g. ec2-user@1.2.3.4 or ubuntu@hostname)"
    echo "  pem-file    Path to your PEM key file"
    echo ""
    echo "Options:"
    echo "  --env FILE  Path to .env file to copy to the server (default: .env.production)"
    echo ""
    echo "Examples:"
    echo "  $0 ec2-user@54.123.45.67 ~/.ssh/my-key.pem"
    echo "  $0 ubuntu@my-instance.com ~/keys/prod.pem --env .env.production"
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

EC2_HOST="$1"
PEM_FILE="$2"
shift 2

while [ $# -gt 0 ]; do
    case "$1" in
        --env)
            ENV_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Default env file: prefer .env (dev=prod), fall back to .env.production
if [ -z "$ENV_FILE" ]; then
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        ENV_FILE="${SCRIPT_DIR}/.env"
    elif [ -f "${SCRIPT_DIR}/.env.production" ]; then
        ENV_FILE="${SCRIPT_DIR}/.env.production"
    fi
fi

# --- Validate inputs ---
if [ ! -f "$PEM_FILE" ]; then
    echo "ERROR: PEM file not found: $PEM_FILE"
    exit 1
fi

if [ -n "$ENV_FILE" ] && [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Env file not found: $ENV_FILE"
    exit 1
fi

SSH_OPTS="-i ${PEM_FILE} -o StrictHostKeyChecking=no -o ConnectTimeout=10"

echo "============================================="
echo "  PLG Lead Sourcer — Deploy to EC2"
echo "============================================="
echo "  Host:     ${EC2_HOST}"
echo "  PEM:      ${PEM_FILE}"
echo "  Env file: ${ENV_FILE:-none}"
echo "  Remote:   ${REMOTE_DIR}"
echo "============================================="
echo ""

# --- Step 1: Create tarball ---
echo "[1/5] Creating deployment tarball..."
cd "$SCRIPT_DIR"

# Avoid macOS AppleDouble metadata files in deployment archives.
export COPYFILE_DISABLE=1

tar czf "/tmp/${TARBALL}" \
    --exclude='.git' \
    --exclude='._*' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.env' \
    --exclude='**/.env' \
    --exclude='**/.env.*' \
    --exclude='frontend/.env' \
    --exclude='frontend/.env.*' \
    --exclude='backend/.env' \
    --exclude='backend/.env.*' \
    --exclude='jobs/.env' \
    --exclude='jobs/.env.*' \
    --exclude='assistant/.env' \
    --exclude='assistant/.env.*' \
    --exclude='.env.local' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='.DS_Store' \
    --exclude='postgres_data' \
    --exclude='backups' \
    --exclude='.idea' \
    --exclude='.vscode' \
    backend/ \
    frontend/ \
    jobs/ \
    assistant/ \
    .agents/ \
    database/ \
    nginx/ \
    docker-compose.prod.yml \
    Makefile

TARBALL_SIZE=$(du -h "/tmp/${TARBALL}" | cut -f1)
echo "  Tarball created: ${TARBALL_SIZE}"

# --- Step 2: Ensure remote directory exists ---
echo "[2/5] Preparing remote host..."
ssh ${SSH_OPTS} "${EC2_HOST}" "sudo mkdir -p ${REMOTE_DIR} && sudo chown \$(whoami):\$(whoami) ${REMOTE_DIR}"

# --- Step 3: Upload tarball ---
echo "[3/5] Uploading tarball to ${EC2_HOST}..."
scp ${SSH_OPTS} "/tmp/${TARBALL}" "${EC2_HOST}:/tmp/${TARBALL}"

# Extract on remote
# Preserve nginx/conf.d overlays from sibling services (e.g., jiralytics)
# by not deleting the entire nginx directory during deploy.
ssh ${SSH_OPTS} "${EC2_HOST}" "cd ${REMOTE_DIR} && rm -rf backend frontend jobs assistant .agents database docker-compose.prod.yml Makefile && tar xzf /tmp/${TARBALL} && rm /tmp/${TARBALL}"
echo "  Upload complete."

# --- Step 4: Copy env file ---
if [ -n "$ENV_FILE" ]; then
    echo "[4/5] Copying environment file..."
    scp ${SSH_OPTS} "${ENV_FILE}" "${EC2_HOST}:${REMOTE_DIR}/.env"
    echo "  .env deployed."
else
    echo "[4/5] No env file specified — skipping."
    echo "  WARNING: Make sure ${REMOTE_DIR}/.env exists on the server!"
fi

CODEX_AUTH_FILE="${HOME}/.codex/auth.json"
if [ -f "${CODEX_AUTH_FILE}" ]; then
    echo "[4/5] Syncing Codex auth for host assistant..."
    scp ${SSH_OPTS} "${CODEX_AUTH_FILE}" "${EC2_HOST}:/tmp/plg-codex-auth.json"
    ssh ${SSH_OPTS} "${EC2_HOST}" "mkdir -p ~/.codex && mv /tmp/plg-codex-auth.json ~/.codex/auth.json && chmod 600 ~/.codex/auth.json"
    echo "  ~/.codex/auth.json synced."
else
    echo "[4/5] No local ~/.codex/auth.json found — skipping Codex auth sync."
fi

# --- Step 5: Build and start ---
echo "[5/5] Building and starting services on remote host..."
ssh ${SSH_OPTS} "${EC2_HOST}" bash -s <<'REMOTE_SCRIPT'
set -euo pipefail

REMOTE_DIR="/opt/plg-lead-sourcer"
COMPOSE_FILE="-f docker-compose.prod.yml"
cd "$REMOTE_DIR"

# Ensure docker is available
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed on this host."
    echo "Install with: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Check if we need sudo for docker
SUDO=""
if ! docker info &> /dev/null; then
    SUDO="sudo"
fi

# Use docker compose v2 if available, fall back to docker-compose
if $SUDO docker compose version &> /dev/null; then
    COMPOSE="$SUDO docker compose"
else
    if ! command -v docker-compose &> /dev/null; then
        echo "ERROR: docker-compose is not installed."
        exit 1
    fi
    COMPOSE="$SUDO docker-compose"
fi

# Check .env exists
if [ ! -f .env ]; then
    echo "ERROR: No .env file found at ${REMOTE_DIR}/.env"
    echo "Copy .env.production template and fill in required values."
    exit 1
fi

install_assistant_prereqs() {
    local need_node=0
    local need_psql=0

    command -v node >/dev/null 2>&1 || need_node=1
    command -v npm >/dev/null 2>&1 || need_node=1
    command -v psql >/dev/null 2>&1 || need_psql=1

    if [ "$need_node" -eq 0 ] && [ "$need_psql" -eq 0 ]; then
        return 0
    fi

    echo "  Installing host prerequisites for assistant..."
    if command -v dnf >/dev/null 2>&1; then
        if [ "$need_node" -eq 1 ]; then
            $SUDO dnf install -y nodejs npm
        fi
        if [ "$need_psql" -eq 1 ]; then
            $SUDO dnf install -y postgresql15 || $SUDO dnf install -y postgresql
        fi
    elif command -v yum >/dev/null 2>&1; then
        if [ "$need_node" -eq 1 ]; then
            $SUDO yum install -y nodejs npm
        fi
        if [ "$need_psql" -eq 1 ]; then
            $SUDO yum install -y postgresql15 || $SUDO yum install -y postgresql
        fi
    elif command -v apt-get >/dev/null 2>&1; then
        $SUDO apt-get update
        if [ "$need_node" -eq 1 ]; then
            $SUDO apt-get install -y nodejs npm
        fi
        if [ "$need_psql" -eq 1 ]; then
            $SUDO apt-get install -y postgresql-client
        fi
    else
        echo "ERROR: unsupported package manager; install node, npm, and psql manually."
        exit 1
    fi
}

install_assistant_prereqs

echo "  Pulling base images..."
$COMPOSE $COMPOSE_FILE pull postgres nginx 2>/dev/null || true

echo "  Building application images..."
$COMPOSE $COMPOSE_FILE build --parallel

echo "  Starting services..."
$COMPOSE $COMPOSE_FILE up -d

# Ensure bind-mounted nginx config refreshes even when only file contents changed.
echo "  Refreshing nginx container (bind-mounted config)..."
$COMPOSE $COMPOSE_FILE up -d --no-deps --force-recreate nginx

echo "  Applying database migrations..."
DB_USER="$(grep -E '^POSTGRES_USER=' .env 2>/dev/null | tail -n1 | cut -d= -f2- || true)"
DB_NAME="$(grep -E '^POSTGRES_DB=' .env 2>/dev/null | tail -n1 | cut -d= -f2- || true)"
DB_USER="${DB_USER%\"}"
DB_USER="${DB_USER#\"}"
DB_NAME="${DB_NAME%\"}"
DB_NAME="${DB_NAME#\"}"
DB_USER="${DB_USER:-plg_user}"
DB_NAME="${DB_NAME:-plg_lead_sourcer}"

MIGRATIONS=(
  database/migrations/001_add_app_settings.sql
  database/migrations/002_add_industry.sql
  database/migrations/003_add_source_column.sql
  database/migrations/004_add_organizations.sql
  database/migrations/005_add_billing.sql
  database/migrations/006_add_clay_push_log.sql
  database/migrations/007_add_chat_conversations.sql
  database/migrations/008_align_billing_schema.sql
)

for f in "${MIGRATIONS[@]}"; do
  if [ -f "$f" ]; then
    echo "    -> $f"
    $COMPOSE $COMPOSE_FILE exec -T postgres psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME" < "$f"
  fi
done

echo "  Installing assistant dependencies..."
if [ ! -d "${REMOTE_DIR}/assistant" ]; then
    echo "ERROR: assistant directory missing at ${REMOTE_DIR}/assistant"
    exit 1
fi
cd "${REMOTE_DIR}/assistant"
if [ -f package-lock.json ]; then
    npm ci --omit=dev || npm ci --production
else
    npm install --omit=dev || npm install --production
fi
cd "${REMOTE_DIR}"

echo "  Configuring host assistant service..."
DEPLOY_USER="$(whoami)"
cat <<SERVICE | $SUDO tee /etc/systemd/system/plg-assistant.service >/dev/null
[Unit]
Description=PLG Assistant (host-run Codex bridge)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${REMOTE_DIR}/assistant
Environment=HOME=${HOME}
Environment=NODE_ENV=production
ExecStart=${REMOTE_DIR}/assistant/start-ec2.sh
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
SERVICE

$SUDO systemctl daemon-reload
$SUDO systemctl enable plg-assistant.service >/dev/null 2>&1 || true
$SUDO systemctl restart plg-assistant.service
if ! $SUDO systemctl is-active --quiet plg-assistant.service; then
    echo "ERROR: plg-assistant.service failed to start"
    $SUDO systemctl status plg-assistant.service --no-pager || true
    exit 1
fi

echo ""
echo "  Waiting for services to start..."
sleep 10

wait_for_backend_health() {
    local max_attempts=30
    local attempt=1
    while [ "$attempt" -le "$max_attempts" ]; do
        if $COMPOSE $COMPOSE_FILE exec -T backend curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
            echo "  ✓ Backend health check passed"
            return 0
        fi
        echo "  ...backend not healthy yet (${attempt}/${max_attempts})"
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "  ✗ Backend health check failed after ${max_attempts} attempts"
    return 1
}

wait_for_assistant_health() {
    local port="$1"
    local max_attempts=30
    local attempt=1
    while [ "$attempt" -le "$max_attempts" ]; do
        if curl -fsS "http://localhost:${port}/health" >/dev/null 2>&1; then
            echo "  ✓ Assistant health check passed on :${port}"
            return 0
        fi
        echo "  ...assistant not healthy yet (${attempt}/${max_attempts})"
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "  ✗ Assistant health check failed after ${max_attempts} attempts"
    return 1
}

check_public_http() {
    local port="$1"
    if curl -fsS "http://localhost:${port}/" >/dev/null 2>&1; then
        echo "  ✓ Public HTTP check passed on :${port}"
        return 0
    fi
    echo "  ✗ Public HTTP check failed on :${port}"
    return 1
}

check_websocket_route() {
    local port="$1"
    local ws_code
    local ws_probe_key="SGVsbG8sIHdvcmxkIQ==" # gitleaks:allow
    ws_code="$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Connection: Upgrade" \
        -H "Upgrade: websocket" \
        -H "Sec-WebSocket-Version: 13" \
        -H "Sec-WebSocket-Key: ${ws_probe_key}" \
        "http://localhost:${port}/ws/codex" || true)"

    case "$ws_code" in
        101|400|403|426)
            echo "  ✓ WebSocket route check passed on :${port} (status ${ws_code})"
            return 0
            ;;
        *)
            echo "  ✗ WebSocket route check failed on :${port} (status ${ws_code})"
            return 1
            ;;
    esac
}

LISTEN_PORT_VALUE="$(grep -E '^LISTEN_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2- || true)"
LISTEN_PORT_VALUE="${LISTEN_PORT_VALUE%\"}"
LISTEN_PORT_VALUE="${LISTEN_PORT_VALUE#\"}"
LISTEN_PORT_VALUE="${LISTEN_PORT_VALUE:-80}"

ASSISTANT_PORT_VALUE="$(grep -E '^ASSISTANT_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2- || true)"
ASSISTANT_PORT_VALUE="${ASSISTANT_PORT_VALUE%\"}"
ASSISTANT_PORT_VALUE="${ASSISTANT_PORT_VALUE#\"}"
ASSISTANT_PORT_VALUE="${ASSISTANT_PORT_VALUE:-3001}"

echo ""
echo "  Running post-deploy health checks..."
wait_for_backend_health
wait_for_assistant_health "$ASSISTANT_PORT_VALUE"
check_public_http "$LISTEN_PORT_VALUE"
check_websocket_route "$LISTEN_PORT_VALUE"

echo ""
echo "  Service status:"
$COMPOSE $COMPOSE_FILE ps

echo ""
echo "============================================="
echo "  Deployment complete!"
echo "  Application: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo '<your-ec2-ip>'):${LISTEN_PORT:-80}"
echo "============================================="
REMOTE_SCRIPT

# Cleanup local tarball
rm -f "/tmp/${TARBALL}"

echo ""
DISPLAY_HOST="${EC2_HOST##*@}"
echo "Done! Your application should be running at http://${DISPLAY_HOST}:80"
echo ""
echo "Useful commands (run on the EC2 instance):"
echo "  cd ${REMOTE_DIR}"
echo "  docker compose -f docker-compose.prod.yml logs -f          # View all logs"
echo "  docker compose -f docker-compose.prod.yml logs -f backend  # View backend logs"
echo "  docker compose -f docker-compose.prod.yml ps               # Service status"
echo "  docker compose -f docker-compose.prod.yml restart          # Restart all services"
echo "  sudo systemctl status plg-assistant --no-pager            # Host assistant service"
echo "  sudo journalctl -u plg-assistant -f                       # Host assistant logs"
