# Frontend — segment-level decisions & known issues

This file tracks decisions/issues from frontend work onward, per
`.claude/skills/skills-organization/SKILL.md`. Newest on top.

See `.claude/skills/product/cpg-engagement-workflow/SKILL.md`'s "UI plan,
by actor" section for the planned shape of the CPG client panel and
internal ops UI — that's the closest thing to frontend planning that
exists today, and is where this segment's first skill doc will likely draw
from once building starts.

---

## 2026-09-12 — Offer lists stay compact; details and editing use dedicated pages

**Decision**: keep the internal and tenant offer tables as summaries, but
make offer titles link to full detail pages. Internal operators and tenant
Admin/Editor members can edit partner-managed offers; tenant Viewers are
read-only, and every tenant lookup is filtered by the selected tenant.

**Locked-data boundary**: offer identity fields are never edited from the
detail flow. After an offer leaves Draft, TCB-controlled terms are displayed
but disabled because the app has no verified MOF update workflow. The local
display title and distribution cap remain editable. `client_managed` offers
are fully read-only because their external Authorized Partner owns the MOF.

**Why**: a dense table should not try to contain every offer field, but every
authorized user still needs a discoverable path to all appropriate data.
Disabling fields in the server-side form as well as the UI prevents crafted
POST requests from bypassing the lifecycle boundary.

---

## 2026-09-03 — First UI slice is server-rendered Django templates

**Decision**: the first Objective 2 UI work uses Django templates under
`backend/templates/`, extending the existing `base.html` with Tailwind/htmx/
Alpine CDN scaffolding. No SPA or frontend build pipeline yet.

**Why**: the immediate work is CRUD/dashboard-heavy and already lives in the
Django backend. Server-rendered forms and tables are enough to validate the
internal intake and tenant-isolation flows before adding frontend build
complexity.

**How to apply**: keep `/internal/` and `/app/` structurally separate.
Internal ops views may cross tenants but must be gated by internal access;
tenant-facing views must filter by the selected active tenant.
