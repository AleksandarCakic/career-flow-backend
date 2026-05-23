# Career Flow — outstanding TODOs

Open items that aren't blocking current dev but need to be done before launch.
Mirror of this file lives in the frontend repo. Keep both in sync.

## User actions still pending

### UptimeRobot signup (Stage 3 of user prereqs)
- **Status**: deferred — uptimerobot.com was unreachable when we first tried (their site was down).
- **Action**: when their site is back, sign up at https://uptimerobot.com using `ops@career-flow.com`. Save credentials in the `Career Flow — Operations` NordPass folder.
- **Monitors to add after Railway is live**:
  - `Career Flow Web (prod)` — GET `https://career-flow.com` — 5-min interval — alerts: email + Slack `#alerts-all` webhook
  - `Career Flow API (prod)` — GET `https://api.career-flow.com/healthz` — 5-min — same alerts
  - `Career Flow Web (staging)` — GET `https://staging.career-flow.com` — 15-min — email only
  - `Career Flow API (staging)` — GET `https://api.staging.career-flow.com/healthz` — 15-min — email only

### PDFs for resource gating
- **Status**: deferred. Backend's `/resources/{slug}/download` endpoint works but returns a JSON placeholder instead of a PDF until files are added.
- **Action**: Generate or locate the three PDFs (v0 repo's `scripts/generate-*-pdf.py` produces them). Place into `career-flow-backend/app/resources_static/`:
  - `resume-guide.pdf`
  - `linkedin-guide.pdf`
  - `interview-prep.pdf`
- Commit + push. Next deploy serves them.

### Brand palette decision
- **Status**: deferred. All five variants exist as switchable themes. Default is `cream-terracotta`.
- **Action**: review at `https://career-flow.com/design-preview` (after deploy) or locally via `?theme=<slug>`. Five candidates:
  - `cream-terracotta` (default)
  - `sand-forest`
  - `snow-sage`
  - `v0-current` (reference baseline)
  - `warm-purple`
- Once decided: tell the agent which slug, and they'll promote it to `:root` in `globals.css` and remove the unused variant scopes.

## Engineering follow-ups

### Skipped integration test
`tests/integration/test_public_endpoints.py::test_list_success_stories_omits_unpublished` is currently `@pytest.mark.skip`'d. Reason: asyncpg/SQLAlchemy raises "another operation in progress" when this test exercises both `db_session` and an HTTP request in the same coroutine. Endpoint is verified manually via curl. Revisit when migrating to pytest-asyncio session loop with explicit engine disposal.

### Coach.expertise not in backend schema
`Coach.expertise` (the specialty tags shown on `/our-team`) lives only in the frontend's static `lib/coaches.ts`. Currently merged onto API coach records by matching slugs. Decide whether to:
- Add as a `coaches.expertise` jsonb column in a new migration, OR
- Leave in the frontend forever (acceptable — these tags rarely change)

### Clerk Production instance — decided no (2026-05-23)
- **Status**: won't do. Staying on Clerk dev instance permanently.
- **Why**: Pro tier ($25/mo) is the only way to get a custom Clerk domain (`clerk.career-flow.com`) and `pk_live_...` keys. For the MVP and likely forever, only the two coach accounts need admin sign-in — the dev instance's MAU limits aren't a concern, and signing in via `*.clerk.accounts.dev` is acceptable for an internal-only surface.
- **Implication**: never need to swap to `pk_live_...` / `sk_live_...`. If we ever launch client-facing accounts (currently out of MVP scope per spec §3), revisit.
