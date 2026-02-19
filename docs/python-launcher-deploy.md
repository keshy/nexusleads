# Python Launcher Deploy (No Docker)

This is an additive deployment path. Existing Docker deployment (`deploy.sh`, `make deploy-ec2`) is unchanged.

## What You Get

- One command to start services:
  - `plg_sourcer -f /path/to/credentials.env`
- One command for full local stack:
  - `plg_sourcer -f /path/to/credentials.env --full-stack`
- Optional jobs worker:
  - `plg_sourcer -f /path/to/credentials.env --with-jobs`
- Optional UI serving from the same backend process:
  - `plg_sourcer -f /path/to/credentials.env --with-ui`
- Optional assistant websocket service:
  - `plg_sourcer -f /path/to/credentials.env --with-assistant`
- Automatic DB setup on startup:
  - applies `database/schema.sql` if DB is empty
  - applies pending SQL files from `database/migrations/`

## 1. Install On Host

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r backend/requirements.txt
python3 -m pip install -e .
```

This installs the CLI command: `plg_sourcer`.

## 2. Credentials File

Create a file such as `/opt/plg/credentials.env`:

```env
DATABASE_URL=postgresql://plg_user:plg_password@127.0.0.1:5432/plg_lead_sourcer
SECRET_KEY=change-me
GITHUB_TOKEN=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview
SERPER_API_KEY=
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## 3. Run

Backend only:

```bash
plg_sourcer -f /opt/plg/credentials.env
```

Backend + jobs:

```bash
plg_sourcer -f /opt/plg/credentials.env --with-jobs
```

Backend + UI (serve built frontend):

```bash
plg_sourcer -f /opt/plg/credentials.env --with-ui
```

Backend + assistant:

```bash
plg_sourcer -f /opt/plg/credentials.env --with-assistant
```

Full stack (backend + UI + assistant + jobs):

```bash
plg_sourcer -f /opt/plg/credentials.env --full-stack --build-ui
```

Build UI first, then serve it:

```bash
plg_sourcer -f /opt/plg/credentials.env --with-ui --build-ui
```

When `--with-ui` is used, assistant starts automatically on port `3001`.
Override with:

```bash
plg_sourcer -f /opt/plg/credentials.env --with-ui --assistant-port 3010
```

Optional flags:

```bash
plg_sourcer -f /opt/plg/credentials.env --host 0.0.0.0 --port 8000 --log-level info
```

Equivalent Make target:

```bash
make run-launcher CREDS=/opt/plg/credentials.env WITH_UI=1 BUILD_UI=1
```

## 3b. Build Distributable Binary

Build a single-file binary artifact:

```bash
make build-binary
```

Output:

- `dist/plg_sourcer` (binary)
- `dist/plg_sourcer_<os>_<arch>.tar.gz` (artifact)

Run from binary:

```bash
./dist/plg_sourcer -f /opt/plg/credentials.env --full-stack
```

## 4. systemd Example (Backend Only)

Create `/etc/systemd/system/plg-backend.service`:

```ini
[Unit]
Description=PLG Lead Sourcer Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/plg-lead-sourcer
Environment=PATH=/opt/plg-lead-sourcer/.venv/bin:/usr/bin:/bin
ExecStart=/opt/plg-lead-sourcer/.venv/bin/plg_sourcer -f /opt/plg/credentials.env --with-ui
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now plg-backend
sudo systemctl status plg-backend
```

## Notes

- This launcher reads settings from your credentials file and environment variables.
- Required values: `DATABASE_URL`, `SECRET_KEY`.
- `--with-ui` expects a built frontend in `frontend/dist` by default.
- You can override UI build path with `--frontend-dist /path/to/dist`.
- `--with-assistant` (or `--with-ui`) runs `assistant/server.js` as a child process.
- Node.js/npm are required when assistant is enabled.
- DB initialization/migrations run automatically on startup.
- Docker-based deployment remains available and untouched.
