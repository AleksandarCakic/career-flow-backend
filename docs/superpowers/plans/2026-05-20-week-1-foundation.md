# Week 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Both repos (`career-flow-backend`, `career-flow-frontend`) scaffolded with working FastAPI + Next.js shells deployed to Railway, GitHub Actions CI green on both, third-party services connected (Sentry, PostHog, Clerk, Resend, Slack, UptimeRobot, Cloudflare DNS), and `api.career-flow.com` + `staging.career-flow.com` responding to healthchecks.

**Architecture:** Two parallel tracks (backend Python+FastAPI+Postgres, frontend Next.js with TS strict). Both deploy to a single Railway project with three environments (`production`, `staging`, preview-per-PR). DNS via Cloudflare. CI via GitHub Actions runs lint + typecheck + test + build + (on staging/main) deploy.

**Tech Stack:**
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, Pydantic v2, pytest, uv, Ruff, mypy, structlog, sentry-sdk
- Frontend: Next.js 16 App Router, React 19, TypeScript strict, Tailwind v4, shadcn/ui, TanStack Query v5, pnpm, ESLint, Vitest, Playwright
- Infra: Railway (3 services × 3 envs), Cloudflare DNS, GitHub Actions
- Third-party (just connected this week, deeper use later): Sentry, PostHog (EU), Clerk, Resend, Slack, UptimeRobot

**Spec reference:** `docs/superpowers/specs/2026-05-20-career-flow-split-design.md`

---

## Phase 0 — User prerequisites (USER ACTIONS REQUIRED)

These can't be automated. Check each off as you complete them. Don't start Phase 1 until all are done.

