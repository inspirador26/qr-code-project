# Frontend — segment-level decisions & known issues

This file tracks decisions/issues from frontend work onward, per
`.claude/skills/skills-organization/SKILL.md`. Newest on top.

See `.claude/skills/product/cpg-engagement-workflow/SKILL.md`'s "UI plan,
by actor" section for the planned shape of the CPG client panel and
internal ops UI — that's the closest thing to frontend planning that
exists today, and is where this segment's first skill doc will likely draw
from once building starts.

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
