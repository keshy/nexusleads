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
#   5. Builds and starts services with docker-compose
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

tar czf "/tmp/${TARBALL}" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.env' \
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
ssh ${SSH_OPTS} "${EC2_HOST}" "cd ${REMOTE_DIR} && tar xzf /tmp/${TARBALL} && rm /tmp/${TARBALL}"
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

# --- Step 5: Build and start ---
echo "[5/5] Building and starting services on remote host..."
ssh ${SSH_OPTS} "${EC2_HOST}" bash -s <<'REMOTE_SCRIPT'
set -euo pipefail

REMOTE_DIR="/opt/plg-lead-sourcer"
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

# Rename prod compose file for convenience
cp docker-compose.prod.yml docker-compose.yml 2>/dev/null || true

echo "  Pulling base images..."
$COMPOSE pull postgres nginx 2>/dev/null || true

echo "  Building application images..."
$COMPOSE build --parallel

echo "  Starting services..."
$COMPOSE up -d

echo ""
echo "  Waiting for services to start..."
sleep 10

echo ""
echo "  Service status:"
$COMPOSE ps

echo ""
echo "============================================="
echo "  Deployment complete!"
echo "  Application: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo '<your-ec2-ip>'):${LISTEN_PORT:-80}"
echo "============================================="
REMOTE_SCRIPT

# Cleanup local tarball
rm -f "/tmp/${TARBALL}"

echo ""
echo "Done! Your application should be running at http://${EC2_HOST%%@*}:80"
echo ""
echo "Useful commands (run on the EC2 instance):"
echo "  cd ${REMOTE_DIR}"
echo "  docker compose logs -f          # View all logs"
echo "  docker compose logs -f backend  # View backend logs"
echo "  docker compose ps               # Service status"
echo "  docker compose restart           # Restart all services"
