## Move the skills directory from .claude/skills/ to a top-level SKILL/

**Branch:** docs/skill-dir-top-level
**Author:** Claude (with Justin)

Justin asked to stop nesting the living-docs tree under `.claude/` and
have it be a top-level `SKILL/` directory instead, matching the shape of
another project of his (`.claude/` stays as Claude Code's own config;
`SKILL/` sits alongside `backend/`, `frontend/`, etc.). Before doing the
move, checked whether this would break Claude Code's actual Skill
auto-load mechanism — it would have, except it turned out these docs were
**already** non-loadable: `Skill("tcb-integration")` and
`Skill("backend:tcb-integration")` both return "Unknown skill." That
mechanism only ever auto-discovers `.claude/skills/<name>/SKILL.md` one
level deep; the segment-folder nesting adopted 2026-09-02
(`.claude/skills/<segment>/<name>/SKILL.md`) put every one of these docs
one level too deep for it, so only `skills-organization` (which happened
to sit at the shallow, correct depth) was ever actually invokable — and
that stops working too once it moves out from under `.claude/` entirely.
Net effect of the move: no working behavior was lost, since none of these
were mechanically auto-loaded skills in practice — they've always
functioned as plain reference docs a session has to be told to read.

### Files touched

- `.claude/skills/` → `SKILL/` — moved the whole tree (`mv`, not `git mv`,
  since git commands aren't run directly in this repo per `AGENTS.md` §1;
  `git add` will detect it as a rename on commit).
- `AGENTS.md` — every `.claude/skills/` path repointed to `SKILL/`;
  removed §3's now-fully-inaccurate "these are Claude Code 'skills'
  mechanically (auto-loadable by name)" claim, replaced with an explicit
  note that they aren't.
- `DOCUMENTATION_POLICY.md` — mapping table repointed to `SKILL/`; added a
  note on why this isn't the Skills mechanism.
- `SKILL/skills-organization/SKILL.md` — rewrote the intro and replaced
  the "A caveat about invoking these skills" section (which incorrectly
  claimed these were name-invokable) with an accurate one documenting the
  `Skill()` test above.
- `SKILL/backend/DOSSIER.md`, `SKILL/backend/consumer-offer-delivery/
  SKILL.md`, `SKILL/backend/DECISIONS_AND_ISSUES.md`,
  `SKILL/legacy/DECISIONS_AND_ISSUES.md`,
  `SKILL/product/DECISIONS_AND_ISSUES.md`,
  `SKILL/frontend/DECISIONS_AND_ISSUES.md`,
  `SKILL/domain/DECISIONS_AND_ISSUES.md`,
  `SKILL/infra/DECISIONS_AND_ISSUES.md` — internal cross-references
  repointed from `.claude/skills/...` to `SKILL/...`.
- `backend/README.md` — same path repointing.
- `backend/wallet/service.py` — one code comment's path reference fixed.
- `changelog.d/docs-consumer-offer-delivery-plan.md` — left that fragment's
  own path references as `.claude/skills/...`, since they're historically
  accurate to when that branch's work happened; only corrected its stale
  claim that the pending root-doc deletions had already occurred.

### Verified

Docs-only branch, no code changes, no test run. Grepped the whole repo
(excluding `venv/`) for `.claude/skills` after the move — every remaining
hit is either deliberate (explaining the move itself, in this fragment,
`AGENTS.md`, `DOCUMENTATION_POLICY.md`, and `SKILL/skills-organization/
SKILL.md`), historical (`CHANGELOG.md`, left untouched), or inside the
still-pending-deletion root `.md` files (not worth fixing since they're
being deleted).

### Not done / known gaps

- The root `.md` files flagged as pending deletion in the previous
  branch's fragment (`ARCHITECTURE.md`, `DATABASE.md`,
  `PROJECT_OVERVIEW.md`, `ROADMAP.md`, `LLM_HANDOFF.md`,
  `HANDOFF_MVP_DEMO.md`, `COUPON_WORKFLOW_PRIMER.md`,
  `backend/docs/HANDOFF_offer_clip_flow.md`) are **still** not deleted —
  still Justin's to run, unrelated to this branch's own scope.
- `changelog.d/docs-consumer-offer-delivery-plan.md` and
  `changelog.d/feature-new-offer.md` are both sitting unfolded past their
  branches' merges — not fixed here, flagged for whoever next has a reason
  to touch `CHANGELOG.md`.