- [ ] **0.1** Create accounts (if you don't have them): Railway, Cloudflare, Clerk, Resend, Sentry, PostHog (sign up in **EU** region — important), UptimeRobot, Slack.
- [ ] **0.2** Make sure `career-flow.com` is in Cloudflare DNS. If it's currently with another registrar, transfer it or change nameservers to Cloudflare's.
- [ ] **0.3** Create GitHub repos `career-flow-backend` and `career-flow-frontend` under your GitHub account. Add the existing local repos as remotes and push `main`:
  ```bash
  cd "/Users/caki/Documents/Engineering/Career Flow/career-flow-backend"
  git remote add origin git@github.com:AleksandarCakic/career-flow-backend.git
  git push -u origin main
  cd "../career-flow-frontend"
  git remote add origin git@github.com:AleksandarCakic/career-flow-frontend.git
  git push -u origin main
  ```
- [ ] **0.4** In Railway: create a project named `career-flow`. Add environments `production` and `staging`. Do NOT connect repos yet.
- [ ] **0.5** Fix your local git identity (the earlier commits used the auto-derived `caki@Cakis-MacBook-Pro.local`):
  ```bash
  git config --global user.name "Aleksandar Cakic"
  git config --global user.email "acakic92@gmail.com"
  ```
- [ ] **0.6** In Resend: add domain `career-flow.com`. Resend will give you SPF, DKIM, and DMARC TXT records — keep that page open, you'll add them in Phase 5.
- [ ] **0.7** In Clerk: create an application named "Career Flow Admin". Enable **Email + Password** and **Email magic link** sign-in methods. Disable signups (admin-only allowlist). Note the publishable + secret keys for each environment (development, production).
- [ ] **0.8** In Sentry: create two projects: `career-flow-backend` (Python) and `career-flow-frontend` (Next.js). Note DSN per environment for each.
- [ ] **0.9** In PostHog Cloud (**EU region**): create a project named "Career Flow". Note the project API key (publishable) and the host (`https://eu.posthog.com`).
- [ ] **0.10** Create the Slack workspace `career-flow` (use `careerflow.slack.com` or similar). Invite your partner. Create channels: `#leads`, `#bookings`, `#payments`, `#alerts-all`. Install a custom Slack app named "Career Flow Backend" with Incoming Webhooks scope. Generate one webhook URL per channel. Save them.
- [ ] **0.11** Sign in to UptimeRobot. Don't add monitors yet — we'll do that in Week 8.
- [ ] **0.12** Install local toolchain:
  ```bash
  # uv (Python package manager)
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # pnpm (Node package manager)
  brew install pnpm

  # Railway CLI (optional but handy)
  brew install railway
  ```
- [ ] **0.13** Tell me when all of 0.1–0.12 are done. I'll verify before starting Phase 1.

---

## Phase 1 — Backend scaffolding

### Task 1: Initialize Python project with uv

**Files:**
- Create: `career-flow-backend/pyproject.toml`
- Create: `career-flow-backend/.python-version`
- Create: `career-flow-backend/.gitignore`
- Create: `career-flow-backend/uv.lock`

- [ ] **Step 1: Initialize uv project**

Run:
```bash
cd "/Users/caki/Documents/Engineering/Career Flow/career-flow-backend"
uv init --python 3.12 --no-readme --no-package
rm main.py hello.py 2>/dev/null || true   # uv may scaffold a stub; remove it
```

Expected: `pyproject.toml`, `.python-version`, possibly `main.py` (delete it).

- [ ] **Step 2: Add production dependencies**

Run:
```bash
uv add \
  "fastapi[standard]" \
  "sqlalchemy[asyncio]" \
  asyncpg \
  alembic \
  pydantic-settings \
  httpx \
  structlog \
  python-multipart \
  stripe \
  "sentry-sdk[fastapi]" \
  pyjwt \
  cryptography
```

- [ ] **Step 3: Add dev dependencies**

Run:
```bash
uv add --dev \
  pytest \
  pytest-asyncio \
  pytest-cov \
  ruff \
  mypy \
  respx \
  pytest-postgresql \
  "psycopg[binary]" \
  factory-boy
```

- [ ] **Step 4: Append tooling config to pyproject.toml**

Append to `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "S", "A", "C4", "T20", "PT", "RET", "SIM"]
ignore = ["S101"]  # allow assert in tests

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S"]
"alembic/**" = ["E501"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
exclude = ["alembic/"]
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["stripe.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra --strict-markers --cov=app --cov-report=term-missing"
testpaths = ["tests"]
markers = [
    "integration: integration tests requiring DB",
    "unit: unit tests with no DB",
]
```

- [ ] **Step 5: Create .gitignore**

Write to `career-flow-backend/.gitignore`:
```
__pycache__/
*.py[cod]
*.so
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.env
.env.local
.venv/
venv/
*.egg-info/
dist/
build/
.DS_Store
```

- [ ] **Step 6: Verify tools install correctly**

Run:
```bash
uv sync
uv run ruff --version
uv run mypy --version
uv run pytest --version
```

Expected: each prints a version, no errors.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .python-version .gitignore uv.lock
git commit -m "chore: initialize Python project with uv and tooling config"
```

---

### Task 2: FastAPI app skeleton with healthcheck

**Files:**
- Create: `career-flow-backend/app/__init__.py`
- Create: `career-flow-backend/app/main.py`
- Create: `career-flow-backend/app/core/__init__.py`
- Create: `career-flow-backend/app/core/config.py`
- Create: `career-flow-backend/app/core/logging.py`
- Create: `career-flow-backend/app/api/__init__.py`
- Create: `career-flow-backend/app/api/routes/__init__.py`
- Create: `career-flow-backend/app/api/routes/health.py`

- [ ] **Step 1: Create config module (Pydantic Settings)**

Write `app/core/config.py`:
```python
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str = Field(default="postgresql+asyncpg://localhost/careerflow_dev")

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    admin_emails: list[str] = Field(default_factory=list)

    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    calendly_webhook_signing_key: str = ""

    resend_api_key: str = ""
    resend_from_inquiry: str = "inquiry@career-flow.com"
    resend_from_noreply: str = "noreply@career-flow.com"
    resend_from_onboarding: str = "onboarding@career-flow.com"

    slack_webhook_leads: str = ""
    slack_webhook_bookings: str = ""
    slack_webhook_payments: str = ""
    slack_webhook_alerts: str = ""

    posthog_api_key: str = ""
    posthog_host: str = "https://eu.posthog.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Create logging module (structlog)**

Write `app/core/logging.py`:
```python
import logging
import sys

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.log_level)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.environment == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

- [ ] **Step 3: Create health route**

Write `app/api/routes/health.py`:
```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    # Will be expanded later to check DB connectivity, etc.
    return {"status": "ready"}
```

- [ ] **Step 4: Create app/main.py**

Write `app/main.py`:
```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.api.routes import health
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
```

- [ ] **Step 5: Create empty __init__.py files**

Run:
```bash
mkdir -p app/api/routes app/core
touch app/__init__.py app/api/__init__.py app/api/routes/__init__.py app/core/__init__.py
```

- [ ] **Step 6: Run the app locally to verify**

Run:
```bash
uv run fastapi dev app/main.py
```

In another terminal: `curl http://127.0.0.1:8000/healthz`
Expected: `{"status":"ok"}`

Stop the server (Ctrl-C).

- [ ] **Step 7: Commit**

```bash
git add app/
git commit -m "feat(api): add FastAPI app skeleton with health endpoints"
```

---

### Task 3: First passing test against the healthcheck

**Files:**
- Create: `career-flow-backend/tests/__init__.py`
- Create: `career-flow-backend/tests/conftest.py`
- Create: `career-flow-backend/tests/unit/__init__.py`
- Create: `career-flow-backend/tests/unit/test_health.py`

- [ ] **Step 1: Create conftest.py with an httpx-based async client fixture**

Write `tests/conftest.py`:
```python
from typing import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 2: Write the failing test**

Write `tests/unit/test_health.py`:
```python
import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_healthz_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
async def test_readyz_returns_ready(client: AsyncClient) -> None:
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
```

- [ ] **Step 3: Create empty __init__.py for test packages**

Run:
```bash
mkdir -p tests/unit tests/integration
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_health.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test(health): add async tests for healthcheck endpoints"
```

---

### Task 4: Alembic + SQLAlchemy 2.0 async setup

**Files:**
- Create: `career-flow-backend/alembic.ini`
- Create: `career-flow-backend/alembic/env.py`
- Create: `career-flow-backend/alembic/script.py.mako`
- Create: `career-flow-backend/alembic/versions/.gitkeep`
- Create: `career-flow-backend/app/core/db.py`
- Create: `career-flow-backend/app/models/__init__.py`
- Create: `career-flow-backend/app/models/base.py`

- [ ] **Step 1: Initialize Alembic**

Run:
```bash
uv run alembic init -t async alembic
```

This creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 2: Replace alembic.ini sqlalchemy.url to read from env**

In `alembic.ini`, find the line `sqlalchemy.url = ` and set it to empty (we'll override in `env.py`):
```
sqlalchemy.url =
```

- [ ] **Step 3: Create base model**

Write `app/models/__init__.py`:
```python
from app.models.base import Base

__all__ = ["Base"]
```

Write `app/models/base.py`:
```python
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TimestampedBase(Base):
    __abstract__ = True

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
```

- [ ] **Step 4: Create DB session module**

Write `app/core/db.py`:
```python
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 5: Wire alembic/env.py to async + use Settings**

Replace `alembic/env.py` with:
```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.models import Base  # noqa: F401  # ensures all models import

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 6: Create empty initial migration**

Run:
```bash
uv run alembic revision -m "initial empty"
```

Expected: creates `alembic/versions/<hash>_initial_empty.py`. The `upgrade()` and `downgrade()` bodies should be `pass` — leave them empty for now.

- [ ] **Step 7: Verify alembic check works**

We can't actually upgrade yet (no DB). Just verify alembic loads:
```bash
uv run alembic heads
```

Expected: prints one revision id with `(head)`.

- [ ] **Step 8: Commit**

```bash
git add alembic.ini alembic/ app/core/db.py app/models/
git commit -m "feat(db): set up async SQLAlchemy 2.0 + Alembic with empty initial migration"
```

---

### Task 5: Backend `.env.example`

**Files:**
- Create: `career-flow-backend/.env.example`

- [ ] **Step 1: Write .env.example**

Write `career-flow-backend/.env.example`:
```
# Core
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://localhost/careerflow_dev

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Admin allowlist (comma-separated emails)
ADMIN_EMAILS=["acakic92@gmail.com"]

# Clerk
CLERK_SECRET_KEY=
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Calendly
CALENDLY_WEBHOOK_SIGNING_KEY=

# Resend
RESEND_API_KEY=
RESEND_FROM_INQUIRY=inquiry@career-flow.com
RESEND_FROM_NOREPLY=noreply@career-flow.com
RESEND_FROM_ONBOARDING=onboarding@career-flow.com

# Slack incoming webhooks
SLACK_WEBHOOK_LEADS=
SLACK_WEBHOOK_BOOKINGS=
SLACK_WEBHOOK_PAYMENTS=
SLACK_WEBHOOK_ALERTS=

# PostHog (server-side)
POSTHOG_API_KEY=
POSTHOG_HOST=https://eu.posthog.com

# Sentry
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add .env.example for backend"
```

---

### Task 6: Backend Dockerfile

**Files:**
- Create: `career-flow-backend/Dockerfile`
- Create: `career-flow-backend/.dockerignore`

- [ ] **Step 1: Write .dockerignore**

Write `.dockerignore`:
```
.git
.gitignore
.env
.env.local
.venv
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
tests/
docs/
*.md
.github/
```

- [ ] **Step 2: Write multi-stage Dockerfile**

Write `Dockerfile`:
```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

RUN pip install --no-cache-dir uv==0.5.18

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN uv sync --frozen --no-dev


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --no-create-home --shell /bin/false app

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

USER app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- [ ] **Step 3: Test Docker build locally (USER ACTION, requires Docker Desktop)**

Run:
```bash
docker build -t career-flow-backend:test .
docker run --rm -p 8000:8000 -e DATABASE_URL="postgresql+asyncpg://invalid" career-flow-backend:test &
sleep 5
curl http://localhost:8000/healthz
```

Expected: `{"status":"ok"}`. The alembic upgrade will fail with the invalid DB URL but the curl should still work because we only need `/healthz` to confirm the image runs. Stop with `docker stop $(docker ps -q --filter "ancestor=career-flow-backend:test")`.

If you don't have Docker locally, skip this step — Railway will build the image during deploy.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat(deploy): add multi-stage Dockerfile for Railway"
```

---

### Task 7: Backend `railway.toml`

**Files:**
- Create: `career-flow-backend/railway.toml`

- [ ] **Step 1: Write railway.toml**

Write `railway.toml`:
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/healthz"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 2: Commit**

```bash
git add railway.toml
git commit -m "feat(deploy): add Railway service config"
```

---

### Task 8: Backend GitHub Actions CI

**Files:**
- Create: `career-flow-backend/.github/workflows/ci.yml`

- [ ] **Step 1: Write CI workflow**

Write `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main, staging]

