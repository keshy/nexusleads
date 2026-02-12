"""Main FastAPI application."""
from fastapi import FastAPI
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
    redirect_slashes=False,
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


from codex_bridge import codex_websocket
app.websocket("/ws/codex")(codex_websocket)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": app_settings.APP_NAME,
        "version": app_settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
