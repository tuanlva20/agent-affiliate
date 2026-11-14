"""AMAS v1.5.0 — FastAPI Main Application Entrypoint (Phase 5.5 / AMAS-17)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.calendar import router as calendar_router
from src.api.channels import router as channels_router
from src.api.groups import router as groups_router
from src.api.history import router as history_router
from src.api.openseo import router as openseo_router
from src.api.projects import router as projects_router
from src.api.proxies import router as proxies_router
from src.api.studio import router as studio_router

app = FastAPI(
    title="AMAS Studio API",
    version="1.5.0",
    description="Backend API for AMAS AI Motion Control Studio, Multi-Project Workspace & Multi-Channel Publisher",
)

# CORS configuration for Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(studio_router)
app.include_router(channels_router)
app.include_router(proxies_router)
app.include_router(history_router)
app.include_router(projects_router)
app.include_router(calendar_router)
app.include_router(groups_router)
app.include_router(openseo_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """System health check endpoint."""
    return {"status": "ok", "service": "amas-api", "version": "1.5.0"}