env:
  PYTHON_VERSION: "3.12"

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run mypy app/

  test-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run pytest tests/unit -v

  test-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: ci
          POSTGRES_PASSWORD: ci
          POSTGRES_DB: careerflow_ci
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://ci:ci@localhost:5432/careerflow_ci
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run alembic upgrade head
      - run: uv run pytest tests/integration -v

  openapi-export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen
      - name: Export OpenAPI schema
        run: uv run python -m app.export_openapi > openapi.json
      - name: Upload as artifact
        uses: actions/upload-artifact@v4
        with:
          name: openapi-schema
          path: openapi.json
          retention-days: 30

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Build Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          load: true
          tags: career-flow-backend:ci
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 2: Create the openapi export script**

Write `app/export_openapi.py`:
```python
"""Dump the FastAPI OpenAPI schema to stdout for CI."""
import json
import sys

from app.main import app


def main() -> None:
    schema = app.openapi()
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add .github/ app/export_openapi.py
git commit -m "ci(backend): add GitHub Actions workflow with lint, typecheck, tests, openapi export, docker build"
```

---

### Task 9: Push backend to origin and confirm CI runs

- [ ] **Step 1: Push**

Run:
```bash
git push origin main
```

- [ ] **Step 2: Verify CI runs**

USER ACTION: open `https://github.com/AleksandarCakic/career-flow-backend/actions`. Confirm the CI workflow ran on this push and all jobs passed.

If any job failed: investigate the logs, fix, re-commit, re-push.

---

## Phase 2 — Frontend scaffolding

### Task 10: Initialize Next.js 16 project

**Files:**
- Create: `career-flow-frontend/package.json`
- Create: `career-flow-frontend/tsconfig.json`
- Create: `career-flow-frontend/next.config.mjs`
- Create: `career-flow-frontend/app/layout.tsx`
- Create: `career-flow-frontend/app/page.tsx`
- Create: `career-flow-frontend/app/globals.css`
- Create: `career-flow-frontend/.gitignore`
- Create: `career-flow-frontend/pnpm-lock.yaml`

- [ ] **Step 1: Run create-next-app**

Run:
```bash
cd "/Users/caki/Documents/Engineering/Career Flow"
pnpm create next-app@latest career-flow-frontend-tmp \
  --typescript --tailwind --eslint --app --src-dir --no-import-alias \
  --turbopack
```

When asked "Use App Router?" → Yes. When asked about Turbopack → Yes.

- [ ] **Step 2: Merge the tmp directory into the existing repo (we need to preserve the existing CLAUDE.md, docs/, .git)**

Run:
```bash
# Move only the new files into the existing repo
cd career-flow-frontend-tmp
rsync -av --exclude='.git' --exclude='.gitignore' --exclude='README.md' \
  --exclude='node_modules' \
  . "../career-flow-frontend/"

# Merge .gitignore additions
cat .gitignore >> "../career-flow-frontend/.gitignore"

# Remove the temp dir
cd ..
rm -rf career-flow-frontend-tmp
```

- [ ] **Step 3: Deduplicate .gitignore**

Edit `career-flow-frontend/.gitignore` and remove duplicate lines. The final file should contain:
```
node_modules/
.next/
out/
build/
dist/

# environment
.env
.env.local
.env*.local

# debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*

# misc
.DS_Store
*.pem
.vscode/

# typescript
*.tsbuildinfo
next-env.d.ts

# tests / coverage
coverage/
playwright-report/
test-results/
.lighthouseci/

# generated api client
src/lib/api-client/*.gen.ts
src/lib/api-client/*.gen.json
```

