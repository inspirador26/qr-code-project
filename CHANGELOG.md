# Changelog

Running log of what changed and why, for humans and any LLM picking up this repo mid-stream. Newest entry on top. See `LLM_HANDOFF.md` for the standing architecture/context brief — this file is just the session-by-session diff of that.

Entry format:

```
## YYYY-MM-DD — <author: name or "Claude"/other LLM>

- What changed
- Why (skip if obvious)
- Anything the next person/LLM needs to know (blockers, follow-ups, gotchas)
```

---

## 2026-08-22 — Claude (with Justin), part 2

- Set up a branching model: `main` (stable) ← `staging` (integration) ←
  `feature/*` branches, merged back into `staging` rather than `main`.
- Added `.claude/skills/qr-coupon-flow/SKILL.md` and
  `.claude/skills/google-wallet/SKILL.md`, joining `dev-environment` as the
  first three living per-feature architecture docs (mechanics, known
  problems/solutions, TODOs) — distilled from `server.js` plus what today's
  session actually diagnosed. These are meant to be updated in place as
  understanding changes, unlike this changelog which stays append-only
  history.
- Added `CLAUDE.md` with a standing policy: Claude does not run `git commit`,
  open PRs, or `git push` unless explicitly asked to do so in that moment —
  Justin runs those himself by default.

## 2026-08-22 — Claude (with Justin)

- Resumed the 2026-08-07 session, which had ended mid-fix without confirming the result. Started the server (`LISTEN_HOST=0.0.0.0`, LAN IP had changed again to `192.168.0.162`), confirmed the pending `server.js` fix (dropping `reviewStatus: 'underReview'` from the Google Wallet save JWT — see 2026-08-07 entry) actually resolves the "unable to load this pass" error: Justin scanned a live QR and reached the wallet save step successfully.
- The pass still shows a "[TEST ONLY]" banner. Confirmed this is a separate, expected thing — governed by the Issuer account's own review/publish status in the Wallet Business Console, not the per-class `reviewStatus` (which is already `approved`). Corrected the stale note in `LLM_HANDOFF.md`'s Known Issues that implied the JWT fix would also clear this banner.
- Committed the `server.js` fix (finally — it had sat uncommitted since 2026-08-07) along with the `LLM_HANDOFF.md` corrections and this file.
- Next up: Justin's partner already owns the GCP project, so he'll mint his own copy of the rotated `wallet-sa.json` key directly rather than it being transferred — no action needed on our end.
- Follow-up idea from this session: adopt Claude Code **skills** (`.claude/skills/`) as living per-feature architecture docs (policies, known problems/solutions, TODOs), separate from this changelog's flat session history. See next session for setup.

---

## 2026-07-27 — Claude (with Justin)

- Cloned `github.com/inspirador26/qr-code-project` into this local folder (`git init` + `remote add origin` + `fetch` + `checkout -b main origin/main`, rather than `git clone` since the folder already had 5 local planning docs). Committed those docs as the first local commit.
- Ran `npm install` then `npm rebuild better-sqlite3` — the committed `node_modules` had a `better_sqlite3.node` built for a non-Windows platform ("not a valid Win32 application"). Rebuilding fixed it. **If you pull fresh on a new machine, always run `npm rebuild better-sqlite3`.**
- Added this file and a pointer to it in `LLM_HANDOFF.md`.
- Created empty `keys/` folder (gitignored) — needs `wallet-sa.json` (Google Wallet Issuer service account key) dropped in locally before `server.js` will boot. Not committed, never will be.
