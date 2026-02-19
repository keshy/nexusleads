#!/usr/bin/env python3
"""Single-command launcher for PLG Lead Sourcer without Docker."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict

from dotenv import dotenv_values


DEFAULT_DATABASE_URL = "postgresql://plg_user:plg_password@localhost:5433/plg_lead_sourcer"
MIGRATIONS_TABLE = "schema_migrations"


def _runtime_root() -> Path | None:
    """Return PyInstaller extraction root when running as a frozen binary."""
    base = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and base:
        return Path(base)
    return None


def _find_project_root(start: Path) -> Path:
    """Find repository root by checking current and parent directories."""
    runtime_root = _runtime_root()
    if runtime_root and (runtime_root / "backend" / "main.py").exists():
        return runtime_root

    candidates = [start.resolve(), *start.resolve().parents]
    for candidate in candidates:
        if (candidate / "backend" / "main.py").exists() and (candidate / "jobs" / "job_processor.py").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find project root (expected backend/main.py and jobs/job_processor.py). "
        "Run from repo root or pass --project-root."
    )


def _load_credentials(path: Path) -> Dict[str, str]:
    """Load credentials from .env/.txt key-value format or JSON object."""
    if not path.exists():
        raise FileNotFoundError(f"Credentials file not found: {path}")

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("JSON credentials file must contain an object at top level.")
        return {str(k): str(v) for k, v in data.items() if v is not None}

    values = dotenv_values(path)
    return {k: v for k, v in values.items() if v is not None}


def _terminate_process(proc: subprocess.Popen, name: str) -> None:
    """Gracefully stop a child process."""
    if proc.poll() is not None:
        return

    print(f"Stopping {name}...")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _run_command(cmd: list[str], cwd: Path) -> None:
    """Run a command and fail fast with a readable message."""
    proc = subprocess.run(cmd, cwd=str(cwd), env=os.environ.copy(), check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def _require_command(name: str) -> None:
    """Ensure a CLI command exists in PATH."""
    if shutil.which(name):
        return
    raise RuntimeError(f"Required command not found in PATH: {name}")


def _apply_sql_file(cursor, path: Path) -> None:
    """Execute SQL from a file using the active DB cursor."""
    sql = path.read_text(encoding="utf-8")
    cursor.execute(sql)


def _ensure_database_ready(project_root: Path, database_url: str) -> None:
    """Bootstrap schema on empty DB and apply pending migrations."""
    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError(
            "psycopg2 is required for automatic DB setup. "
            "Install backend deps first: python3 -m pip install -r backend/requirements.txt"
        ) from exc

    schema_path = project_root / "database" / "schema.sql"
    migration_dir = project_root / "database" / "migrations"
    migration_files = sorted(migration_dir.glob("*.sql"))

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with psycopg2.connect(database_url) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            # Empty DB detection: no users table means base schema not applied.
            cur.execute("SELECT to_regclass('public.users') IS NOT NULL;")
            has_users_table = bool(cur.fetchone()[0])

            if not has_users_table:
                print("Database appears empty; applying base schema.sql...")
                _apply_sql_file(cur, schema_path)
                conn.commit()
                print("Base schema applied.")

            # Track migrations we've applied via launcher.
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            conn.commit()

            cur.execute(f"SELECT filename FROM {MIGRATIONS_TABLE};")
            applied = {row[0] for row in cur.fetchall()}

            pending = [path for path in migration_files if path.name not in applied]
            if pending:
                print(f"Applying {len(pending)} pending migration(s)...")
            for path in pending:
                print(f"  -> {path.name}")
                try:
                    _apply_sql_file(cur, path)
                    cur.execute(
                        f"INSERT INTO {MIGRATIONS_TABLE} (filename) VALUES (%s);",
                        (path.name,),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            if pending:
                print("Database migrations complete.")


def _run_jobs_worker(project_root: Path) -> int:
    """Run the jobs processor in-process (used by frozen child process mode)."""
    jobs_dir = project_root / "jobs"
    sys.path.insert(0, str(jobs_dir))

    import asyncio
    from job_processor import JobProcessor

    processor = JobProcessor()
    asyncio.run(processor.run())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="plg_sourcer",
        description="Run PLG Lead Sourcer backend (and optional jobs worker) without Docker.",
    )
    parser.add_argument(
        "-f",
        "--credentials-file",
        required=True,
        help="Path to credentials file (.env/.txt key=value or .json).",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Path to project root (defaults to current directory).",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Backend host.")
    parser.add_argument("--port", type=int, default=8000, help="Backend port.")
    parser.add_argument(
        "--with-jobs",
        action="store_true",
        help="Also start jobs worker process.",
    )
    parser.add_argument(
        "--full-stack",
        action="store_true",
        help="Run backend + UI + assistant + jobs in one command.",
    )
    parser.add_argument(
        "--with-ui",
        action="store_true",
        help="Serve frontend UI from the backend process.",
    )
    parser.add_argument(
        "--with-assistant",
        action="store_true",
        help="Also start assistant websocket service.",
    )
    parser.add_argument(
        "--assistant-port",
        type=int,
        default=3001,
        help="Assistant service port.",
    )
    parser.add_argument(
        "--build-ui",
        action="store_true",
        help="Build frontend UI before startup (requires npm).",
    )
    parser.add_argument(
        "--frontend-dist",
        default="frontend/dist",
        help="Frontend build output directory (used with --with-ui).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable backend auto-reload (development use).",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Backend log level.",
    )
    parser.add_argument(
        "--internal-run-jobs-worker",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args()

    if args.full_stack:
        args.with_ui = True
        args.with_assistant = True
        args.with_jobs = True

    project_root = _find_project_root(Path(args.project_root))
    credentials_path = Path(args.credentials_file).expanduser().resolve()
    env_updates = _load_credentials(credentials_path)

    for key, value in env_updates.items():
        os.environ[key] = value

    if not os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URL"] = DEFAULT_DATABASE_URL
        print(
            f"DATABASE_URL not set; defaulting to {DEFAULT_DATABASE_URL}",
            file=sys.stderr,
        )

    required = ["SECRET_KEY"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        print(
            f"Missing required settings in credentials/environment: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 2

    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    jobs_proc = None
    assistant_proc = None
    try:
        _ensure_database_ready(project_root, os.environ["DATABASE_URL"])

        if args.internal_run_jobs_worker:
            return _run_jobs_worker(project_root)

        if args.with_ui:
            frontend_dist = Path(args.frontend_dist)
            if not frontend_dist.is_absolute():
                frontend_dist = (project_root / frontend_dist).resolve()
            index_path = frontend_dist / "index.html"

            if args.build_ui:
                frontend_dir = project_root / "frontend"
                print("Building frontend UI...")
                if not (frontend_dir / "node_modules").exists():
                    _run_command(["npm", "install"], cwd=frontend_dir)
                _run_command(["npm", "run", "build"], cwd=frontend_dir)

            if not index_path.exists():
                print(
                    f"Frontend build not found at {index_path}. "
                    "Run with --build-ui or provide --frontend-dist.",
                    file=sys.stderr,
                )
                return 2

            os.environ["SERVE_FRONTEND"] = "true"
            os.environ["FRONTEND_DIST"] = str(frontend_dist)
            print(f"Serving UI from {frontend_dist}")

        start_assistant = args.with_assistant or args.with_ui
        if start_assistant:
            _require_command("node")
            assistant_dir = project_root / "assistant"
            if not (assistant_dir / "node_modules").exists():
                _require_command("npm")
                print("Installing assistant dependencies...")
                _run_command(["npm", "install"], cwd=assistant_dir)

            assistant_env = os.environ.copy()
            assistant_env["PORT"] = str(args.assistant_port)
            assistant_env["PROJECT_ROOT"] = str(project_root)
            assistant_env.setdefault("DATABASE_URL", os.environ["DATABASE_URL"])

            assistant_proc = subprocess.Popen(
                ["node", "server.js"],
                cwd=str(assistant_dir),
                env=assistant_env,
            )
            print(f"Started assistant (pid={assistant_proc.pid}) on port {args.assistant_port}.")

        if args.with_jobs:
            if getattr(sys, "frozen", False):
                jobs_cmd = [
                    sys.executable,
                    "--internal-run-jobs-worker",
                    "--credentials-file",
                    str(credentials_path),
                    "--project-root",
                    str(project_root),
                ]
                jobs_proc = subprocess.Popen(jobs_cmd, env=os.environ.copy())
            else:
                jobs_dir = project_root / "jobs"
                jobs_cmd = [sys.executable, "job_processor.py"]
                jobs_proc = subprocess.Popen(jobs_cmd, cwd=str(jobs_dir), env=os.environ.copy())
            print(f"Started jobs worker (pid={jobs_proc.pid}).")

        backend_dir = project_root / "backend"

        import uvicorn

        print(f"Starting backend at http://{args.host}:{args.port} ...")
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            app_dir=str(backend_dir),
            reload=args.reload,
            log_level=args.log_level,
        )
        return 0
    finally:
        if assistant_proc is not None:
            _terminate_process(assistant_proc, "assistant service")
        if jobs_proc is not None:
            _terminate_process(jobs_proc, "jobs worker")


if __name__ == "__main__":
    raise SystemExit(main())