- [ ] **Step 4: Verify it runs**

Run:
```bash
cd career-flow-frontend
pnpm install
pnpm dev
```

Open http://localhost:3000 in browser. Confirm the default Next.js page loads. Stop with Ctrl-C.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: scaffold Next.js 16 with App Router + Tailwind + TypeScript"
```

---

### Task 11: Tighten TypeScript strict config

**Files:**
- Modify: `career-flow-frontend/tsconfig.json`

- [ ] **Step 1: Add strict flags**

Open `tsconfig.json`. The `compilerOptions` should already have `"strict": true`. Add these additional flags:
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "verbatimModuleSyntax": true
  }
}
```

(Leave all other fields that create-next-app generated untouched.)

- [ ] **Step 2: Run typecheck**

Run:
```bash
pnpm tsc --noEmit
```

Expected: no errors. If there are errors, fix them (likely just adding `as const` or narrowing in generated code).

- [ ] **Step 3: Commit**

```bash
git add tsconfig.json
git commit -m "chore(ts): enable additional strict TypeScript flags"
```

---

### Task 12: Install shadcn/ui and core component primitives

**Files:**
- Create: `career-flow-frontend/components.json`
- Create: `career-flow-frontend/src/lib/utils.ts`
- Create: `career-flow-frontend/src/components/ui/button.tsx`
- Create: `career-flow-frontend/src/components/ui/card.tsx`
- Create: `career-flow-frontend/src/components/ui/input.tsx`
- Create: `career-flow-frontend/src/components/ui/label.tsx`
- Create: `career-flow-frontend/src/components/ui/textarea.tsx`
- Create: `career-flow-frontend/src/components/ui/form.tsx`
- Create: `career-flow-frontend/src/components/ui/toast.tsx`

- [ ] **Step 1: Initialize shadcn**

Run:
```bash
cd career-flow-frontend
pnpm dlx shadcn@latest init
```

Answer prompts:
- Style: default
- Base color: neutral
- CSS variables: yes

This creates `components.json`, `src/lib/utils.ts`, and updates `src/app/globals.css` with CSS variables.

- [ ] **Step 2: Add the components we'll need in Week 1**

Run:
```bash
pnpm dlx shadcn@latest add button card input label textarea form toast sonner
```

- [ ] **Step 3: Verify build still works**

Run:
```bash
pnpm build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(ui): add shadcn/ui base primitives (button, card, input, label, textarea, form, toast)"
```

---

### Task 13: Install runtime dependencies

**Files:**
- Modify: `career-flow-frontend/package.json`

- [ ] **Step 1: Add runtime deps**

Run:
```bash
pnpm add \
  @clerk/nextjs \
  @sentry/nextjs \
  posthog-js \
  @tanstack/react-query \
  react-hook-form \
  @hookform/resolvers \
  zod \
  framer-motion \
  next-themes \
  lucide-react \
  date-fns \
  resend \
  @react-email/components \
  sharp
```

- [ ] **Step 2: Add dev deps**

Run:
```bash
pnpm add -D \
  @hey-api/openapi-ts \
  @tanstack/react-query-devtools \
  @types/node \
  vitest \
  @vitest/coverage-v8 \
  @testing-library/react \
  @testing-library/jest-dom \
  jsdom \
  @playwright/test \
  @lhci/cli
```

