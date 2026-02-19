#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
fi

echo "Using Python: ${PYTHON_BIN}"

cd "${ROOT_DIR}"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is required to bundle frontend/assistant assets."
  exit 1
fi

echo "[1/6] Installing build dependencies..."
"${PYTHON_BIN}" -m pip install -r backend/requirements.txt
"${PYTHON_BIN}" -m pip install tenacity schedule
"${PYTHON_BIN}" -m pip install -e .
"${PYTHON_BIN}" -m pip install pyinstaller

echo "[2/6] Building frontend assets..."
cd frontend
if [[ ! -d node_modules ]]; then
  npm install
fi
npm run build
cd "${ROOT_DIR}"

echo "[3/6] Installing assistant dependencies..."
cd assistant
if [[ ! -d node_modules ]]; then
  npm install
fi
cd "${ROOT_DIR}"

STAGE_DIR="${ROOT_DIR}/build/binary-resources"
echo "[4/6] Preparing bundle resources in ${STAGE_DIR}..."
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}" "${STAGE_DIR}/frontend"

rsync -a --delete \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='__pycache__' \
  backend/ "${STAGE_DIR}/backend/"

rsync -a --delete \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='__pycache__' \
  jobs/ "${STAGE_DIR}/jobs/"

rsync -a --delete database/ "${STAGE_DIR}/database/"

rsync -a --delete \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='__pycache__' \
  assistant/ "${STAGE_DIR}/assistant/"

rsync -a --delete frontend/dist/ "${STAGE_DIR}/frontend/dist/"

SEP=":"
case "${OS:-}" in
  Windows_NT) SEP=";" ;;
esac

echo "[5/6] Building one-file binary with PyInstaller..."
"${PYTHON_BIN}" -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name plg_sourcer \
  --add-data "${STAGE_DIR}/backend${SEP}backend" \
  --add-data "${STAGE_DIR}/jobs${SEP}jobs" \
  --add-data "${STAGE_DIR}/database${SEP}database" \
  --add-data "${STAGE_DIR}/assistant${SEP}assistant" \
  --add-data "${STAGE_DIR}/frontend/dist${SEP}frontend/dist" \
  --collect-all fastapi \
  --collect-all starlette \
  --collect-all pydantic \
  --collect-all pydantic_settings \
  --collect-all sqlalchemy \
  --collect-all uvicorn \
  --collect-all psycopg2 \
  --collect-all tenacity \
  --collect-all schedule \
  --collect-all passlib \
  --collect-all jose \
  --collect-all github \
  --collect-all openai \
  --collect-all anthropic \
  plg_sourcer.py

echo "[6/6] Packaging artifact..."
OS_NAME="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH_NAME="$(uname -m)"
ARTIFACT="dist/plg_sourcer_${OS_NAME}_${ARCH_NAME}.tar.gz"
tar -czf "${ARTIFACT}" -C dist plg_sourcer

echo "Built binary: dist/plg_sourcer"
echo "Packaged artifact: ${ARTIFACT}"
