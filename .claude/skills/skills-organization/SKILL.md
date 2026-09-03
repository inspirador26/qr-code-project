---
name: skills-organization
description: Policy for how this repo's .claude/skills/ directory is organized — segment folders (backend, frontend, legacy, product, domain, infra), where a new skill doc goes, and how each segment tracks its own policy decisions and known issues. Load this before creating a new skill doc, moving one, or when you need to know which segment a topic belongs to.
---

# Skills organization policy

This repo tracks living documentation as Claude Code **skills** under
`.claude/skills/`, per-feature (architecture, known problems/solutions,
TODOs — see `CLAUDE.md`). As of 2026-09-02, those skill docs are grouped
into **segment directories**, one per part of the system, instead of sitting
flat. This doc is the policy for that grouping — read it before adding,
moving, or renaming a skill.

## Why

The flat layout stopped scaling once the number of skill docs grew past a
handful — it wasn't obvious at a glance whether a topic was backend-code-
specific, product/business planning, or cross-cutting domain knowledge, and
there was nowhere to record a decision or a known issue that applies to a
whole area (e.g. "backend" generally) rather than one specific feature.

## Current segments

| Segment | Directory | What goes here |
|---|---|---|
| Backend | `.claude/skills/backend/` | Django backend (`backend/`) feature-specific skills — one skill dir per app/subsystem. Currently: `tcb-integration`, `tenancy-and-auth`, `google-wallet`. |
| Frontend | `.claude/skills/frontend/` | Client-facing UI work. **Empty as of 2026-09-02** — no frontend has been built yet (see `product/cpg-engagement-workflow`'s "UI plan" section for what's planned). Add skill docs here once frontend work starts. |
| Legacy | `.claude/skills/legacy/` | The original Node/Express proof-of-concept (`server.js`), kept only as a behavioral reference during the Django rewrite. Currently: `qr-coupon-flow`. |
| Product | `.claude/skills/product/` | Business/workflow planning docs that aren't tied to a specific piece of code — client engagement flow, billing model, open business decisions. Currently: `cpg-engagement-workflow`. |
| Domain | `.claude/skills/domain/` | Industry/vocabulary knowledge that isn't project-specific but is load-bearing for understanding the domain (e.g. who's who in digital coupons). Currently: `coupon-industry-roles`. |
| Infra | `.claude/skills/infra/` | Local dev setup, credentials, running servers, branching — operational concerns that span both `backend/` and `legacy/`. Currently: `dev-environment`. |

Each segment folder holds one subdirectory per skill (`<segment>/<skill-name>/SKILL.md`), exactly like the old flat layout — only the parent directory changed. Skill frontmatter (`name:`, `description:`) is unchanged by this move.

## Where a new skill doc goes

Ask: is this about a specific Django app/subsystem in `backend/`? →
`backend/`. About UI once it exists? → `frontend/`. About the legacy POC? →
`legacy/`. A business/workflow decision not tied to code? → `product/`.
Industry vocabulary/glossary? → `domain/`. Dev setup/credentials/ops? →
`infra/`. If none fit, that's a sign a new segment is needed — add a row to
the table above rather than force-fitting it.

## Tracking policy decisions and known issues per segment

Each segment directory has a **`DECISIONS_AND_ISSUES.md`** file (plain
markdown, not a `SKILL.md` — it's a log, not something to load standalone)
for anything that applies at the segment level rather than to one specific
skill/feature:
- A policy decision that affects more than one skill in that segment (e.g.
  a routing convention every backend endpoint must follow).
- A known issue/gotcha that isn't specific to one feature (e.g. a shared
  library quirk, a naming collision between two unrelated apps).

This is **in addition to**, not a replacement for, each individual skill
doc's own architecture/known-problems/TODO sections — segment-level entries
are for things that don't belong to just one skill. When in doubt, log it
on the specific skill doc first; only promote it to the segment log if a
second, unrelated skill in the same segment runs into the same thing.

Format: newest entry on top, same style as `CHANGELOG.md` — date, what was
decided or found, why, and what it affects.

## A caveat about invoking these skills

Skills nested under a segment directory are still invoked by their own
name (e.g. `tcb-integration`), same as before — the segment directory is
just where the file lives on disk, not part of the invocation. If the skill
listing ever shows a path-prefixed form (e.g. `backend:tcb-integration`)
because of a name collision across segments, use that exact form instead.