(Prettier integration is intentionally omitted for Week 1 — Tailwind class ordering is handled by ESLint via Next's defaults; reintroduce Prettier in a later week if formatting drift becomes a problem.)

- [ ] **Step 3: Verify build**

Run: `pnpm build`
Expected: success.

- [ ] **Step 4: Commit**

```bash
git add package.json pnpm-lock.yaml
git commit -m "chore(deps): add runtime dependencies (Clerk, Sentry, PostHog, TanStack Query, RHF, Zod, Framer, Email)"
```

---

### Task 14: Configure ESLint to forbid direct fetch to the API

**Files:**
- Modify: `career-flow-frontend/.eslintrc.json` (or whatever config file create-next-app generated)
- Create: `career-flow-frontend/eslint-rules/no-direct-api-fetch.md` (documentation only)

- [ ] **Step 1: Check what ESLint config file exists**

Run: `ls -la career-flow-frontend/.eslint*`

Recent Next.js scaffolds generate `eslint.config.mjs` (flat config) — adjust steps below accordingly.

- [ ] **Step 2: Add no-restricted-imports rule (flat config)**

Edit `eslint.config.mjs` and add inside the rules block of the main config:
```js
rules: {
  "no-restricted-imports": [
    "error",
    {
      patterns: [
        {
          group: ["**/api-client/raw-fetch", "*"],
          message: "Use the generated TanStack Query hooks from '@/lib/api-client' instead of direct fetch.",
        },
      ],
    },
  ],
  "no-restricted-globals": [
    "error",
    {
      name: "fetch",
      message: "Use the generated TanStack Query hooks from '@/lib/api-client' instead of direct fetch. If you really must hit the API directly, place the call in '@/lib/api-client' itself.",
    },
  ],
}
```

- [ ] **Step 3: Verify lint passes (no offending code yet so it should)**

Run: `pnpm lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add eslint.config.mjs
git commit -m "chore(lint): forbid direct fetch to the API in app code"
```

---

### Task 15: Add health route and verify

**Files:**
- Create: `career-flow-frontend/src/app/api/health/route.ts`

- [ ] **Step 1: Write the health route**

Write `src/app/api/health/route.ts`:
```ts
import { NextResponse } from "next/server"

export const dynamic = "force-dynamic"

export function GET() {
  return NextResponse.json({ status: "ok" })
}
```

- [ ] **Step 2: Verify locally**

Run: `pnpm dev` and curl `http://localhost:3000/api/health`.
Expected: `{"status":"ok"}`. Stop with Ctrl-C.

- [ ] **Step 3: Commit**

```bash
git add src/app/api/health/route.ts
git commit -m "feat(web): add /api/health route for Railway healthcheck"
```

---

### Task 16: Replace default homepage with a placeholder

**Files:**
- Modify: `career-flow-frontend/src/app/page.tsx`
- Modify: `career-flow-frontend/src/app/layout.tsx`

- [ ] **Step 1: Write placeholder homepage**

Replace `src/app/page.tsx` with:
```tsx
import { Button } from "@/components/ui/button"

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 px-6 text-center">
      <h1 className="text-balance text-4xl font-bold tracking-tight md:text-6xl">
        Career Flow is coming
      </h1>
      <p className="max-w-prose text-balance text-lg text-muted-foreground">
        We&apos;re rebuilding our coaching platform. Sign up for the waitlist or book a discovery
        call with one of our coaches.
      </p>
      <div className="flex flex-wrap items-center justify-center gap-4">
        <Button asChild>
          <a href="https://calendly.com/acakic92/30min" target="_blank" rel="noreferrer">
            Book a Discovery Call
          </a>
        </Button>
      </div>
    </main>
  )
}
```

- [ ] **Step 2: Update layout to set basic metadata**

Replace `src/app/layout.tsx` with:
```tsx
import "./globals.css"

import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" })
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" })

export const metadata: Metadata = {
  title: "Career Flow",
  description:
    "Career coaching that helps you navigate transitions, build confidence, and land your next role.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Step 3: Verify locally**

Run: `pnpm dev` and open `http://localhost:3000`.
Expected: placeholder page loads, "Book a Discovery Call" button works. Stop with Ctrl-C.

- [ ] **Step 4: Commit**

```bash
git add src/app/page.tsx src/app/layout.tsx
git commit -m "feat(web): add placeholder homepage with Calendly CTA"
```

---

### Task 17: Frontend `.env.example`

**Files:**
- Create: `career-flow-frontend/.env.example`

- [ ] **Step 1: Write .env.example**

Write `.env.example`:
```
# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# PostHog
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://eu.posthog.com

# Sentry
NEXT_PUBLIC_SENTRY_DSN=
SENTRY_AUTH_TOKEN=
SENTRY_ORG=
SENTRY_PROJECT=career-flow-frontend
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add .env.example for frontend"
```

---

### Task 18: Frontend `railway.toml`

**Files:**
- Create: `career-flow-frontend/railway.toml`

- [ ] **Step 1: Write railway.toml**

Write `railway.toml`:
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "pnpm start"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 2: Commit**

```bash
git add railway.toml
git commit -m "feat(deploy): add Railway service config for frontend"
```

---

### Task 19: Frontend GitHub Actions CI

**Files:**
- Create: `career-flow-frontend/.github/workflows/ci.yml`

- [ ] **Step 1: Write CI workflow**

Write `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main, staging]

env:
  PNPM_VERSION: 9
  NODE_VERSION: 20

jobs:
  install:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: pnpm
      - run: pnpm install --frozen-lockfile

  lint:
    runs-on: ubuntu-latest
    needs: install
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint

  typecheck:
    runs-on: ubuntu-latest
    needs: install
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm exec tsc --noEmit

  unit-test:
    runs-on: ubuntu-latest
    needs: install
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm test -- --run

  build:
    runs-on: ubuntu-latest
    needs: install
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm build
        env:
          NEXT_PUBLIC_API_URL: http://placeholder.local
          NEXT_PUBLIC_POSTHOG_KEY: phc_placeholder
          NEXT_PUBLIC_POSTHOG_HOST: https://eu.posthog.com
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: pk_test_placeholder
          CLERK_SECRET_KEY: sk_test_placeholder
          NEXT_PUBLIC_SENTRY_DSN: https://placeholder@sentry.io/0
```

- [ ] **Step 2: Add a placeholder Vitest test so the `unit-test` job has something to run**

Create `src/lib/__tests__/utils.test.ts`:
```ts
import { describe, expect, it } from "vitest"

import { cn } from "@/lib/utils"

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("px-2", "py-2")).toBe("px-2 py-2")
  })

  it("dedupes conflicting tailwind classes (last wins)", () => {
    expect(cn("px-2", "px-4")).toBe("px-4")
  })
})
```

Create `vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import path from "node:path"

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: false,
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/lib/api-client/**"],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
```

Add to `package.json` scripts:
```json
"test": "vitest"
```

Run: `pnpm add -D @vitejs/plugin-react`
Run: `pnpm test -- --run`
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add .github/ src/lib/__tests__/ vitest.config.ts package.json pnpm-lock.yaml
git commit -m "ci(frontend): add GitHub Actions workflow with lint, typecheck, test, build"
```

---

### Task 20: Push frontend to origin and confirm CI runs

- [ ] **Step 1: Push**

```bash
git push origin main
```

- [ ] **Step 2: Verify CI passes**

USER ACTION: open `https://github.com/AleksandarCakic/career-flow-frontend/actions`. Confirm all jobs passed.

---

## Phase 3 — Third-party glue (frontend)

### Task 21: PostHog provider

**Files:**
- Create: `career-flow-frontend/src/lib/posthog.ts`
- Create: `career-flow-frontend/src/components/providers/posthog-provider.tsx`
- Modify: `career-flow-frontend/src/app/layout.tsx`

- [ ] **Step 1: Create PostHog init module**

Write `src/lib/posthog.ts`:
```ts
"use client"

import posthog from "posthog-js"

let initialized = false

export function initPostHogClient(): typeof posthog {
  if (typeof window === "undefined") return posthog
  if (initialized) return posthog

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY
  const host = process.env.NEXT_PUBLIC_POSTHOG_HOST

  if (!key || !host) {
    if (process.env.NODE_ENV !== "production") {
      console.warn("[posthog] NEXT_PUBLIC_POSTHOG_KEY or NEXT_PUBLIC_POSTHOG_HOST not set")
    }
    return posthog
  }

  posthog.init(key, {
    api_host: host,
    person_profiles: "identified_only",
    capture_pageview: false, // we'll capture manually for SPA routing
    capture_pageleave: true,
    session_recording: {
      maskAllInputs: true,
    },
  })

  initialized = true
  return posthog
}

export { posthog }
```

- [ ] **Step 2: Create provider**

Write `src/components/providers/posthog-provider.tsx`:
```tsx
"use client"

import { usePathname, useSearchParams } from "next/navigation"
import { PostHogProvider as Provider } from "posthog-js/react"
import { Suspense, useEffect } from "react"

import { initPostHogClient, posthog } from "@/lib/posthog"

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initPostHogClient()
  }, [])

  return (
    <Provider client={posthog}>
      <Suspense fallback={null}>
        <PageviewTracker />
      </Suspense>
      {children}
    </Provider>
  )
}

function PageviewTracker() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!pathname) return
    const url = window.location.origin + pathname + (searchParams?.toString() ? `?${searchParams}` : "")
    posthog?.capture("$pageview", { $current_url: url })
  }, [pathname, searchParams])

  return null
}
```

- [ ] **Step 3: Add `posthog-js/react` to deps if not already**

Run: `pnpm add posthog-js`
(Note: `posthog-js/react` is a subpath of `posthog-js`.)

- [ ] **Step 4: Wrap layout with PostHogProvider**

Modify `src/app/layout.tsx`:
```tsx
import "./globals.css"

import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"

import { PostHogProvider } from "@/components/providers/posthog-provider"

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" })
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" })

export const metadata: Metadata = {
  title: "Career Flow",
  description:
    "Career coaching that helps you navigate transitions, build confidence, and land your next role.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <PostHogProvider>{children}</PostHogProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 5: Verify locally**

Run: `pnpm dev`, open http://localhost:3000 with PostHog dev tools open (or check Network → look for requests to `eu.i.posthog.com`).
Expected: pageview event fires.

- [ ] **Step 6: Commit**

```bash
git add src/lib/posthog.ts src/components/providers/posthog-provider.tsx src/app/layout.tsx
git commit -m "feat(web): add PostHog provider with SPA-aware pageview tracking"
```

---

### Task 22: Sentry SDK integration

**Files:**
- Run: Sentry's `npx @sentry/wizard@latest -i nextjs`

- [ ] **Step 1: Run the Sentry wizard**

```bash
cd career-flow-frontend
pnpm dlx @sentry/wizard@latest -i nextjs
```

Wizard prompts:
- Choose project: `career-flow-frontend`
- Reuse `SENTRY_AUTH_TOKEN`: yes (paste the token Sentry gave you)
- Org: your org
- Use existing Next.js config: yes
- Configure tunnel route: no for MVP (can add if you ever notice ad blockers eating events)

This adds `sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`, and modifies `next.config.mjs`.

- [ ] **Step 2: Update sentry.client.config.ts to scrub PII**

Find the `Sentry.init({...})` call and add:
```ts
beforeSend(event) {
  // Strip form-field values from breadcrumbs
  if (event.breadcrumbs) {
    event.breadcrumbs = event.breadcrumbs.filter(
      (b) => b.category !== "ui.input"
    )
  }
  return event
},
```

- [ ] **Step 3: Verify build**

Run: `pnpm build`
Expected: success. Sentry upload step will fail if the env vars are missing locally — that's fine, it'll work in CI/Railway with proper env vars.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(web): integrate Sentry SDK with PII scrubbing"
```

---

### Task 23: Clerk provider scaffolding (no admin UI yet)

**Files:**
- Modify: `career-flow-frontend/src/app/layout.tsx`
- Create: `career-flow-frontend/middleware.ts`

- [ ] **Step 1: Wrap layout in ClerkProvider**

Edit `src/app/layout.tsx`:
```tsx
import "./globals.css"

import { ClerkProvider } from "@clerk/nextjs"
import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"

import { PostHogProvider } from "@/components/providers/posthog-provider"

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" })
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" })

export const metadata: Metadata = {
  title: "Career Flow",
  description:
    "Career coaching that helps you navigate transitions, build confidence, and land your next role.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
          <PostHogProvider>{children}</PostHogProvider>
        </body>
      </html>
    </ClerkProvider>
  )
}
```

- [ ] **Step 2: Add middleware that protects /admin/\* even though those pages don't exist yet**

Write `middleware.ts` at the repo root:
```ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server"

const isAdminRoute = createRouteMatcher(["/admin(.*)"])

export default clerkMiddleware(async (auth, req) => {
  if (isAdminRoute(req)) {
    await auth.protect()
  }
})

export const config = {
  matcher: [
    // skip Next.js internals + static files
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
}
```

- [ ] **Step 3: Verify build**

Run: `pnpm build`
Expected: success.

- [ ] **Step 4: Commit**

```bash
git add src/app/layout.tsx middleware.ts
git commit -m "feat(auth): wire Clerk provider and middleware (no admin pages yet)"
```

---

### Task 24: OpenAPI client codegen setup (placeholder)

**Files:**
- Create: `career-flow-frontend/openapi-ts.config.ts`
- Modify: `career-flow-frontend/package.json` (add gen:api script)
- Create: `career-flow-frontend/src/lib/api-client/.gitignore`

- [ ] **Step 1: Create config**

Write `openapi-ts.config.ts`:
```ts
import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: process.env.OPENAPI_INPUT ?? "http://localhost:8000/openapi.json",
  output: {
    format: "prettier",
    path: "src/lib/api-client",
  },
  plugins: [
    "@hey-api/typescript",
    "@hey-api/sdk",
    {
      name: "@tanstack/react-query",
      asClass: true,
    },
  ],
})
```

- [ ] **Step 2: Add scripts**

Add to `package.json` scripts:
```json
"gen:api": "openapi-ts",
"gen:api:check": "git diff --exit-code src/lib/api-client"
```

- [ ] **Step 3: Create placeholder so the dir exists**

Write `src/lib/api-client/.gitignore`:
```
*.gen.ts
*.gen.json
```

Write `src/lib/api-client/index.ts`:
```ts
// Generated files (suffixed .gen.ts) are populated by `pnpm gen:api`.
// Hand-written re-exports go below.

// Placeholder until the backend has any real endpoints beyond /healthz.
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? ""
```

- [ ] **Step 4: Run codegen against the local backend (USER ACTION: backend must be running)**

In one terminal:
```bash
cd "../career-flow-backend"
uv run fastapi dev app/main.py
```

In another:
```bash
cd career-flow-frontend
pnpm gen:api
```

Expected: files appear under `src/lib/api-client/`. Since the backend only has `/healthz`/`/readyz`, there will be one or two simple methods. Verify `pnpm tsc --noEmit` still passes.

- [ ] **Step 5: Commit (only non-`.gen.*` files — those are gitignored)**

```bash
git add openapi-ts.config.ts package.json pnpm-lock.yaml src/lib/api-client/.gitignore src/lib/api-client/index.ts
git commit -m "feat(api): scaffold OpenAPI codegen pipeline with hey-api"
```

---

### Task 25: Playwright skeleton (smoke test for the placeholder homepage)

**Files:**
- Create: `career-flow-frontend/playwright.config.ts`
- Create: `career-flow-frontend/e2e/home.spec.ts`

- [ ] **Step 1: Install Playwright browsers**

Run:
```bash
pnpm exec playwright install --with-deps chromium
```

- [ ] **Step 2: Write playwright config**

Write `playwright.config.ts`:
```ts
import { defineConfig, devices } from "@playwright/test"

const PORT = process.env.PORT ?? "3000"
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${PORT}`

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",

  use: {
    baseURL,
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: "pnpm dev",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
      },
})
```

- [ ] **Step 3: Write smoke test**

Write `e2e/home.spec.ts`:
```ts
import { expect, test } from "@playwright/test"

