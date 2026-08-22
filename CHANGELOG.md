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

## 2026-08-22 — Claude (with Justin), part 3

- Big-picture planning session: reviewed the GS1 AI(8112) coupon spec
  (`project-docs/`) and TCB's real Developer Portal API docs
  (`portal.thecouponbureau.org/developer/api_docs`), then wrote a full
  architecture/foundation plan for the actual product — a multi-tenant
  service distributing 8112 coupons for CPG clients via The Coupon Bureau,
  not just this repo's single-merchant QR/wallet demo. Plan saved at
  `C:\Users\Justin McMahon\.claude\plans\i-am-working-on-compressed-valiant.md`.
- **Decided: the backend is being rewritten in Python/Django**, not
  continued in Node/Express — `server.js` is kept only as a behavioral
  reference during the port, not migrated in place. Also decided: Django
  server-rendered UI (templates + htmx + Tailwind, no separate SPA), and
  `libzint` (BSD-3-Clause) for barcode rendering rather than
  `treepoem`/Ghostscript, which is AGPL-or-pay and would require an Artifex
  commercial license for closed-source SaaS use — checked actual current
  license terms for all of this rather than assuming.
- Started the new project at `backend/` (Django, Python 3.13, venv). Scaffolded
  10 apps per the plan (`tenancy`, `accounts`, `offers`, `coupons`,
  `tcb_integration`, `gs1`, `wallet`, `reporting`, `api`, `internal`), a
  settings package split into `base`/`dev`/`prod`, `docker-compose.yml`
  (Postgres + Redis), and Celery app skeleton. Implemented `Tenant`/
  `TenantMembership` and `User`/`UserIdentity`/`InternalOperator` models plus
  `TenantContextMiddleware` (tenant selection is explicit, never inferred)
  and an invite-only `django-allauth` social adapter. Verified the project
  boots clean (system checks, migrations, `/` and `/admin/` both 200)
  against a temporary SQLite DB. **Follow-up once Docker was started**: ran
  the full stack against the real `docker-compose` Postgres container and
  confirmed it end-to-end (migrations + `/` + `/admin/` all 200). Hit one
  real environment gotcha: this machine already runs a **native Postgres
  service on host port 5432**, separate from Docker, which was silently
  winning the port and causing Django to authenticate against the wrong
  instance. Fixed by remapping the container to host port **5433** in
  `docker-compose.yml`/`DATABASE_URL` — the native instance wasn't touched.
- Spiked `pyzint` for GS1 DataBar rendering and **it doesn't work**: GS1
  element-string encoding fails (`Error 252: Data does not start with an
  AI`) even for a control AI unrelated to 8112, and a malformed constructor
  call segfaults the process rather than raising cleanly. Don't use it.
