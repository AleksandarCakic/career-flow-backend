import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.api.routes import (
    admin,
    coaches,
    health,
    newsletter,
    packages,
    public,
    resources,
    success_stories,
)
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
log = get_logger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[FastApiIntegration()],
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info("application.starting", environment=settings.environment)
    yield
    log.info("application.stopping")


app = FastAPI(
    title="Career Flow API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# GZip every response > 1KB. Saves on the 30%+ bandwidth penalty for
# JSON-heavy admin list responses (which can hit 50-200KB with full leads).
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def log_request_timing(request: Request, call_next: Any) -> Response:
    """Structured per-request log: method, path, status, duration_ms."""
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    log.info(
        "http.request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


app.include_router(health.router)
app.include_router(coaches.router)
app.include_router(packages.router)
app.include_router(success_stories.router)
app.include_router(public.router)
app.include_router(resources.router)
app.include_router(newsletter.router)
app.include_router(admin.router)
