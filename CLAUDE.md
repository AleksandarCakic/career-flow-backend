# Career Flow Backend

Python FastAPI backend for [career-flow.com](https://www.career-flow.com), with PostgreSQL, Stripe, and Calendly integrations. The React + TypeScript frontend lives in a separate repository.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on `career-flow-coaching/career-flow-backend`, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Active specs

The current cross-repo design for the v0 → backend/frontend split and full platform MVP lives at `docs/superpowers/specs/2026-05-20-career-flow-split-design.md`. Read it before making implementation decisions; an identical copy is in the frontend repo.