- **Follow-up: spiked `zint-bindings` instead (PyPI `zint-bindings`, imports
  as `zint`) and it works.** Has the `InputMode.GS1PARENS` flag `pyzint` was
  missing, the `Symbology.DBAR_EXPSTK` constant (GS1 DataBar Expanded
  Stacked), and in-memory PNG rendering (`BARCODE_MEMORY_FILE` +
  `Symbol.memfile`, no temp files). Confirmed it renders a real TCB-example
  serialized data string to a valid PNG with no human-readable text, and
  that zint validates AI(8112)'s own VLI structure internally (a nice bonus
  layer of validation). One gotcha: an unrelated PyPI package also literally
  named `zint` (a ctypes wrapper needing a system `libzint` we don't have)
  claims the same import name and will shadow `zint-bindings` if both get
  installed — only `zint-bindings` should be a dependency.
  Implemented and tested `backend/gs1/data_string.py` (VLI builder/parser
  per the spec) and `backend/gs1/barcode.py` (the renderer) — 12 unit tests,
  all passing. The parser test suite caught a real bug during this work: it
  raised a bare `IndexError` on truncated input instead of a clean
  `DataStringError`; fixed with a bounds-checked `take()` helper.
- **Follow-up: implemented the full data model** across `offers`
  (`TcbManufacturerLink`, `DistributionChannel`, `Offer`,
  `OfferChannelConfig`), `coupons` (`CouponClip`, `CouponFetchCode`),
  `tcb_integration` (`TcbSyncLog` + a `TcbSyncLogClip` join table recording
  each clip's individual outcome bucket from a batch deposit response),
  `reporting` (`ClipEvent`, `RedemptionEvent`, `PromoReport`), and `api`
  (`ApiClient`, wrapping a `django-oauth-toolkit` `Application` rather than
  storing its own secret). All migrations generate and apply cleanly against
  Postgres; full test suite (12 tests) and system checks still pass; server
  still boots clean with every model registered in Django admin. One
  settings fix needed: `OAUTH2_PROVIDER_APPLICATION_MODEL` must be set
  explicitly even for oauth-toolkit's default `Application` model, or
  `makemigrations` fails resolving its swappable-model dependency.
- Justin asked about making signup "public" via Google/Microsoft — clarified
  that registering OAuth credentials with Google/Microsoft is required
  either way (public vs. gated doesn't change that), and that authentication
  (can you log in) and authorization (do you see a tenant's data) are
  separate questions. Confirmed: keep the invite-only tenant-attachment
  design as already built — anyone can authenticate once real OAuth
  credentials exist, but only an invited email gets access to a tenant.
  Gave Justin the concrete Google Cloud Console / Microsoft Entra ID
  registration steps to do on his own time (not blocking).
- **Follow-up: ported the Google Wallet service** from `server.js`'s
  `/wallet/google/:codeId` route — `wallet/service.py` (RS256 JWT signing,
  same `reviewStatus` omission fix already documented in
  `.claude/skills/google-wallet/SKILL.md`) + `wallet/views.py`
  (`GET /wallet/google/<clip_id>/`). Real design question resolved along the
  way: the Node POC had one Wallet OfferClass per `merchant`, reused across
  all their offers, but the new schema ties `OfferChannelConfig` to `Offer`,
  not `Tenant` — resolved by deriving the class id deterministically from
  `tenant.id`, so it's naturally stable/reused per-tenant without a lookup
  query, preserving the original intent. Deliberately did NOT switch the
  wallet barcode from CODE_128/raw clip id to the AI(8112) string — that's
  still an open, unconfirmed decision (plan Open Item 6). Added 4 tests,
  including a real RS256 sign/verify round-trip against a throwaway
  generated keypair (no real service account needed for tests). 16/16 tests
  passing overall.
- **Follow-up: built the TCB integration framework with a mock backing
  implementation**, per Justin's direction — he still needs to request a
  special TCB test/dev account, so build everything to call through a
  swappable seam now rather than block on that. `tcb_integration/client.py`
  defines `BaseTcbClient` (an ABC covering register_offer, assign_provider,
  get_serialization_prefix, deposit_serials, create_fetch_code,
  pull_audit_data) and `get_tcb_client()` — the one factory function
  everything else must go through, switched by `settings.TCB_USE_MOCK`
  (default `True`). `real_client.py` is the actual HTTP implementation
  against TCB's documented endpoints (not yet tested against a live
  account); `mock_client.py` is a stateful in-memory stand-in realistic
  enough to exercise offer→lock→deposit→redemption end to end, including
  the failure buckets (not_locked, no_copies_available, not_owned_by_you,
  invalid_gs1s, already_added), plus a test-only `simulate_redemption()`
  helper since there's no real POS to redeem against in dev.
  `services.py` is the logged business-logic layer (`register_and_lock_offer`,
  `issue_and_deposit_clip`, `pull_and_reconcile_redemptions`) everything
  else should call.
- **Real bug the tests caught**: both service functions were originally
  `@transaction.atomic`, which silently rolled back the exact "this failed"
  log/clip rows they exist to create, every time they raised. Removed the
  decorator — Django's default autocommit is what the "never silently lost"
  design actually needs. 7 new tests, 23/23 passing project-wide.
- Not yet done: real Google/Microsoft OAuth app credentials, a
  Celery-driven async outbox worker (deposits are synchronous for now — fine
  for exercising the framework, not the final design), the consumer-facing
  clip landing page, and — still — real TCB credentials to point
  `RealTcbClient` at and confirm it actually works end to end.

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
