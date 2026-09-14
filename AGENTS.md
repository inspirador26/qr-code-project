# Repo policy — always-on rules

This file is loaded at the start of every session, for every person and
every AI assistant working in this repo (Claude Code, Codex, or otherwise —
see `CLAUDE.md` for the one-line pointer that tells Claude Code specifically
to read this file). It holds only the rules that must never be missed.
Everything else lives in `SKILL/` — see `DOCUMENTATION_POLICY.md` for the
full system this belongs to.

**To find out where things stand, ask the repo — not a file someone
maintained by hand.** There is no standing "resume point" document.

| Question | Where the answer actually lives |
|---|---|
| What is in flight? | `ls changelog.d/` — a file per branch. An empty folder (aside from its README) is healthy |
| What is waiting on review? | `gh pr list` |
| What do I need to know about the backend? | `SKILL/backend/DOSSIER.md` |
| What happened, and why? | `CHANGELOG.md` — grep it, never read it start to end |
| Why was a specific decision made? | `SKILL/<segment>/DECISIONS_AND_ISSUES.md` |

## Numbering discipline

Sections below are numbered and may be cited from other docs (e.g. "see
`AGENTS.md` §2"). **Never renumber** — it leaves every citation pointing at
the wrong rule while still reading perfectly. New rules are appended as the
next free number, never inserted. See `DOCUMENTATION_POLICY.md` for the
full rationale and the two-branches-pick-the-same-number hazard.

## 1. Who runs git commands

**No AI assistant runs a `git` command itself** — not `commit`, `push`,
`gh pr`, and not read-only ones like `status`/`diff`/`log` either. Instead,
give Justin the exact command(s) to run. The one exception: Justin
explicitly says something like "go ahead and do the git commands this
time" in that specific message — that authorizes it for that moment only,
never carrying forward to the next ask. Staging files, showing diffs, or
proposing a commit message is still fine to do directly; only the actual
git invocation is off-limits without that explicit go-ahead.

## 2. No AI attribution in commits

Never add a `Co-Authored-By: Claude` (or similar, for any assistant)
trailer to a commit message, PR description, or code comment, unless
explicitly asked for it again in that moment.

## 3. Where the standing docs are

- `CHANGELOG.md` — session-by-session history, folded from `changelog.d/`
  fragments on merge. Grep it; don't read it top to bottom.
- `SKILL/` — living per-feature docs (architecture, known
  problems/solutions, TODOs), grouped into segment folders (`backend/`,
  `frontend/`, `legacy/`, `product/`, `domain/`, `infra/`). See
  `SKILL/skills-organization/SKILL.md` for the grouping policy,
  and `DOCUMENTATION_POLICY.md` for the full documentation system
  (dossiers, decisions logs, changelog fragments). Despite the `SKILL.md`
  filename convention, these are plain reference markdown — **not** Claude
  Code's auto-loaded Skills mechanism (that only scans
  `.claude/skills/<name>/SKILL.md`, unrelated to this top-level directory);
  a session has to be pointed at one or read it directly.

## 4. Documentation rides with the work

A feature isn't done when it merges undocumented "for a later branch" —
that later branch is the one that never gets written. Update the relevant
dossier (`SKILL/<segment>/DOSSIER.md` §5–§8), decisions log, and
`changelog.d/<branch>.md` fragment in the same branch as the work, not
after. Full detail in `DOCUMENTATION_POLICY.md`.