test("homepage loads and shows the placeholder content", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Career Flow is coming")
  await expect(page.getByRole("link", { name: /Book a Discovery Call/i })).toHaveAttribute(
    "href",
    /calendly\.com/,
  )
})
```

- [ ] **Step 4: Add e2e script and run locally**

Add to `package.json`:
```json
"e2e": "playwright test",
"e2e:ui": "playwright test --ui"
```

Run: `pnpm e2e`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add playwright.config.ts e2e/ package.json
git commit -m "test(e2e): add Playwright skeleton with homepage smoke test"
```

---

## Phase 4 — Deploy to Railway

### Task 26: Connect both repos in Railway

**This phase is mostly USER ACTIONS in the Railway dashboard. I'll guide.**

- [ ] **Step 1: Create Postgres service**

In Railway UI: project `career-flow` → environment `production` → "+ New" → Database → Postgres. Name it `db`. Repeat for `staging`. Skip preview (Railway provisions a fresh DB per preview env automatically — see Step 5).

- [ ] **Step 2: Connect backend repo**

In Railway UI: production env → "+ New" → GitHub Repo → select `career-flow-backend`. Name the service `api`. Disable "Auto-Deploy" until env vars are set (next step).

- [ ] **Step 3: Set backend env vars (production)**

Service `api` → Variables. Add (paste actual values, not placeholders):
- `ENVIRONMENT=production`
- `DATABASE_URL=${{Postgres.DATABASE_URL}}` (Railway substitutes from the linked db service — use Railway's variable references syntax)
- `LOG_LEVEL=INFO`
- `CORS_ORIGINS=["https://career-flow.com","https://www.career-flow.com"]`
- `ADMIN_EMAILS=["acakic92@gmail.com","<partner-email>"]`
- `CLERK_SECRET_KEY=<from Clerk production env>`
- `CLERK_JWKS_URL=<from Clerk; the .well-known/jwks.json URL>`
- `STRIPE_SECRET_KEY=<leave empty for Week 1; we set in Week 6>`
- `STRIPE_WEBHOOK_SECRET=`
- `CALENDLY_WEBHOOK_SIGNING_KEY=`
- `RESEND_API_KEY=<from Resend>`
- `RESEND_FROM_INQUIRY=inquiry@career-flow.com`
- `RESEND_FROM_NOREPLY=noreply@career-flow.com`
- `RESEND_FROM_ONBOARDING=onboarding@career-flow.com`
- `SLACK_WEBHOOK_LEADS=<from Slack>`
- `SLACK_WEBHOOK_BOOKINGS=<from Slack>`
- `SLACK_WEBHOOK_PAYMENTS=<from Slack>`
- `SLACK_WEBHOOK_ALERTS=<from Slack>`
- `POSTHOG_API_KEY=<from PostHog>`
- `POSTHOG_HOST=https://eu.posthog.com`
- `SENTRY_DSN=<from Sentry backend project, production env>`
- `SENTRY_TRACES_SAMPLE_RATE=0.1`

- [ ] **Step 4: Enable auto-deploy from `main`**

Service `api` → Settings → Deploy → Trigger on push to `main`. Save.

- [ ] **Step 5: Repeat for staging environment**

Service `api` in staging → set the same vars but with staging-grade values (Sentry preview project, Stripe **test** keys empty for now, PostHog dev project key, etc.). Trigger on push to `staging` branch.

- [ ] **Step 6: Set up preview environments**

Project Settings → Pull Request Previews → enable for both repos. Railway will create a fresh env (including a Postgres) per PR.

- [ ] **Step 7: Connect frontend repo**

Repeat steps 2–6 for `career-flow-frontend`. Service name `web`. Production env vars:
- `NEXT_PUBLIC_API_URL=https://api.career-flow.com`
- `NEXT_PUBLIC_POSTHOG_KEY=<from PostHog>`
- `NEXT_PUBLIC_POSTHOG_HOST=https://eu.posthog.com`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<from Clerk production>`
- `CLERK_SECRET_KEY=<from Clerk production>`
- `NEXT_PUBLIC_SENTRY_DSN=<from Sentry frontend project, production>`
- `SENTRY_AUTH_TOKEN=<from Sentry>` (needed for source-map uploads at build time)
- `SENTRY_ORG=<your org slug>`
- `SENTRY_PROJECT=career-flow-frontend`

- [ ] **Step 8: Trigger first deploys**

In Railway UI, manually trigger deploys for `api` (production), `api` (staging), `web` (production), `web` (staging). Wait for green.

Verify the placeholder is up by visiting the Railway-provided URLs (e.g. `web-production-abc123.up.railway.app`). At this point custom domains aren't wired yet.

---

### Task 27: Configure custom domains and DNS

- [ ] **Step 1: Add custom domains in Railway**

For each environment + service, add:

**Production:**
- service `web` → custom domain `career-flow.com` and `www.career-flow.com`
- service `api` → custom domain `api.career-flow.com`

**Staging:**
- service `web` → custom domain `staging.career-flow.com`
- service `api` → custom domain `api.staging.career-flow.com`

Railway will give you a CNAME target for each (e.g. `web-production-abc123.up.railway.app`).

- [ ] **Step 2: Set DNS records in Cloudflare**

In Cloudflare DNS for `career-flow.com`:
- `CNAME www → <web-production CNAME>`, proxied (orange cloud)
- `CNAME api → <api-production CNAME>`, proxied
- `CNAME staging → <web-staging CNAME>`, proxied
- `CNAME api.staging → <api-staging CNAME>`, proxied
- For the apex `career-flow.com`: use Cloudflare's CNAME flattening — add `CNAME @ → <web-production CNAME>`, proxied

Also add the Resend records you saved in Phase 0.6:
- `TXT @ "v=spf1 include:_spf.resend.com ~all"`
- `TXT resend._domainkey <DKIM value from Resend>`
- `TXT _dmarc "v=DMARC1; p=none; rua=mailto:dmarc@career-flow.com"`

- [ ] **Step 3: Wait for SSL provisioning**

Railway provisions Let's Encrypt certs automatically once DNS resolves. Takes a few minutes.

- [ ] **Step 4: Verify everything**

```bash
curl https://career-flow.com
curl https://api.career-flow.com/healthz
curl https://staging.career-flow.com
curl https://api.staging.career-flow.com/healthz
```

Expected:
- `career-flow.com` returns the placeholder HTML
- `api.career-flow.com/healthz` returns `{"status":"ok"}`
- staging URLs same

If anything fails:
- DNS not yet propagated → wait 5 min
- SSL not yet issued → wait 5 min
- App actually failing → check Railway logs

- [ ] **Step 5: Verify Resend domain**

In Resend dashboard, click "Verify" on the domain. All three DNS records should turn green within a minute or two.

---

### Task 28: Verify Sentry receives events end-to-end

- [ ] **Step 1: Throw a test error from backend**

Add a temporary route to confirm Sentry works (we'll remove it).

Create `app/api/routes/_sentry_test.py`:
```python
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["_sentry_test"], include_in_schema=False)


