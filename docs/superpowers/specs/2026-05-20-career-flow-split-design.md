# Career Flow — Backend/Frontend Split & Platform Design

**Date:** 2026-05-20
**Status:** Approved (brainstorming phase complete, awaiting implementation plan)
**Authors:** Aleksandar Cakic (acakic92@gmail.com)
**Affected repos:** `career-flow-backend`, `career-flow-frontend`
**Supersedes:** the v0 prototype at github.com/AleksandarCakic/v0-coaching-website

---

## 1. Summary

Career Flow is a small, two-coach career coaching practice (Aleksandar Cakic and a partner) selling 1-on-1 monthly coaching subscriptions ($1,200–$2,100/mo tiers) and one-time group cohorts ($800). The current site is a v0-generated Next.js prototype with no backend, hardcoded pricing, and a single Calendly link.

This spec defines the rewrite into a production architecture:

- **`career-flow-backend`** — Python 3.12 + FastAPI + PostgreSQL, deployed to Railway.
- **`career-flow-frontend`** — Next.js 16 + React 19 + TypeScript (strict), deployed to Railway.
- Coach-generated Stripe payment links (no public buy-now buttons), Calendly for scheduling, Resend for transactional email, Slack for internal alerts, PostHog for analytics, Clerk for admin auth, Sentry for errors.

v0 will be used as visual reference only; both repos are fresh rewrites with pragmatic best practices.

## 2. Goals

- Ship a production-quality marketing site that converts visitors into discovery-call bookings.
- Capture every lead in a Postgres database (not just email).
- Give both coaches a simple admin panel to send Stripe payment links after qualifying calls.
- Track every page view, click, funnel step, and conversion via PostHog with session replay.
- Notify the Slack workspace in real time for leads, bookings, and payments.
- Keep the architecture extensible for v2 features (Stripe Connect for external coaches, native mobile app, blog CMS, client accounts) without committing to them now.

## 3. Non-goals (deferred to v2)

