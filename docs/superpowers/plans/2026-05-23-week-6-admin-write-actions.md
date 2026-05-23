# Week 6 — Admin write actions

> Executed inline 2026-05-23. Use `superpowers:subagent-driven-development` only if rerunning.

**Goal:** Make the admin panel useful for day-to-day operations. Coaches can change lead status, assign / reassign leads to themselves or each other, and fully manage success stories (create, edit, publish/unpublish, soft delete) without DB surgery. Stripe and Calendly remain deferred until the user provides those keys.

**Architecture:** Backend exposes three new write paths under `/admin/*` (lead update, success-story CRUD, admin coach listing). Frontend uses Next.js server actions to wrap each, react-hook-form + zod for form state, and the shadcn `Sheet` primitive as a right-side detail drawer launched from clicking a row.

**Spec reference:** `docs/superpowers/specs/2026-05-20-career-flow-split-design.md` §6 (admin scope).

---

## Tasks

- [ ] **Task 1**: `PATCH /admin/leads/{id}` in `app/api/routes/admin.py`. Body `{status?: LeadStatus, assigned_coach_id?: UUID | null}` — both optional, partial update semantics. Validates coach exists if provided. Returns the joined `LeadAdminRead`. 404 if lead missing, 422 if coach id is malformed or unknown.
- [ ] **Task 2**: `GET /admin/coaches` returning *every* coach (including `is_active=False`) so admins can reassign to inactive ones if needed. New schema `CoachAdminRead` (mirrors the public one plus `is_active`).
- [ ] **Task 3**: Success-story CRUD:
  - `POST /admin/success-stories` — accepts every field in `SuccessStory` model (slug, client_name, etc.). Returns `SuccessStoryAdminRead`. 409 on slug conflict.
  - `PATCH /admin/success-stories/{id}` — partial update; `published_at = null` unpublishes, an ISO datetime publishes.
  - `DELETE /admin/success-stories/{id}` — soft delete (sets `deleted_at`). Returns 204.
- [ ] **Task 4**: New schemas: `LeadUpdate`, `SuccessStoryCreate`, `SuccessStoryUpdate`, `CoachAdminRead` in `app/schemas/admin.py`.
- [ ] **Task 5**: Integration tests for every new endpoint covering 200/201/204 success paths + 401/403 auth gates + 404/409 error paths.
- [ ] **Task 6**: Frontend server actions in `src/app/admin/_actions/` — `updateLead`, `createSuccessStory`, `updateSuccessStory`, `deleteSuccessStory`. Each wraps `adminFetch` (extended to accept method + body), pulls the Clerk token from `auth()`, calls revalidatePath after success.
- [ ] **Task 7**: `LeadEditDrawer` client component. Trigger = clicking a lead row on `/admin/leads`. Form: status `<select>` + coach `<select>` (loaded from `/admin/coaches`). Submit fires `updateLead` server action. Optimistic UI optional; if skipped, just rely on revalidatePath.
- [ ] **Task 8**: `SuccessStoryEditDrawer` client component. "New story" button + click-row-to-edit both open the same drawer in create vs edit mode. Fields: slug, client_name, role_before/after, company_after, headshot_url, linkedin_url, story_short, story_long, is_featured toggle, sort_order, publish/unpublish toggle. Delete button with confirm.
- [ ] **Task 9**: Wire drawers into `/admin/leads/page.tsx` and `/admin/success-stories/page.tsx`. Add "New story" button to the latter. Make rows clickable.

## Acceptance criteria

- [ ] Backend: mypy strict + ruff clean; new integration tests pass.
- [ ] Backend: `PATCH /admin/leads/{id}` actually updates the lead in DB; subsequent `GET /admin/leads` reflects the change.
- [ ] Frontend: `pnpm build` / lint / typecheck green; opening the lead drawer, changing status, and saving updates the row in the list without a manual refresh.
- [ ] Frontend: creating a new success story from the drawer makes it appear in the list; toggling published_at hides/shows the story on the public `/success-stories` page after revalidation.

## Deferred / handed back to user

- [ ] **Stripe payment link generation** — still blocked on user-provided `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`.
- [ ] **Calendly webhook handler** — still blocked on `CALENDLY_WEBHOOK_SIGNING_KEY` + registering the webhook URL in Calendly's dashboard once the endpoint exists.
- [ ] **Bulk actions** (multi-select + bulk status change) — defer to v2 if it ever feels needed.
- [ ] **Audit log of admin changes** — out of scope; rely on PG row-level timestamps for now.

## Files added / modified (planned)

Backend:
- `app/api/routes/admin.py` (extend with 4 new endpoints)
- `app/schemas/admin.py` (add 4 schemas)
- `tests/integration/test_admin.py` (extend with write-action tests)

Frontend:
- `src/app/admin/_actions/` (new directory with server actions)
- `src/components/admin/lead-edit-drawer.tsx` (new)
- `src/components/admin/success-story-edit-drawer.tsx` (new)
- `src/app/admin/leads/page.tsx` (wire drawer)
- `src/app/admin/success-stories/page.tsx` (wire drawer + "New" button)
- `src/lib/admin-fetch.ts` (extend to accept method + body)
- `src/lib/admin-types.ts` (add CoachAdmin, request shapes)
