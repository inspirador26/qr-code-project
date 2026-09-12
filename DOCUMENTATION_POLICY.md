# Documentation policy

Adopted 2026-09-11. A system for keeping this codebase's *reasoning* alive
across sessions, people, and AI instances — not just the code itself. Six
months from now, *what* a column is can be read off the code; *why it is
not the obvious thing* only exists if someone wrote it down.

Two failure modes this guards against:
- **The stale status file** — a hand-maintained "where we left off" doc
  that goes wrong silently, gets read first, and gets believed. Worse than
  having none. This project has no such file; see the "ask the repo" table
  in `CLAUDE.md` instead.
- **The merge-conflict-at-the-top problem** — if every branch appends to
  one shared file, every PR collides in the same spot. Solved here by
  `changelog.d/` (one file per branch, folded into `CHANGELOG.md` on merge).

## How this maps onto our actual structure

This project already had most of tier 2 before this policy was written
down explicitly — the adoption below is mostly naming what already existed
and closing the one real gap (per-branch changelog fragments).

| Concept | Generic name | What it is here |
|---|---|---|
| Tier 1 — always-on rules | `RULES.md` | `CLAUDE.md` (repo root, loaded every session) |
| Tier 2 — deep reference per feature | `DOCS/<app>/<app>-notes.md` | `.claude/skills/<segment>/<skill>/SKILL.md` |
| Tier 2 — why a decision was made | `DOCS/<app>/decisions.md` | `.claude/skills/<segment>/DECISIONS_AND_ISSUES.md` (per segment, not per app — see `skills-organization/SKILL.md`) |
| Tier 2 — app state dossier | `DOCS/apps/<app>.md` | `.claude/skills/<segment>/DOSSIER.md` — **new**, one per app/segment that has running code (currently just `backend/`) |
| Per-branch changelog fragment | `changelog.d/<branch>.md` | `changelog.d/<branch>.md` — **new as of this policy**, same convention |
| Folded history | `DOCS/changelog.md` | `CHANGELOG.md` (already existed, already grepped not read) |

## The numbering discipline (for `CLAUDE.md`)

`CLAUDE.md`'s rule sections are numbered and may be cited from elsewhere
(e.g. a skill doc saying "see `CLAUDE.md` §2"). **Never renumber** — a
renumber leaves every citation pointing at the wrong rule while still
reading perfectly. New rules are appended as the next free number, never
inserted. Two branches adding a rule at the same time will both pick the
next number and merge without complaint — before adding one, check
`git log -1 --stat -- CLAUDE.md` on the branch you're merging into, and put
the addition in its own commit so a collision is a one-line resolve.

## The dossier — ten sections, same order every time

For each `.claude/skills/<segment>/DOSSIER.md`:

1. **Scope** — what it is; what is explicitly OUT and who/what owns it instead
2. **Policy** — the rules that bite; anything a newcomer would violate by default
3. **Where the code is** — a path table
4. **Library reliance** — dependencies and load-bearing config around them
5. **Current state** — live / built-but-not-wired / read-only on purpose
6. **Known issues** — each with what the fix is, plus traps that cost real time
7. **TO DO** — started and not finished, including *why* it was left
8. **Feature plans and ideas** — including what was deliberately deferred, and the ceiling
9. **History pointers** — a table of `CHANGELOG.md` entries still worth reading, not a history in itself
10. **Working on this app** — the numbered routine: what to read, run, update

State lives in the dossier; history lives in `CHANGELOG.md`. The dossier is
a front door, not the whole reference — it links out to the deep-dive
`SKILL.md` files for detail. Whoever finishes work on an app/segment
updates dossier §5–§8 in the same commit as the work.

## The decisions log — the load-bearing half is the reason

Already-adopted format in `<segment>/DECISIONS_AND_ISSUES.md`: newest entry
on top, dated, with what was decided/found, why it matters beyond one
feature, and how to apply it. Keep it **append-only** — when a decision is
reversed, add a new entry saying so rather than editing the old one away.
The superseded reasoning is *why* the new choice is right; a log that only
ever shows good decisions teaches nothing. Quote the actual ask where you
can ("Justin said X") — a quoted sentence survives paraphrase and settles
"did we mean this?" arguments a year later.

## `changelog.d/` — one file per branch (new)

See `changelog.d/README.md` for the format. This is the whole anti-conflict
mechanism: two people never edit the same file mid-branch. Whoever merges a
branch folds its fragment into `CHANGELOG.md` (matching the existing entry
format there) and deletes the fragment — an empty `changelog.d/` (aside
from its `README.md`) is the healthy state, not a red flag.

## The rule that ties it together

**Documentation rides with the work it describes.** Same branch, same
commit where practical: the dossier update, the decisions-log entry, the
deep-dive skill doc, the changelog fragment — including writing a dossier
that doesn't exist yet for a segment that just got its first real feature.
A feature merged with its documentation "deferred to a later branch" merges
undocumented in practice, because the later branch is the one that never
gets written.

The exception: documentation with no feature attached (folding fragments,
correcting an old note, a rules change) gets its own `docs/<segment>/<slug>`
branch — not a place to put documentation someone would rather not write
today.

## What NOT to duplicate

Don't create a second "where things stand" file. If you're tempted to write
a status/handoff doc by hand, that's what the dossier's §5 (Current state)
and §9 (History pointers) are for — update those instead.