- Native mobile app (Expo). Repo layout does not preclude it; we just don't build it.
- Stripe Connect / external-coach onboarding.
- Public self-serve "Buy Now" checkout on marketing pages.
- Client login / accounts (Stripe stores the customer; clients use Stripe's Customer Portal for cancellations).
- Per-coach custom package pricing (both coaches share platform-defined tiers in MVP).
- Headless CMS — blog content lives as MDX in the frontend repo.
- Subscription management UI in admin (Stripe Customer Portal covers this for clients).

## 4. MVP scope

### In MVP

- **Marketing site rewrite** with warm/minimal-premium visual direction. Pages: Home, How We Help (+ 1-on-1, Group sub-pages), Our Team, Coach Detail (`/our-team/[slug]`), Success Stories (DB-backed), Resources (email-gated PDF downloads), FAQ, Contact, Match-Me Quiz, Join Waitlist, Terms, Blog scaffolding (MDX-ready).
- **Two coach profiles** seeded in DB (Aleks + partner), each with their own Calendly URL.
- **Four packages** seeded: Navigator ($1,200/mo), Architect ($1,600/mo), Accelerator ($2,100/mo), Group Cohort ($800 one-time).
- **Admin panel** (Clerk-authenticated, 2-email allowlist): view leads, waitlist, quiz responses, bookings, payments, success stories; generate Stripe payment links.
- **Backend services**: lead capture, waitlist, quiz, resource gating with token-expiry, Stripe Checkout creation + webhook handler, Calendly webhook handler, Resend email sender, Slack alert dispatcher, PostHog server-side events.
- **Analytics**: PostHog browser SDK (autocapture, session replay, funnels) + server-side events for high-trust signals. Cookie banner.
- **Slack workspace** with `#leads`, `#bookings`, `#payments`, `#alerts-all` channels; backend posts via Incoming Webhooks.
- **Resource gating**: PDF download requires email; token issued via email, expires in 7 days.
- **Newsletter signup with double opt-in** via Resend.
- **Match-me-with-a-coach quiz** (5 questions, routes lead to best-fit coach, stored in `quiz_responses`).
- **Dynamic success stories** (DB-backed, manageable from admin).
- **Calendly webhook integration** — bookings stored in DB, Slack notified.
- **Blog with MDX content** — scaffolding plus 1–2 launch posts published.
- **Client community on Slack** — a *separate* Slack workspace (distinct from the internal coach workspace), clients receive a manual invite after their first successful payment. Automation deferred to v2.
- **CI/CD** via GitHub Actions, deployed to Railway with production + staging + ephemeral preview-per-PR environments.
- **Error tracking** via Sentry.
- **Uptime monitoring** via UptimeRobot (free tier).

### Out of MVP (v2)

See section 3.

## 5. Architecture overview

```
Internet
   │
   ├──► career-flow.com  ──────────► Next.js (Railway service "web")
   │                                       │
   │                                       │ HTTPS + Clerk session for /admin/*
   │                                       ▼
   ├──► api.career-flow.com  ──────► FastAPI (Railway service "api")
   │                                       │
   │                                       ├──► Postgres (Railway service "db")
   │                                       ├──► Stripe API
   │                                       ├──► Resend API
   │                                       ├──► Slack Incoming Webhooks
   │                                       ├──► PostHog (server-side events)
   │                                       └──► Sentry
   │
   └──► PostHog Cloud (analytics, scripts loaded in web)
```

**Key boundaries:**

- **Web ↔ API**: REST over HTTPS, JSON, all calls go through an auto-generated TypeScript client built from FastAPI's `/openapi.json` (via `@hey-api/openapi-ts` with TanStack Query plugin). ESLint bans direct `fetch` to the API in app code.
- **Web ↔ Clerk**: Clerk SDK on web validates session; Next.js middleware guards `/admin/*`; API verifies Clerk-issued JWT on every protected endpoint via Clerk's JWKS.
- **Web ↔ PostHog**: PostHog JS SDK in web. Backend can also send events server-side for high-trust signals (`payment.succeeded`, `lead.created`).
- **API ↔ Stripe**: All Stripe secret-key interactions through backend. Web never holds Stripe secret keys. Webhook signatures verified.
- **API ↔ Calendly**: Inbound webhooks only (signed). No outbound API calls in MVP.
- **API ↔ Resend**: Outbound only. Templates rendered as static HTML at frontend build time (via React Email), backend reads files and sends.
- **API ↔ Slack**: Outbound only. Incoming Webhook URLs in env vars, one per channel.
- **Domains**: `career-flow.com` + `www.career-flow.com` → web; `api.career-flow.com` → api. SSL via Railway's Let's Encrypt. DNS recommended via Cloudflare (CDN + DDoS).

## 6. Backend design

### Tech stack

- Python 3.12, FastAPI (async)
- Pydantic v2 for schemas
- SQLAlchemy 2.0 async + `asyncpg`
- Alembic for migrations
- pytest + pytest-asyncio for tests
- `uv` for dependency management (replaces pip)
- Ruff for lint + format (replaces black/isort/flake8)
- structlog for JSON logs
- Stripe Python SDK
- `respx` for HTTP mocking in tests

### Folder layout

```
career-flow-backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── public.py          # contact, waitlist, quiz, resource downloads, calendly-webhook
│   │   │   ├── admin.py           # all /admin/* endpoints (Clerk-protected)
│   │   │   ├── stripe.py          # checkout-session creation, webhook receiver
│   │   │   └── coaches.py         # public coach profiles + packages
│   │   └── deps.py                # FastAPI dependencies (DB session, Clerk auth)
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── base.py                # base class with created_at, updated_at, soft delete
│   │   ├── coach.py
│   │   ├── package.py
│   │   ├── lead.py
│   │   ├── waitlist_entry.py
│   │   ├── quiz_response.py
│   │   ├── booking.py
│   │   ├── payment.py
│   │   ├── stripe_event.py        # idempotency log
│   │   ├── success_story.py
│   │   └── resource_download.py
│   ├── schemas/                   # Pydantic models (separate from ORM)
│   ├── services/                  # business logic; no FastAPI imports here
│   │   ├── stripe_service.py
│   │   ├── calendly_service.py
│   │   ├── email_service.py       # wraps Resend; reads pre-rendered HTML templates
│   │   ├── slack_service.py       # wraps Slack incoming webhook
│   │   ├── posthog_service.py     # server-side events
│   │   └── pdf_service.py         # generates email-gated download tokens
│   ├── core/
│   │   ├── config.py              # Pydantic Settings
│   │   ├── db.py                  # async SQLAlchemy session
│   │   ├── clerk_auth.py          # JWT verification via JWKS
│   │   ├── logging.py             # structlog setup
│   │   └── errors.py              # BusinessError, exception handlers
│   ├── emails/                    # pre-rendered HTML templates (copied from frontend build)
│   ├── export_openapi.py          # CI script: dump openapi.json
│   └── main.py                    # FastAPI app, middleware, lifespan
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py                # async test DB, factories, Stripe mock setup
│   ├── unit/
│   │   └── services/
│   └── integration/
│       ├── test_stripe_webhook.py
│       ├── test_calendly_webhook.py
│       ├── test_contact_form.py
│       ├── test_admin_endpoints.py
│       └── test_resource_gating.py
├── docs/
│   ├── adr/                       # Architecture Decision Records
│   ├── agents/                    # configured by setup-matt-pocock-skills
│   └── superpowers/specs/         # this file
├── pyproject.toml                 # uv + deps + ruff config
├── alembic.ini
├── railway.toml
├── Dockerfile                     # multi-stage, non-root user
├── .env.example
├── .github/workflows/ci.yml
├── CLAUDE.md
├── CONTEXT.md
└── README.md
```

### Database schema

UUID primary keys everywhere. `created_at` and `updated_at` (timestamptz, UTC) on all tables via base model. Soft-delete (`deleted_at`) on `coaches` and `success_stories`. JSONB for variable-shape fields.

```sql
coaches (
    id uuid pk, email text unique not null, name text not null,
    slug text unique not null, bio_short text, bio_long text,
    headshot_url text, calendly_url text not null,
    is_active boolean default true, sort_order int default 0,
    deleted_at timestamptz, created_at timestamptz, updated_at timestamptz
);

packages (
    id uuid pk, name text not null, slug text unique not null,
    tier text not null check (tier in ('navigator','architect','accelerator','group')),
    pricing_model text not null check (pricing_model in ('subscription_monthly','one_time')),
    amount_cents int not null, currency text default 'USD',
    description text, features jsonb,
    stripe_product_id text, stripe_price_id text,
    is_active boolean default true,
    created_at timestamptz, updated_at timestamptz
);

leads (
    id uuid pk, name text not null, email text not null,
    subject text, message text,
    source_page text, posthog_distinct_id text,
    assigned_coach_id uuid fk → coaches(id),
    status text default 'new' check (status in ('new','contacted','qualified','booked','paid','lost')),
    created_at timestamptz, updated_at timestamptz
);

waitlist_entries (
    id uuid pk, email text not null,
    current_role text, years_of_experience text,
    biggest_challenge text, linkedin_profile text,
    coach_preference text, workshop_interests text[],
    posthog_distinct_id text,
    status text default 'new',
    created_at timestamptz
);

quiz_responses (
    id uuid pk, email text not null, answers jsonb not null,
    matched_coach_id uuid fk → coaches(id),
    posthog_distinct_id text,
    created_at timestamptz
);

bookings (
    id uuid pk, calendly_event_uri text unique not null,
    coach_id uuid fk → coaches(id),
    invitee_email text, invitee_name text,
    event_type text, scheduled_at timestamptz,
    status text default 'scheduled' check (status in ('scheduled','completed','canceled','no_show')),
    lead_id uuid fk → leads(id),
    created_at timestamptz, updated_at timestamptz
);

payments (
    id uuid pk,
    stripe_payment_intent_id text unique,
    stripe_customer_id text,
    stripe_subscription_id text,        -- nullable, only for subs
    stripe_checkout_session_id text,
    coach_id uuid fk → coaches(id),
    package_id uuid fk → packages(id),
    lead_id uuid fk → leads(id),
    amount_cents int, currency text,
    status text check (status in ('pending','succeeded','failed','refunded')),
    raw_event jsonb,                    -- last webhook event for debugging
    created_at timestamptz, updated_at timestamptz
);

stripe_events (                         -- idempotency
    id uuid pk, stripe_event_id text unique not null,
    event_type text, processed_at timestamptz default now(),
    raw_payload jsonb
);

success_stories (
    id uuid pk, client_name text, client_role_before text,
    client_role_after text, client_company_after text,
    headshot_url text, linkedin_url text,
    story_short text, story_long text,
    coach_id uuid fk → coaches(id),
    is_featured boolean default false, sort_order int default 0,
    published_at timestamptz, deleted_at timestamptz,
    created_at timestamptz, updated_at timestamptz
);

resource_downloads (
    id uuid pk, email text not null,
    resource_slug text not null,        -- "resume-guide", "linkedin-guide", "interview-prep"
    download_token text unique not null,
    expires_at timestamptz not null,    -- created_at + 7 days
    downloaded_at timestamptz,
    posthog_distinct_id text,
    created_at timestamptz
);
```

### Service layer

Each service is a class instantiated per-request via FastAPI dependency injection. Contains all business logic; routes are thin (parse input → call one service method → return).

```python
class StripeService:
    def __init__(self, stripe_client, db: AsyncSession):
        self.stripe = stripe_client
        self.db = db

    async def create_checkout_session_for_package(
        self, package: Package, client_email: str, coach: Coach
    ) -> str: ...

    async def handle_webhook(self, payload: bytes, sig_header: str) -> None: ...
```

### Endpoint groups

| Group | Endpoints | Auth |
|---|---|---|
| Public | `POST /contact`, `POST /waitlist`, `POST /quiz`, `POST /resources/{slug}/request`, `GET /resources/{slug}/download?token=`, `GET /coaches`, `GET /coaches/{slug}`, `GET /success-stories` | None |
| Admin | `GET/POST/PUT/DELETE /admin/leads`, `/admin/bookings`, `/admin/payments`, `/admin/success-stories`, `POST /admin/checkout-link` | Clerk JWT, email in `ADMIN_EMAILS` |
| Stripe | `POST /stripe/webhook` | Stripe signature |
| Calendly | `POST /calendly/webhook` | Calendly signature |
| Health | `GET /healthz`, `GET /readyz` | None |

## 7. Frontend design

### Tech stack

- Next.js 16 App Router, React 19
- TypeScript with `strict: true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`
- Tailwind CSS v4 + shadcn/ui primitives
- TanStack Query v5 for server state
- React Hook Form + Zod for forms
- Framer Motion for restrained, purposeful animation
- `next-themes` for dark-mode toggle
- Clerk SDK
- PostHog browser SDK
- Sentry browser SDK
- React Email for transactional email templates (compiled to static HTML, consumed by backend)
- `next/image` + sharp
- Vitest (unit) + Playwright (e2e, happy paths)
- pnpm package manager

### OpenAPI → strict TypeScript client

`@hey-api/openapi-ts` with the `@tanstack/react-query` plugin. CI verifies that committed client matches backend's current OpenAPI spec; PRs that drift will fail.

```
FastAPI /openapi.json
        │
        │ pnpm gen:api
        ▼
src/lib/api-client/
├── types.gen.ts        # exact TS types per Pydantic schema
├── services.gen.ts     # typed fetch functions
└── hooks.gen.ts        # TanStack Query hooks
```

All API calls in app code import from `lib/api-client`. Direct `fetch` to the API is forbidden via `no-restricted-imports`.

### Folder layout

```
career-flow-frontend/
├── app/
│   ├── (marketing)/                  # public site
│   │   ├── page.tsx                  # Home
│   │   ├── how-we-help/
│   │   │   ├── page.tsx
│   │   │   ├── one-on-one/page.tsx
│   │   │   └── group-coaching/page.tsx
│   │   ├── our-team/
│   │   │   ├── page.tsx
│   │   │   └── [slug]/page.tsx
│   │   ├── success-stories/page.tsx
│   │   ├── resources/[slug]/page.tsx
│   │   ├── faq/page.tsx
│   │   ├── contact/page.tsx
│   │   ├── quiz/page.tsx
│   │   ├── join-waitlist/page.tsx
│   │   ├── terms/page.tsx
│   │   └── blog/
│   │       ├── page.tsx
│   │       └── [slug]/page.tsx
│   ├── (admin)/admin/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── leads/page.tsx
│   │   ├── bookings/page.tsx
│   │   ├── payments/page.tsx
│   │   ├── success-stories/page.tsx
│   │   └── send-link/page.tsx
│   ├── api/
│   │   ├── download/[token]/route.ts
│   │   └── revalidate/route.ts
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                           # shadcn/ui primitives
│   ├── marketing/
│   └── admin/
├── content/blog/                     # MDX
├── lib/
│   ├── api-client/                   # generated
│   ├── schemas/                      # hand-written Zod
│   ├── posthog.ts
│   ├── clerk.ts
│   └── utils.ts
├── emails/                           # React Email components → static HTML at build
├── public/
├── e2e/                              # Playwright
├── tests/                            # Vitest
├── docs/
│   ├── adr/
│   ├── agents/
│   └── superpowers/specs/            # this file (copy)
├── next.config.mjs
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── pnpm-lock.yaml
├── .env.example
├── .github/workflows/ci.yml
├── CLAUDE.md
├── CONTEXT.md
└── README.md
```

### Rendering strategy

| Page | Strategy | Why |
|---|---|---|
| Home, How We Help, FAQ, Terms | SSG | Pure marketing, max SEO |
| Our Team, Coach Detail, Success Stories | ISR (on-demand revalidate + 1hr fallback) | DB-backed, rarely changes |
| Resources listing | SSG | Static config |
| Resource download | SSR | Request-time token validation |
| Contact, Quiz, Waitlist | SSG shell + client form | Interactive form on static shell |
| Admin pages | SSR force-dynamic | Per-user, behind auth |
| Blog | SSG from MDX | Static content from repo |

### State management

- Server state → TanStack Query
- Form state → React Hook Form + Zod
- UI state → React hooks per component
- Global UI state (theme, toast) → Zustand if needed; React Context otherwise
- Not using Redux or MobX

### Design tokens

Warm + minimal premium direction is locked. **Final brand palette decided at implementation kickoff via 5-variant mockup review:**

1. **Cream & Terracotta** — warm off-white background, deep terracotta primary, charcoal text.
2. **Sand & Forest** — warm sand background, deep forest green primary, ink text.
3. **Snow & Sage** — near-white background, sage green primary, dark slate text.
4. **Current v0 (reference baseline)** — dark purple gradient (`#261f4d → #6b5eab → #42425c`), magenta-purple primary (HSL 300 70 60), gold accent.
5. **Warm Purple** — cream background, deep aubergine-purple primary (≈ HSL 280 30 35), warm dusty rose accent. Inherits v0's purple identity but reads warm.

All variants will: drop translucent-black-on-gradient pattern; use tighter typographic scale; use 1-2 carefully-chosen accent colors; support optional dark mode.

### Performance + accessibility budgets

- Lighthouse Performance ≥ 80 (marketing); Accessibility ≥ 95; SEO ≥ 95; Best Practices ≥ 95
- First-load JS ≤ 100KB on marketing pages
- LCP < 2s on 4G
- All interactive elements keyboard-navigable, visible focus rings, ARIA labels for icon-only buttons
- Form fields use shadcn/ui Form components with proper labels and error messaging

## 8. Integrations

### Stripe

- One-time + subscription via Checkout Session. Customer Portal for cancellations.
- Secret key in backend env only.
- Webhook signature verified via `STRIPE_WEBHOOK_SECRET`.
- Coach uses Admin → *Send Link* → backend creates Checkout Session with package, client email, success/cancel URLs → returns hosted Stripe URL → backend emails client via Resend → client pays → Stripe webhook → `payments` row + Slack alert.
- Idempotency via `stripe_events` table on `event.id`.
- Stripe Connect deferred to v2.

### Calendly

- Link-only outbound (each coach's URL stored in `coaches.calendly_url`).
- Webhook subscriptions installed on each coach's account, pointing to `api.career-flow.com/calendly/webhook`.
- Signature verified via `CALENDLY_WEBHOOK_SIGNING_KEY`.
- `invitee.created` → `bookings` row + Slack `#bookings` + link to lead by email.
- `invitee.canceled` → status update.

### Resend

- API key in backend env.
- Domain `career-flow.com` verified in Resend (SPF, DKIM, DMARC TXT records in DNS).
- Sender addresses: `noreply@`, `inquiry@`, `onboarding@`.
- React Email templates live in `career-flow-frontend/emails/` (TSX components). `pnpm build:emails` renders each to a static `.html` file in `career-flow-frontend/emails/dist/`. A small GitHub Action in the frontend repo opens an automatic PR against `career-flow-backend` that updates `app/emails/*.html` whenever a template TSX file changes on `main`. Backend reads the HTML files and sends via Resend's Python SDK. CI in backend fails if `app/emails/*.html` is missing or stale relative to the latest frontend release tag.
- Failure → log to Sentry, retry 3× with exponential backoff in a background task. Form submitter not blocked.

### Slack

- One `career-flow` workspace.
- Channels: `#leads`, `#bookings`, `#payments`, `#alerts-all`.
- One Slack app with Incoming Webhooks scope; URLs per channel in env.
- Posts are fire-and-forget; failures logged but don't block the original action.
- Don't include payment amounts in `#leads`. `#payments` channel can include amounts (private channel for both coaches).

### PostHog

- PostHog Cloud, EU region (better GDPR posture).
- Browser SDK with autocapture + session replay + form-input masking.
- Server-side events for high-trust signals (`payment.succeeded`, `lead.created`, `booking.scheduled`).
- Identity stitching: `posthog_distinct_id` denormalized into `leads`, `waitlist_entries`, `quiz_responses`, `resource_downloads`.
- Cookie banner required for GDPR; PostHog respects opt-out.

### Clerk

- Admin auth only (2-user MVP).
- `@clerk/nextjs` on frontend, JWKS verification on backend.
- `ADMIN_EMAILS` env var is comma-separated allowlist. Enforced in both Next.js middleware AND backend dependency.
- When external coaches arrive: add `coaches.clerk_user_id` and adapt admin UI.

### Sentry

- DSN per environment (production, staging, preview).
- Auto-scrub PII, manually exclude form-field values via `beforeSend`.
- Release tagged with git SHA in CI.
- Free tier (5k errors/mo, 10k perf events/mo).

## 9. Deployment & CI/CD

### Railway topology

One Railway project `career-flow`, three environments (production, staging, preview-per-PR), three services per environment (`web`, `api`, `db`).

**Domains:**

| Domain | Service |
|---|---|
| `career-flow.com`, `www.career-flow.com` | web (production) |
| `api.career-flow.com` | api (production) |
| `staging.career-flow.com`, `api.staging.career-flow.com` | web/api (staging) |
| `*-pr-N.up.railway.app` | preview |

DNS recommended via Cloudflare (CDN + DDoS). SSL via Railway's Let's Encrypt.

### Branch strategy

- `main` → production (auto-deploy)
- `staging` → staging (auto-deploy)
- Feature branches → preview-per-PR (auto-create-and-destroy)
- Normal flow: `feature → staging → main`

### CI workflows (GitHub Actions)

**Backend `ci.yml`:**

- lint (ruff)
- typecheck (mypy)
- unit tests (pytest tests/unit)
- integration tests with Postgres service (pytest tests/integration)
- export OpenAPI and diff against committed `openapi.json` (fails if dev forgot to commit)
- Docker build

**Frontend `ci.yml`:**

- lint (ESLint)
- typecheck (`tsc --noEmit`)
- unit tests (Vitest)
- API-client sync: download `openapi.json` from backend's latest CI artifact, regenerate client, diff against committed (fails if backend drifted and frontend didn't regen)
- build (`next build`)
- Playwright e2e on preview deploy URL
- Lighthouse CI with enforced budgets

### Migrations

- Alembic, auto-run on deploy (`alembic upgrade head` before uvicorn starts).
- Every PR touching `app/models/` must include a migration; CI runs `alembic check`.
- Forward-only.

### Secrets

All in Railway env vars, per environment. Local `.env.local` uses preview keys. `.env.example` in each repo lists required vars (placeholders only).

## 10. Testing & observability

### Backend tests

Coverage target: ~70% overall, 95%+ on `services/`, 20% on `routes/`.

- Unit tests for services with HTTP mocks (`respx`) and Stripe mock (`stripe-mock`).
- Integration tests against real Postgres in CI (`pytest-postgresql` or Docker).
- TDD discipline: red → green → refactor for every endpoint, enforced by `superpowers:test-driven-development` skill.

### Frontend tests

- Vitest: Zod schemas, utility functions only. Skip component rendering / snapshots.
- Playwright (Chromium only for MVP): home loads, contact form submits, waitlist submits, quiz completes, resource gating works end-to-end, admin login enforces allowlist, send-link generates URL.
- Lighthouse CI enforces budgets in section 7.

### Error handling

Backend error categories:

1. **Validation (422)** — auto-handled by Pydantic, log INFO, no alert.
2. **Business rule errors** (`BusinessError` subclass) — custom 4xx with `{error, message}` JSON, log WARNING, no alert.
3. **Infrastructure** — generic 500, log ERROR + Sentry, Slack alert if rate spikes.

Frontend:

- TanStack Query handles network errors uniformly → Sonner toast with retry.
- Error Boundary at layout level → fallback UI + Sentry.
- Form errors inline at field level.
- Critical mutations (send-link) require confirmation + disable on submit.

### Observability stack

| Signal | Tool |
|---|---|
| Errors | Sentry |
| Application logs (JSON) | Railway log viewer |
| Performance traces | Sentry + PostHog Web Vitals |
| Business events | PostHog + Slack |
| Pageviews + funnels + replays | PostHog |
| Uptime | UptimeRobot (free, 5-min interval) |
| DB performance | Railway dashboard |

### Slack alert rules

| Condition | Channel |
|---|---|
| Backend 5xx > 1% over 5min | `#alerts-all` |
| Stripe webhook signature failure | `#alerts-all` |
| New lead | `#leads` |
| New booking (Calendly) | `#bookings` |
| Payment succeeded | `#payments` |
| Payment failed | `#payments` + `#alerts-all` |
| Uptime down | email + `#alerts-all` |
| CI on `main` fails | `#alerts-all` |

## 11. Phased rollout plan

| Week | Milestone |
|---|---|
| **1** | Repo scaffolding. Backend: FastAPI shell, Alembic init, pytest config, Dockerfile, Railway deploy of `/healthz`. Frontend: Next.js init, TS strict, Tailwind v4, shadcn/ui setup, Clerk scaffold, Railway deploy of placeholder. Both repos: GitHub Actions CI, `.env.example`, Sentry integration, Resend domain verified, DNS for `career-flow.com` + `api.career-flow.com`. |
| **2** | Marketing pages (visual rebuild). Mock 5 brand variants → user picks one → lock design tokens. Home, How We Help (+ sub-pages), Our Team (static placeholder), FAQ, Terms — all SSG. PostHog client + cookie banner. Calendly link CTAs. Lighthouse budgets passing. |
| **3** | DB + coaches + packages. Migrations for `coaches`, `packages`. Seed Aleks + partner + 4 packages. Dynamic `/our-team/[slug]` wired to API via generated client. Success stories table + page (DB-backed). |
| **4** | Lead capture. Contact + waitlist + quiz forms wired to backend, replacing v0's Resend server actions. Resend email templates (React Email). Slack `#leads` alerts. PostHog event linking via `posthog_distinct_id`. |
| **5** | Admin panel basics. Clerk auth + `ADMIN_EMAILS` enforced both sides. Leads/waitlist/quiz/success-stories viewers. Send-payment-link UI (pick package, enter email, click → URL emailed). |
| **6** | Stripe integration. Stripe products/prices seeded from packages table via setup script. Checkout Session endpoint. Webhook handler with idempotency. Payment log. Slack `#payments` alerts. Customer Portal link in confirmation emails. |
| **7** | Calendly + resource gating. Calendly webhook handler → `bookings`. Slack `#bookings`. Lead-by-email linking. Resource downloads: email-gated, 7-day token. Migrate 3 PDFs from v0. |
| **8** | Polish + launch. All Playwright e2e green. Lighthouse thresholds met. Sentry release tracking. UptimeRobot configured. Final warm/minimal theme polish. Staging validation. DNS cutover from v0 to `career-flow.com` production. |
| **9** | MVP closeout. Newsletter signup form + Resend Broadcasts double opt-in. MDX blog scaffolding + 1–2 launch posts published. PostHog dashboards built out for the admin home view. Client-community Slack workspace created; manual invite flow documented (Stripe webhook posts to `#payments` with a reminder to invite the new client). Final accessibility + SEO audit. |

**Total: ~9 weeks for full MVP.** Weeks 1–8 deliver the conversion-critical path; Week 9 closes out the secondary-priority MVP features.

## 12. Cost summary (monthly recurring)

| Service | Production | Staging | Notes |
|---|---|---|---|
| Railway web | $5–10 | $3 | Usage-based |
| Railway api | $5 | $3 | Usage-based |
| Railway Postgres | $5 | $5 | Shared CPU tier |
| Clerk | $0 | $0 | Free under 10k MAU |
| Resend | $0 | $0 | Free 3k emails/mo |
| Sentry | $0 | $0 | Free 5k errors/mo |
| PostHog Cloud | $0 | $0 | Free 1M events/mo |
| Slack (internal coach workspace) | $0 | — | Free tier |
| Slack (client community workspace) | $0 | — | Free tier; manual invites in MVP |
| Cloudflare DNS + CDN | $0 | $0 | Free tier sufficient |
| UptimeRobot | $0 | — | Free 50 monitors |
| GitHub Actions | $0 | — | Free 2k min/mo |
| Stripe | per-transaction | per-transaction | 2.9% + $0.30 |
| Calendly | $10–15/coach | — | User's existing |
| **Total infra** | **~$15–20** | **~$11** | **~$25–35/mo** |

Domain registration ~$15/year. Total <$40/mo before transaction fees and Calendly.

## 13. Deferred decisions

These are intentionally not resolved in this spec; they'll be addressed at the noted milestones.

| Decision | When |
|---|---|
| Final brand color palette (1 of 5 variants) | Week 2 implementation kickoff |
| Specific MDX blog content + voice | Week 9 |
| Stripe Connect onboarding flow (v2) | When first external coach is onboarded |
| Native mobile app — Expo, frontend monorepo restructure (v2) | When app development starts |
| Headless CMS migration from MDX (v2) | When non-technical authors need to publish |
| Client login + dashboard (v2) | When clients ask for booking history visibility |
| Subscription self-management UI in admin (v2) | When Stripe Customer Portal is insufficient |
| EU vs US Slack/PostHog data residency review (v2) | Before scaling to EU clients in volume |

## 14. References

- v0 prototype: `github.com/AleksandarCakic/v0-coaching-website`
- Current pricing pages: `app/how-we-help/one-on-one/page.tsx`, `app/how-we-help/group-coaching/page.tsx` in v0 repo
- Existing Calendly URL: `calendly.com/acakic92/30min`
- Setup of agent-skills configuration: `docs/agents/` (both repos)
