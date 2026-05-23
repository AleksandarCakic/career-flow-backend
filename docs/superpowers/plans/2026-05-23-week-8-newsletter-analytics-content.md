# Week 8 — Newsletter double opt-in, PostHog browser, blog launch, CSV export

> Executed inline 2026-05-23. Single combined PR per repo.

**Goal:** Ship every MVP item from the spec that doesn't need external secrets (Stripe / Calendly / Slack workspace) or DNS. That leaves: full analytics loop (server-side already done, browser side now), GDPR-style cookie banner, newsletter double opt-in, two real blog launch posts, and a CSV export so the coaches can pull leads out of the admin into their inbox / spreadsheet of choice.

**Architecture:**
- Backend: `NewsletterSubscription` model + migration. Three endpoints under `/newsletter/*` — subscribe (sends confirmation email via existing Resend wrapper), confirm (token-validated, marks `confirmed_at`), unsubscribe (token-validated, marks `unsubscribed_at`). PostHog events on each step. CSV export endpoints under `/admin/{leads,waitlist}/export.csv` that stream via `StreamingResponse`. Fix the long-skipped success-story integration test.
- Frontend: `posthog-js` properly initialized in the existing `PostHogProvider` (autocapture + session recording with form masking; no-ops when key unset). New `CookieBanner` client component gates PostHog opt-in/opt-out via localStorage. `NewsletterForm` component on the marketing footer + dedicated `/newsletter/confirm` and `/newsletter/unsubscribe` pages. Two MDX launch posts under `content/blog/`. "Export CSV" buttons on `/admin/leads` and `/admin/waitlist` preserving active filters.

**Spec reference:** `docs/superpowers/specs/2026-05-20-career-flow-split-design.md` §4 (analytics, newsletter, blog), §6 (admin export).

---

## Tasks

### Backend (single PR `feat/newsletter-csv-and-polish`)

- [ ] **Task 1**: `app/models/newsletter_subscription.py` + Alembic migration. Columns: `id`, `email` (indexed), `confirmation_token` (unique), `confirmed_at`, `unsubscribed_at`, `posthog_distinct_id`, `source` (string — "footer", "blog-cta", etc.), timestamps. Multiple rows per email allowed (re-subscribe creates a new row); list-management logic queries the latest non-unsubscribed row.
- [ ] **Task 2**: `app/services/newsletter_service.py` — create, find_by_token, confirm, unsubscribe. Token generation via `secrets.token_urlsafe(32)`.
- [ ] **Task 3**: `app/api/routes/newsletter.py` — POST /subscribe (idempotent against latest unconfirmed for same email — re-sends the email), GET /confirm?token=, GET /unsubscribe?token=. Confirmation email via existing `EmailService` with proper unsubscribe link. PostHog events `newsletter.subscribe_requested`, `newsletter.subscribe_confirmed`, `newsletter.unsubscribed`.
- [ ] **Task 4**: `app/schemas/newsletter.py` — Pydantic request/response shapes.
- [ ] **Task 5**: `app/api/routes/admin.py` — `GET /admin/leads/export.csv` and `/admin/waitlist/export.csv`. StreamingResponse. Honors the same filter params as the list endpoints (for leads).
- [ ] **Task 6**: Fix `tests/integration/test_public_endpoints.py::test_list_success_stories_omits_unpublished` — currently `@pytest.mark.skip`'d because the test exercises both `db_session` and an HTTP request in the same coroutine, hitting asyncpg "another operation in progress". Diagnose and fix.
- [ ] **Task 7**: Integration tests for newsletter endpoints + CSV exports.

### Frontend (single PR `feat/analytics-newsletter-blog-csv`)

- [ ] **Task 8**: `PostHogProvider` — actually initialize `posthog-js` with NEXT_PUBLIC_POSTHOG_KEY + host. Defaults: `autocapture: true`, `session_recording: { maskAllInputs: true }`, `capture_pageview: true`. Skip init when key unset.
- [ ] **Task 9**: `CookieBanner` component + storage key `cf-cookie-consent` (`accepted` | `declined`). When declined, calls `posthog.opt_out_capturing()`. When dismissed/never decided, banner reappears next page load.
- [ ] **Task 10**: `NewsletterForm` client component. Calls `POST /newsletter/subscribe` via `src/lib/api-submit.ts`. Inline success / error states. Add to the marketing footer.
- [ ] **Task 11**: `/newsletter/confirm` and `/newsletter/unsubscribe` route handlers. Server-side fetch to the backend with the `token` query param; render success/error inline. `noindex` meta.
- [ ] **Task 12**: Two MDX posts under `content/blog/`. Frontmatter matches existing post structure. Real long-form coaching content, not lorem.
- [ ] **Task 13**: `ExportCsvButton` component on `/admin/leads` and `/admin/waitlist`. Triggers a download via a server action that proxies the CSV stream (so the Clerk token stays server-side).

## Acceptance criteria

- [ ] Backend ruff/format/mypy/unit tests all clean. New integration tests pass against local Postgres.
- [ ] `POST /newsletter/subscribe` returns 201 + creates a row; confirmation email sent (when RESEND_API_KEY set). `GET /newsletter/confirm?token=<valid>` sets `confirmed_at` and returns 200.
- [ ] Frontend lint/typecheck/build clean.
- [ ] Visiting any marketing page shows the cookie banner on first visit only; declining stops PostHog network calls.
- [ ] Newsletter form on the footer submits, shows "Check your email" success state.
- [ ] `/blog` lists at least two posts; each post page renders without error.
- [ ] Admin "Export CSV" button downloads a valid CSV that matches the current filters.

## Out of scope

- Stripe / Calendly (per user instruction)
- Slack workspace setup / webhook URL config (user action)
- Custom domains / DNS / UptimeRobot (user action)
- React Email migration of existing inline-HTML templates (deferred to Week 9 polish)
- Admin: bookings / payments edit affordances (wait for those data sources)
