# Repo policy

- **Never run `git commit`, `git push`, or open/manage a pull request
  (`gh pr ...`) unless explicitly asked to do so in that specific moment.**
  Justin runs commits, PRs, and pushes himself by default. Staging files,
  showing diffs, or proposing a commit message is fine — executing the
  commit/push/PR is not, without a direct ask each time.
- See `LLM_HANDOFF.md` for the standing architecture/context brief and
  `CHANGELOG.md` for session-by-session history.
- See `.claude/skills/` for living per-feature docs (architecture, known
  problems/solutions, TODOs), grouped into segment folders (`backend/`,
  `frontend/`, `legacy/`, `product/`, `domain/`, `infra/`) — see
  `.claude/skills/skills-organization/SKILL.md` for the policy on that
  grouping, including where each segment tracks its own cross-cutting
  decisions/known issues (`<segment>/DECISIONS_AND_ISSUES.md`).