@router.get("/_sentry-test")
async def sentry_test() -> dict[str, str]:
    raise HTTPException(status_code=500, detail="Sentry backend test error")
```

Wire it in `app/main.py` temporarily:
```python
from app.api.routes import _sentry_test as sentry_test_route
...
app.include_router(sentry_test_route.router)
```

Commit + push to staging, hit `https://api.staging.career-flow.com/_sentry-test`, then verify the error appears in Sentry's `career-flow-backend` project (staging environment).

- [ ] **Step 2: Throw a test error from frontend**

Add a button to the placeholder homepage that throws an error on click:
```tsx
<button
  type="button"
  onClick={() => {
    throw new Error("Sentry frontend test error")
  }}
  className="text-xs text-muted-foreground underline"
>
  (sentry test)
</button>
```

Push to staging, visit staging.career-flow.com, click the button, verify Sentry receives the error in the `career-flow-frontend` project (staging env).

- [ ] **Step 3: Remove both test endpoints**

Revert the backend route addition and the frontend button. Push to staging.

- [ ] **Step 4: Commit the revert**

```bash
# backend
git add -A && git commit -m "chore: remove sentry test endpoint after verification"
git push origin staging  # or main if you're cycling through
# frontend same
```

---

### Task 29: Set up UptimeRobot monitors

