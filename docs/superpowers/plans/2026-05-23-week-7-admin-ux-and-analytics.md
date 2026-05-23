# Week 7 — Admin UX (notes, filtering, search) + PostHog server-side events

> Executed inline 2026-05-23.

**Goal:** Make the admin lead workflow usable end-to-end for daily ops, and start capturing the high-trust conversion signals that the spec calls for. After this week, Alex and Atiyeh should be able to (a) jot notes after a discovery call and find leads again later by email or status, and (b) trust that PostHog funnels are reflecting reality.

**Architecture:**
- Backend: `leads.notes` jsonb-free string column (Alembic migration), extended `LeadAdminRead` / `LeadUpdate`, `?status=` and `?search=` query params on `GET /admin/leads`, and a thin `app/services/posthog_service.py` that fires server-side captures. Fires on lead create + status change + coach assignment.
- Frontend: lead drawer adds a notes `<textarea>`; the leads page gains a sticky filter row (status `<select>` + search `<input>`) that drives the existing pagination + filter query params.

**Spec reference:** `docs/superpowers/specs/2026-05-20-career-flow-split-design.md` §6 (admin), §7 (analytics).

---

## Tasks

- [ ] **Task 1**: `Lead.notes: Mapped[str | None]` (no length cap; can grow). Alembic autogenerate + run on local. Extend `LeadAdminRead` to include notes, extend `LeadUpdate` to accept notes (partial). Update `PATCH /admin/leads/{id}` to persist.
- [ ] **Task 2**: `GET /admin/leads` accepts `status: LeadStatus | None` and `search: str | None`. `search` does `ILIKE '%term%'` against name + email (case-insensitive, no SQL-injection risk via parameterized queries). Filters apply to `total` too.
- [ ] **Task 3**: `app/services/posthog_service.py`. Use `posthog` SDK (already in pyproject) with `posthog.api_key` set from settings; no-op + log warning when unset. Expose `capture(distinct_id, event, properties)`. Wire into `LeadService.create` (event `lead.created`) and `PATCH /admin/leads/{id}` (events `lead.status_changed` + `lead.assigned`).
- [ ] **Task 4**: Unit tests for `posthog_service` (capture path + no-op path, both via mocked posthog client). Integration tests for new query params on `GET /admin/leads`.
- [ ] **Task 5**: Frontend — extend `LeadEditDrawer` with notes textarea (save on submit; multi-line). Update `LeadUpdatePayload` type. Server action passes through.
- [ ] **Task 6**: Frontend — new `LeadFilters` client component above the table: status `<select>` + debounced search input. Updates URL via `router.replace` with `status` / `search` params; server re-renders with filtered data.
- [ ] **Task 7**: Frontend — update `/admin/leads/page.tsx` to forward `status` + `search` to backend.

## Acceptance criteria

- [ ] Backend mypy + ruff + unit & integration tests pass.
- [ ] `PATCH /admin/leads/{id}` with `{"notes": "called 5/22, qualified"}` persists; next `GET` returns it.
- [ ] `GET /admin/leads?status=qualified&search=alex` returns only matching rows; `total` reflects the filtered count.
- [ ] PostHog dashboard shows `lead.created`, `lead.status_changed`, `lead.assigned` events when keys are set; backend logs warn-once when unset and no crash.
- [ ] Frontend build/lint/typecheck green; notes editable in drawer; filters update list without full page reload (server-side render via URL params).

## Deferred

- Notes on `Booking` and `Payment` rows — wait until those data sources are wired (post Stripe/Calendly).
- Saved filters / per-coach views — only worth building once usage shows it.
- Audit log of admin changes — out of scope.

## Files added / modified (planned)

Backend:
- `app/models/lead.py` (add notes)
- `alembic/versions/...add_lead_notes.py` (new)
- `app/schemas/admin.py` (extend Lead schemas)
- `app/api/routes/admin.py` (filters, persist notes, fire events)
- `app/services/posthog_service.py` (new)
- `app/services/lead_service.py` (fire `lead.created` event)
- `tests/unit/test_posthog_service.py` (new)
- `tests/integration/test_admin.py` (extend with filter/search tests)

Frontend:
- `src/components/admin/lead-edit-drawer.tsx` (notes textarea)
- `src/components/admin/leads-filters.tsx` (new)
- `src/app/admin/leads/page.tsx` (forward filter params)
- `src/lib/admin-types.ts` (add notes to LeadAdmin + LeadUpdatePayload)
