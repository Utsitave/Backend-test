import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401 — registers all ORM models with SQLAlchemy's metadata
from app.config import get_settings
from app.database import Base, engine
from app.routers import admin, certificates, health, measurements, metrics
from app.services.certificate_service import initialize_ca

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    initialize_ca()
    logger.info("IoT backend started on %s:%d", settings.host, settings.port)
    yield
    await engine.dispose()
    logger.info("IoT backend stopped")


app = FastAPI(
    title="IoT Secure Backend",
    description="Secure FastAPI backend for IoT data collection and device certificate management",
    version="1.0.0",
    lifespan=lifespan,
)

# Only server-to-server traffic expected (IoT devices + Grafana).
# Add specific origins here if a browser UI is ever added.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["X-Device-API-Key", "X-API-Key", "X-Admin-API-Key", "Content-Type"],
)

app.include_router(health.router)
app.include_router(measurements.router)
app.include_router(certificates.router)
app.include_router(metrics.router)
app.include_router(admin.router)


@app.exception_handler(Exception)
async def _unhandled_exception(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
