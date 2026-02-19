"""Main FastAPI application."""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings as app_settings
from routers import auth, projects, repositories, contributors, jobs, dashboard, users, settings as settings_router, organizations, integrations, billing, chat

# Create FastAPI app
app = FastAPI(
    title=app_settings.APP_NAME,
    version=app_settings.APP_VERSION,
    description="Enterprise-grade PLG lead sourcing application",
    docs_url="/docs",
    redoc_url="/redoc",
    # Accept both trailing-slash and non-trailing-slash paths.
    redirect_slashes=True,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(repositories.router, prefix="/api/repositories", tags=["Repositories"])
app.include_router(contributors.router, prefix="/api/contributors", tags=["Contributors"])
app.include_router(contributors.router, prefix="/api/leads", tags=["Leads"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["Organizations"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])


def _resolve_frontend_index() -> Path | None:
    """Resolve frontend index file path when static UI serving is enabled."""
    serve_frontend = os.getenv("SERVE_FRONTEND", "").lower() in {"1", "true", "yes"}
    if not serve_frontend:
        return None

    frontend_dist = os.getenv("FRONTEND_DIST", "").strip()
    if not frontend_dist:
        return None

    dist_path = Path(frontend_dist).expanduser()
    if not dist_path.is_absolute():
        dist_path = (Path(__file__).resolve().parent.parent / dist_path).resolve()

    index_path = dist_path / "index.html"
    if not index_path.exists():
        return None
    return index_path


FRONTEND_INDEX = _resolve_frontend_index()
FRONTEND_DIST = FRONTEND_INDEX.parent if FRONTEND_INDEX else None


@app.get("/")
async def root():
    """Root endpoint."""
    if FRONTEND_INDEX:
        return FileResponse(FRONTEND_INDEX)

    return {
        "name": app_settings.APP_NAME,
        "version": app_settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


def _configure_frontend_static(app: FastAPI) -> None:
    """Serve frontend static build when explicitly enabled."""
    if not FRONTEND_INDEX or not FRONTEND_DIST:
        return

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_files(full_path: str):
        # Preserve API/docs/health routes, only handle SPA UI paths.
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
            raise HTTPException(status_code=404, detail="Not Found")

        requested = (FRONTEND_DIST / full_path).resolve()
        if requested.is_file() and str(requested).startswith(str(FRONTEND_DIST)):
            return FileResponse(requested)
        return FileResponse(FRONTEND_INDEX)


_configure_frontend_static(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