USER ACTION ONLY.

- [ ] **Step 1: Create monitors**

In UptimeRobot:
- `Career Flow Web (prod)` — GET `https://career-flow.com`, 5-min interval, alert via email + Slack webhook for `#alerts-all`
- `Career Flow API (prod)` — GET `https://api.career-flow.com/healthz`, 5-min interval, same alert contacts
- `Career Flow Web (staging)` — same for staging URL, longer interval (15 min), email-only

- [ ] **Step 2: Verify alert routing**

Manually pause one production monitor. Wait for an alert to fire to Slack/email. Re-enable.

---

## Phase 5 — Acceptance criteria

- [ ] All 28 prior tasks checked off (Phase 0 prereqs + Phases 1–4)
- [ ] `https://career-flow.com` and `https://staging.career-flow.com` return the placeholder homepage with TLS
- [ ] `https://api.career-flow.com/healthz` and `https://api.staging.career-flow.com/healthz` return `{"status":"ok"}` with TLS
- [ ] Both repos' GitHub Actions CI is green on `main` and `staging`
- [ ] Resend domain verified (all three DNS records green)
- [ ] Both PostHog projects receiving pageview events
- [ ] Both Sentry projects received the test error and were then cleaned up
- [ ] UptimeRobot monitors green and routing to Slack
- [ ] Slack `#alerts-all` channel has received: at least one CI notification (we'll add this in Week 2 properly), or at least one UptimeRobot alert from the verification step
- [ ] `.env.example` is committed in both repos and reflects exactly the env vars used in `app/core/config.py` (backend) and `src/lib/posthog.ts` / `sentry.client.config.ts` (frontend)
- [ ] Git identity fix applied (`user.name` and `user.email` properly set, not the auto-derived hostname value)

When all of the above are true, Week 1 is done. Ping me and we'll write Plan 2 (Marketing pages + design system).

---

## Notes for the implementing agent

- Follow `superpowers:test-driven-development` discipline: write the failing test first when a step asks for one.
- Follow `superpowers:verification-before-completion`: don't check a step off until you've run the command and seen the expected output.
- Commit frequently. Every task ends with a commit step on purpose.
- If you hit an unexpected error: don't shortcut it — invoke `superpowers:systematic-debugging` or `diagnose` to root-cause.
- USER ACTION steps must be done by Aleks; flag them in chat and wait for confirmation before proceeding.
- If a step's exact code/config no longer matches reality (a library updated and changed its API), invoke `superpowers:source-driven-development` to ground the fix in current official docs rather than guessing.
