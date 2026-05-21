# Week 4 — Lead capture (contact, waitlist, quiz)

> Executed inline 2026-05-21. Use `superpowers:subagent-driven-development` only if rerunning.

**Goal:** Replace the local-only form acknowledgements with real backend submissions. Contact, waitlist, and quiz forms write rows to the database, fire a Slack alert to `#leads`, and (where relevant) send a confirmation email via Resend. All third-party calls degrade gracefully when credentials are missing so dev / preview environments keep working until Phase 0 prereqs land in Railway env vars.

**Architecture:** Three POST endpoints under `/contact`, `/waitlist`, `/quiz`. Each parses a Pydantic model with `EmailStr`, delegates persistence to `LeadService`, and then fires Slack + email side-effects via thin wrappers (`SlackService`, `EmailService`). Wrappers use httpx for outbound HTTP with a short timeout and log warnings on failure instead of raising — submissions succeed even if Slack/Resend is down. Frontend forms call the API via `src/lib/api-submit.ts` and surface loading + error states.

**Spec reference:** `docs/superpowers/specs/2026-05-20-career-flow-split-design.md`

---

## Tasks

- [x] **Task 1**: `app/services/email_service.py` + `app/services/slack_service.py`. Both no-op + warn when credentials are missing; both call out via httpx with sensible timeouts.
- [x] **Task 2**: Lead capture endpoints. `POST /contact` (validates name/email/subject/message length); `POST /waitlist` (validates role/experience/challenge + accepts optional LinkedIn / coach preference / workshop interests); `POST /quiz` (accepts arbitrary JSON answers + matched coach slug; looks up coach to FK the response). All return `201` with `{id}`.
- [x] **Task 3**: Integration tests. `tests/integration/test_lead_capture.py` covers happy path for each endpoint + 422 rejections for short message / bad email. Uses `respx` to mock Resend and Slack endpoints.
- [x] **Task 4**: Frontend wiring. `src/lib/api-submit.ts` exposes typed `submitContact`, `submitWaitlist`, `submitQuiz`. ContactForm and WaitlistForm replace local-only acks with API calls. QuizClient adds an opt-in email gate on the results screen so we only capture quiz responses when the user actively asks us to follow up. PostHog `lead.contact_submitted`, `lead.waitlist_submitted`, `quiz.completed`, and `quiz.email_saved` events fire on success.

## Acceptance criteria

- [x] `POST /contact|/waitlist|/quiz` all return 201 with a UUID id against locally-seeded Postgres
- [x] Email + Slack wrappers no-op silently when `RESEND_API_KEY` / `SLACK_WEBHOOK_*` are unset
- [x] mypy strict + ruff clean across 40 source files (backend); 9 integration tests passing
- [x] Frontend `pnpm build` / lint / typecheck all green; forms render and submit
- [x] PostHog events fire on lead-capture success
- [x] `exactOptionalPropertyTypes` satisfied in all submit calls (optional values spread, not assigned `| undefined`)

## Deferred / handed back to user

- [ ] Set `RESEND_API_KEY` in Railway env so confirmation emails actually send. The Resend domain `career-flow.com` is verified per Phase 0; we just need the API key wired in.
- [ ] Set the four `SLACK_WEBHOOK_*` URLs in Railway env so `#leads` alerts fire. Done once the Slack app + incoming webhooks are created (Phase 0 step 5).
- [ ] Once both are wired, do an end-to-end smoke against `staging.career-flow.com/contact` — fill in the form, confirm DB row, Slack alert, and confirmation email all arrive.

## Files added / modified

Backend:
- `app/services/email_service.py`, `app/services/slack_service.py`
- `app/schemas/lead.py`, `app/services/lead_service.py`
- `app/api/routes/public.py` (contact / waitlist / quiz)
- `app/main.py` wires `public.router`
- `pyproject.toml` adds `email-validator`
- `tests/integration/test_lead_capture.py`

Frontend:
- `src/lib/api-submit.ts`
- `src/components/marketing/{contact-form,waitlist-form,quiz-client}.tsx`
- `eslint.config.mjs` carves out `src/lib/api-submit.ts` from no-fetch
