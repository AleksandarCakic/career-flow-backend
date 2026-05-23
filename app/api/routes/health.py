"""Health and readiness endpoints.

`/healthz` is a liveness probe — returns 200 as long as the process is alive
and serving HTTP. Railway's healthcheck targets this so it doesn't bounce
the container during transient DB blips.

`/readyz` is a readiness probe — returns 200 only when the app can actually
serve requests, which today means the database is reachable. Used by
external uptime monitoring (UptimeRobot) to detect "the API is up but the
DB is down" — a state liveness alone wouldn't catch.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.api.deps import DBSession

log = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(session: DBSession) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("readyz.db_unreachable", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable.",
        ) from exc
    return {"status": "ready"}
