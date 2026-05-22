# Week 5 — Admin panel (auth + read-only listings)

> Executed inline 2026-05-22. Use `superpowers:subagent-driven-development` only if rerunning.

**Goal:** Stand up an authenticated admin surface that lets the two coaches see every lead, waitlist signup, quiz response, booking, payment, and success story that the system has captured. Read-only first; write actions (status changes, Stripe link generation, success-story CRUD) come in Week 6+.

**Architecture:** Backend exposes a new `/admin/*` route group protected by a Clerk-JWT-verifying dependency that also gates on an email allowlist (`settings.admin_emails`). Frontend ships an `/admin` shell (Clerk-protected via existing middleware) with a sidebar nav and one page per entity. Server components fetch via the generated TS client, passing the Clerk session token through.

**Spec reference:** `docs/superpowers/specs/2026-05-20-career-flow-split-design.md` §6 (Admin panel scope).

---

## Tasks

- [ ] **Task 1**: `app/core/security.py`. Implements Clerk JWT verification against the JWKS endpoint (cached `httpx` client, signature + `iss`/`aud`/`exp` claim checks via PyJWT). Exposes `require_admin` FastAPI dep that returns the claims dict on success, raises 401 on bad token, 403 if `email` claim isn't in `settings.admin_emails`. Unit-tested with mocked JWKS + signed test tokens.
- [ ] **Task 2**: `app/api/routes/admin.py`. Paginated GET endpoints (`?limit=50&offset=0`, max limit 200):
  - `GET /admin/leads` — newest first; includes assigned coach slug if any.
  - `GET /admin/waitlist` — newest first; includes parsed `workshop_interests`.
  - `GET /admin/quiz-responses` — newest first; includes matched coach slug.
  - `GET /admin/bookings` — by `scheduled_at` desc; joins lead email when available.
  - `GET /admin/payments` — newest first; joins coach + package slugs; cents → dollars in response.
  - `GET /admin/success-stories` — newest first; includes coach slug + `published_at`.
  - All return `{items: [...], total: int, limit: int, offset: int}`.
- [ ] **Task 3**: `app/schemas/admin.py`. `Out`-only response schemas for each list (`LeadAdminRead`, `WaitlistAdminRead`, etc.) and a generic `AdminListResponse[T]` envelope.
- [ ] **Task 4**: `tests/integration/test_admin.py`. For each endpoint cover: 401 with no token; 403 with token whose email isn't admin; 200 with admin token; pagination (offset/limit honored); newest-first ordering. JWKS mocked via `respx`; tokens signed locally with a test RSA key.
- [ ] **Task 5**: Frontend shadcn primitives. Add `table`, `dialog`, `tabs`, `badge`, `dropdown-menu` via `pnpm dlx shadcn@latest add ...` (and `drawer` if not already in via `sheet`).
- [ ] **Task 6**: `src/app/admin/layout.tsx` + `src/components/admin/sidebar.tsx`. Sidebar lists: Dashboard, Leads, Waitlist, Quiz, Bookings, Payments, Success Stories. Header shows Clerk `<UserButton/>`. Uses existing theme tokens.
- [ ] **Task 7**: `pnpm gen:api` to regenerate the TS client against the new `/admin/*` routes. Commit the diff.
- [ ] **Task 8**: One page per entity under `src/app/admin/`:
  - `page.tsx` (dashboard): counts + 5 most recent rows of each list.
  - `leads/page.tsx`, `waitlist/page.tsx`, `quiz/page.tsx`, `bookings/page.tsx`, `payments/page.tsx`, `success-stories/page.tsx`: server components, render the relevant Table. Click a row → `Sheet` (right drawer) with full record. Empty states with helpful copy. Pagination via query string (`?page=2`).
- [ ] **Task 9**: Pass Clerk token through to API on server. Use `auth().getToken({ template: ... })` from `@clerk/nextjs/server` and forward as `Authorization: Bearer` header on the generated client config.

## Acceptance criteria

- [ ] Backend: mypy strict + ruff clean; all integration tests green.
- [ ] Backend: `GET /admin/leads` returns 401 without token, 403 with non-admin token, 200 + paginated payload with admin token.
- [ ] Frontend: `pnpm build` / lint / typecheck green; visiting `/admin` while signed-in shows the dashboard with live counts.
- [ ] Visiting `/admin` while signed out redirects to Clerk sign-in (middleware behavior already in place).
- [ ] Visiting `/admin` while signed in with a non-allowlisted email shows a friendly 403 view (not a server crash).

## Deferred / handed back to user

- [ ] **Stripe** — payment-link generation endpoint + webhook handler. Blocked on: user has not yet provided `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`. Resume when keys are in Railway env vars.
- [ ] **Calendly webhook** — booking ingest. Blocked on: webhook URL must be registered in Calendly *after* the endpoint exists and *after* the api has a public URL (currently `*.up.railway.app` — fine for now; will swap to `api.career-flow.com` after DNS).
- [ ] **Admin write actions** — status changes on leads, marking success stories published/unpublished, etc. Out of Week 5 scope; planned for Week 6.
- [ ] **PostHog server-side events for admin actions** — defer until write actions exist (nothing meaningful to log yet).

## Files added / modified (planned)

Backend:
- `app/core/security.py` (new)
- `app/api/routes/admin.py` (new) + register in `app/main.py`
- `app/schemas/admin.py` (new)
- `tests/integration/test_admin.py` (new)
- `tests/unit/test_security.py` (new)

Frontend:
- `src/app/admin/layout.tsx` (new) + page files for each entity
- `src/components/admin/sidebar.tsx` (new)
- `src/components/ui/{table,dialog,tabs,badge,dropdown-menu}.tsx` (shadcn add)
- `src/lib/admin-fetch.ts` (new) — thin wrapper that attaches Clerk Bearer token
- `src/lib/api-client/**/*.gen.ts` (regenerated)
