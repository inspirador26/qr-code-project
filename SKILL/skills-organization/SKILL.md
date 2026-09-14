---
name: skills-organization
description: Policy for how this repo's top-level SKILL/ directory is organized — segment folders (backend, frontend, legacy, product, domain, infra), where a new skill doc goes, and how each segment tracks its own policy decisions and known issues. Load this before creating a new skill doc, moving one, or when you need to know which segment a topic belongs to.
---

# Skills organization policy

This repo tracks living documentation as per-feature "skill" docs
(architecture, known problems/solutions, TODOs — see `AGENTS.md`) under a
top-level `SKILL/` directory. As of 2026-09-02, those skill docs are
grouped into **segment directories**, one per part of the system, instead
of sitting flat. As of 2026-09-13, `SKILL/` moved out from under
`.claude/skills/` to repo-root top level — **these are plain reference
markdown, not Claude Code's auto-loaded Skills mechanism** (that's a
distinct, narrower thing scanning `.claude/skills/<name>/SKILL.md` one
level deep; it never actually picked these up even before the move,
because the segment-folder nesting put them one level too deep for it).
The `SKILL.md` filename is this project's own naming convention, nothing
more — a session has to be told to read one, the same as any other doc.
This doc is the policy for the grouping — read it before adding, moving,
or renaming a skill doc.

## Why

The flat layout stopped scaling once the number of skill docs grew past a
handful — it wasn't obvious at a glance whether a topic was backend-code-
specific, product/business planning, or cross-cutting domain knowledge, and
there was nowhere to record a decision or a known issue that applies to a
whole area (e.g. "backend" generally) rather than one specific feature.

## Current segments

| Segment | Directory | What goes here |
|---|---|---|
| Backend | `SKILL/backend/` | Django backend (`backend/`) feature-specific skills — one skill dir per app/subsystem. Currently: `tcb-integration`, `tenancy-and-auth`, `google-wallet`, `consumer-offer-delivery`. |
| Frontend | `SKILL/frontend/` | Client-facing UI work. Currently: `django-panel-ui`. |
| Legacy | `SKILL/legacy/` | The original Node/Express proof-of-concept (`server.js`), kept only as a behavioral reference during the Django rewrite. Currently: `qr-coupon-flow`. |
| Product | `SKILL/product/` | Business/workflow planning docs that aren't tied to a specific piece of code — client engagement flow, billing model, open business decisions. Currently: `cpg-engagement-workflow`. |
| Domain | `SKILL/domain/` | Industry/vocabulary knowledge that isn't project-specific but is load-bearing for understanding the domain (e.g. who's who in digital coupons). Currently: `coupon-industry-roles`. |
| Infra | `SKILL/infra/` | Local dev setup, credentials, running servers, branching — operational concerns that span both `backend/` and `legacy/`. Currently: `dev-environment`. |

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

## Dossiers (new as of 2026-09-11)

A segment with running code (currently just `backend/`) also gets a
**`DOSSIER.md`** — a fixed-ten-section "what's the current state of this
whole segment" front door, distinct from both the per-skill `SKILL.md`
deep-dives and the segment's `DECISIONS_AND_ISSUES.md` log. See
`DOCUMENTATION_POLICY.md` for the section list and update discipline, and
`SKILL/backend/DOSSIER.md` for the first one.

## A caveat about these not being loadable Skills

Despite the `SKILL.md` filename, none of these are invokable through
Claude Code's Skill tool — confirmed directly (`Skill("tcb-integration")`
and `Skill("backend:tcb-integration")` both return "Unknown skill"). That
mechanism only auto-discovers `.claude/skills/<name>/SKILL.md`, one level
deep, under the hidden `.claude/` config directory — unrelated to this
top-level `SKILL/` tree. Point a session at the specific file (or have it
grep/read the directory) rather than expecting it to be offered in a skill
listing or loaded by name.
