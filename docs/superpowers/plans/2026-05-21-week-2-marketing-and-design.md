# Week 2 — Marketing pages + design system

> **For agentic workers:** This plan was executed inline in the autonomy run on 2026-05-20/21. Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` only if rerunning. Most tasks are already complete and committed in `career-flow-frontend`.

**Goal:** All public marketing pages live with warm/minimal visual direction; 5 brand palette variants implemented as switchable themes so the brand-colour decision can happen against real layout; Lighthouse CI enforcing perf / a11y / best-practices / SEO budgets; placeholder forms and quiz functional in the browser pending backend integration in Plan 4.

**Architecture:** All pages live in `src/app/(marketing)/` route group with a shared `MainNav + Footer` layout. Theme variants live in `src/app/globals.css` as `[data-theme="…"]` scopes; the active theme is set client-side by `ThemeApplier` (from `?theme=` query param) or server-side from `NEXT_PUBLIC_THEME`. Coach, package, success story, FAQ, resource, blog, and quiz content is hand-written in `src/lib/*` to match the eventual API shape, so swapping to API-backed data in Plan 3 is a small refactor.

**Tech stack additions:** shadcn primitives `sheet`, `separator`, `form`, `accordion`, `select`, `checkbox`, `radio-group`; zod downgraded to 3.25 for `@hookform/resolvers` compatibility; Lighthouse CI (`@lhci/cli`).

**Spec reference:** `docs/superpowers/specs/2026-05-20-career-flow-split-design.md`

---

## Phase 0 — Prerequisites

- [x] Brand direction locked (warm + minimal premium; references Calm/Headspace + Apple)
- [x] 5 candidate palettes documented in spec

## Phase 1 — Theme system + shared layout

- [x] **Task 1**: 5-variant theme system. `src/app/globals.css` defines `:root` and four `[data-theme="..."]` scopes with full token sets (background, foreground, muted, card, popover, primary, secondary, accent, destructive, border, input, ring). `@theme inline` block binds CSS vars to Tailwind v4 colour tokens. Variants: `cream-terracotta` (default), `sand-forest`, `snow-sage`, `v0-current`, `warm-purple`. `src/lib/themes.ts` exports the union type, labels, and `isTheme` guard. `src/components/providers/theme-applier.tsx` switches via `?theme=` query param or `NEXT_PUBLIC_THEME` env var. `/design-preview` (noindex) shows all five rendered side-by-side in their own colours.
- [x] **Task 2**: Shared marketing layout. `(marketing)/layout.tsx` wraps with `MainNav` and `Footer`. `MainNav` is a sticky translucent bar with desktop links and a mobile `Sheet` drawer. `Footer` has 4 columns (about + Explore + Programs + Connect) and `hello@career-flow.com` contact.
- [x] **Task 3**: Home page. Hero → Why coaching (3 cards) → Our impact (3 stats) → Who we serve (4 cards) → final CTA banner. Framer Motion hero entrance.

## Phase 2 — Conversion pages

- [x] **Task 4**: How We Help. `/how-we-help` overview compares 1-on-1 vs group with quiz + discovery-call CTAs. `/how-we-help/one-on-one` renders 3 `PackageCard`s (Navigator $1200/mo, Architect $1600/mo featured, Accelerator from $2100/mo). `/how-we-help/group-coaching` shows the 6-week agenda alongside the $800 Group Cohort card. All package data lives in `src/lib/packages.ts` with shape matching the backend `packages` schema.
- [x] **Task 5**: Our Team. `src/lib/coaches.ts` defines Alex + Atiyeh with full bios. `/our-team` lists both via `CoachCard`. `/our-team/[slug]` is SSG (`generateStaticParams` for both slugs) with full bio, expertise pills, dual CTAs (own Calendly + general discovery), and email link.
- [x] **Task 5b**: Success Stories. `src/lib/success-stories.ts` defines 3 sample stories. `/success-stories` renders them with before/after roles, coach attribution, CTA to discovery call.
- [x] **Task 6**: Resources. `src/lib/resources.ts` defines 3 PDFs. `/resources` lists them with topic pills. `/resources/[slug]` is SSG with detail + `ResourceRequestForm` (RHF + Zod, local-only submit ack pending Plan 4 backend wiring).
- [x] **Task 6b**: Blog scaffolding. `src/lib/blog.ts` carries 2 launch posts as plain text bodies. `/blog` lists them, `/blog/[slug]` renders detail. MDX upgrade deferred to Week 9.
- [x] **Task 7**: FAQ + Contact + Terms + Join Waitlist.
  - `/faq`: base-ui Accordion with 7 questions
  - `/contact`: RHF form with name/email/subject/message, local-only submit ack
  - `/terms`: static prose covering coaching, billing, confidentiality, data
  - `/join-waitlist`: RHF form for group cohort with email, role, years of exp, biggest challenge, optional LinkedIn, coach preference, workshop interest checkboxes
- [x] **Task 8**: Match-Me Quiz. `src/lib/quiz.ts` defines 5 questions with option-level +1 votes for Alex or Atiyeh; `scoreQuiz` + `pickRecommendedCoach` produce result. `QuizClient` (client component) walks one question at a time and shows recommended coach card(s) at the end with bio + book CTAs.

## Phase 3 — CI / observability for the marketing site

- [x] **Task 9**: Lighthouse CI. `lighthouserc.cjs` runs against 13 marketing routes in desktop preset with budgets Perf ≥ 0.80, A11y ≥ 0.95, Best Practices ≥ 0.95, SEO ≥ 0.95. Wired into GitHub Actions as the `lighthouse` job (after `build`) with `continue-on-error: true` for the first few runs while budgets stabilise.

## Phase 4 — Deferred / handed back to user

- [ ] **Task 10**: Brand palette pick. Five variants are mockable now via `?theme=<slug>` against any page. **Decision happens at implementation kickoff for Plan 3+ once the user has time to review.** Once chosen, lock in via `NEXT_PUBLIC_THEME` env var (or by promoting the chosen variant to `:root`).

## Acceptance criteria

- [x] All 13 marketing routes build statically (or SSG) with no TS or ESLint errors
- [x] Lint, typecheck, build, unit tests all green
- [x] Playwright homepage smoke test green
- [x] `/design-preview` renders all 5 variants in their own colours
- [x] All forms render and validate via zod
- [x] Marketing routes pass lint + typecheck in CI; Lighthouse runs (assertions soft-fail until budgets are tuned against real production hosting)
- [ ] **Deferred**: brand palette decision (one of the 5 variants)
- [ ] **Deferred**: form submissions wire to backend (Plan 4)
- [ ] **Deferred**: coach / story / package data sources from backend API (Plan 3)

## Files created in this plan

- `src/app/(marketing)/{layout.tsx, page.tsx, how-we-help/page.tsx, how-we-help/one-on-one/page.tsx, how-we-help/group-coaching/page.tsx, our-team/page.tsx, our-team/[slug]/page.tsx, success-stories/page.tsx, resources/page.tsx, resources/[slug]/page.tsx, blog/page.tsx, blog/[slug]/page.tsx, faq/page.tsx, contact/page.tsx, terms/page.tsx, join-waitlist/page.tsx, quiz/page.tsx}`
- `src/app/design-preview/page.tsx`
- `src/components/marketing/{logo.tsx, main-nav.tsx, footer.tsx, section.tsx, hero.tsx, package-card.tsx, coach-card.tsx, resource-request-form.tsx, contact-form.tsx, waitlist-form.tsx, quiz-client.tsx}`
- `src/components/providers/theme-applier.tsx`
- `src/components/ui/{form.tsx, sheet.tsx, separator.tsx, accordion.tsx, select.tsx, checkbox.tsx, radio-group.tsx}`
- `src/lib/{themes.ts, nav.ts, packages.ts, coaches.ts, success-stories.ts, resources.ts, blog.ts, faqs.ts, quiz.ts}`
- `src/lib/schemas/{resource-request.ts, contact.ts, waitlist.ts}`
- `src/app/globals.css` (5-variant tokens)
- `lighthouserc.cjs`
- `.github/workflows/ci.yml` (added `lighthouse` job)
