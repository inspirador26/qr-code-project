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

## 2026-09-03 — Codex (with Justin), Objective 2 UI slice

- Added the first real server-rendered UI surfaces for Objective 2:
  `/internal/` now has an internal ops dashboard and `/internal/accounts/new/`
  account intake form, while `/app/` has a tenant-facing dashboard plus
  explicit tenant selection at `/app/tenants/`.
- The internal intake flow creates/updates a `Tenant`, authorized
  `TcbManufacturerLink`, `gs1_8112_barcode` `DistributionChannel`, initial
  partner-managed `Offer`, `OfferChannelConfig`, and optional invited
  `TenantMembership`, then calls `register_and_lock_offer(offer)` through
  the service layer. The TCB registration call is kept outside any atomic
  wrapper so failure logs can survive, matching the backend policy.
- Added tests for internal access gating, account intake creation, tenant
  dashboard membership enforcement, explicit tenant switching, and tenant-
  scoped offer visibility.
- Added `.claude/skills/frontend/django-panel-ui/SKILL.md`, updated the
  frontend segment decision log, refreshed the product/tenancy skill docs,
  and documented the new `/internal/` and `/app/` screens in
  `backend/README.md`.

---

## 2026-09-03 — Codex (with Justin)

- Added `python manage.py seed_demo_offer`, a Django management command under
  `backend/offers/management/commands/`, to create a repeatable demo
  `Tenant` + authorized `TcbManufacturerLink` + `gs1_8112_barcode`
  `DistributionChannel` + partner-managed `Offer` + `OfferChannelConfig`.
  The command builds `base_gs1` with `gs1.data_string.build_base_data_string`,
  calls `tcb_integration.services.register_and_lock_offer(offer)` so the
  mock TCB client will accept deposits, refuses real TCB by default, and
  prints the seeded offer UUID/planned `/offer/<uuid>/` URL.
- Added focused tests for the seeder, including a rerun after resetting the
  in-memory mock TCB state to mimic a fresh command process against an
  already-seeded database.
- Documented the command in `backend/README.md` and updated the TCB skill doc
  so the handoff's "seed demo data first" requirement now points at the
  implemented command.

---

## 2026-09-02 — Claude (with Justin), third entry

- Reorganized `.claude/skills/` from a flat list into segment directories,
  per Justin's request to track policy decisions/issues per area (e.g.
  frontend, backend). New segments: `backend/` (`tcb-integration`,
  `tenancy-and-auth`, `google-wallet`), `frontend/` (empty — no frontend
  built yet), `legacy/` (`qr-coupon-flow`), `product/`
  (`cpg-engagement-workflow`), `domain/` (`coupon-industry-roles`), `infra/`
  (`dev-environment`). Moved via `git mv`, history preserved.
- Added a new main policy skill,
  `.claude/skills/skills-organization/SKILL.md`, documenting the segment
  table, where a new skill doc should go, and the
  `<segment>/DECISIONS_AND_ISSUES.md` convention for cross-cutting
  decisions/known issues that apply to a whole segment rather than one
  feature.
- Created `DECISIONS_AND_ISSUES.md` in every segment, seeded with real
  entries where we already had them: `backend/` got the `/o/` ↔
  `oauth2_provider` routing collision and the "don't wrap
  failure-logging service functions in `transaction.atomic`" pattern
  (both surfaced while spec'ing the offer-clip-flow handoff);
  `legacy/` and `domain/` got the existing Node-POC-is-reference-only and
  TCB-is-not-a-settlement-party corrections, respectively, cross-referenced
  from where they were first recorded. `frontend/` and `infra/` are empty
  templates — no cross-cutting entries exist yet.
- Fixed now-stale `.claude/skills/<name>/SKILL.md` path references in
  `LLM_HANDOFF.md`, `backend/README.md`, `backend/wallet/service.py`,
  `COUPON_WORKFLOW_PRIMER.md`, and `HANDOFF_MVP_DEMO.md` to point at the
  new segmented paths. Left historical references inside past
  `CHANGELOG.md` entries alone (they were accurate at the time written).
  Also corrected `LLM_HANDOFF.md`'s Objective 3 description, which still
  said `GET/POST /o/<offer_token>/...` — that route prefix was already
  known-wrong per the `backend/docs/HANDOFF_offer_clip_flow.md` research
  earlier this session; now points there as the superseding spec.
- **Caveat for next session**: Claude Code's skill listing for this
  session was generated before the move, so this session still only sees
  the new `skills-organization` skill in its available-skills list, not
  the moved ones (`backend:tcb-integration` etc.) — they should appear
  correctly once a fresh session loads `.claude/skills/` from disk. Worth
  confirming next session that nested skills are still auto-discovered and
  invokable the same way.
- Nothing in application code changed — this is docs/skills reorganization
  only.

---

## 2026-09-02 — Claude (with Justin), second entry

- Wrote a standalone, self-contained technical handoff at
  `backend/docs/HANDOFF_offer_clip_flow.md` for the partner's LLM to work
  from directly — covers Objective 3 (offer ID → clippable URI → GS1
  barcode) from the partner-objectives entry above.
- Verified the spec against actual current code (not just the plan docs)
  via a read-only research pass: confirmed `Offer` has no public
  token/slug field yet (needs a migration), confirmed `CouponClip`'s
  existing `unique_serialized_gs1` constraint already enforces
  "never reuse a pincode for an offer" as a side effect of `serialized_gs1`
  embedding the offer's unique `base_gs1`, confirmed `CouponFetchCode` has
  **no** uniqueness constraint at all (flagged as a gap, not fixed), and
  found a real routing collision: `/o/` is already mounted by
  `django-oauth-toolkit` in `config/urls.py`, so the new public offer route
  can't use that prefix (recommended `/offer/<token>/` in the `offers` app
  instead).
- Doc includes exact current signatures for
  `tcb_integration.services.issue_and_deposit_clip`,
  `gs1.data_string.build_serialized_data_string`,
  `gs1.barcode.render_gs1_databar_png`, the existing
  `GET /wallet/google/<clip_id>/` route to reuse as-is, and a
  prerequisite note to create a test `Tenant`+`Offer` via `/admin/` rather
  than waiting on the (separate, not-yet-built) internal intake form.
- Nothing implemented — spec/handoff doc only. No migrations or code
  touched.

---

## 2026-09-02 — Claude (with Justin)

- Justin is bringing a partner onto the `backend/` Django rewrite. Added a
  "Partner handoff — objectives" section to `LLM_HANDOFF.md` (right after
  the superseded notice) and expanded the MVP milestone in
  `.claude/skills/cpg-engagement-workflow/SKILL.md`.
- Three objectives recorded: (1) account creation — a way to create
  `Tenant`s and add `Offer`s under them, supporting multiple tenants with
  correctly-scoped data; (2) two structurally separate UI surfaces — a
  tenant-facing user panel and an `InternalOperator`-gated superuser
  surface (distinct from Django `/admin/`); (3) the first concrete build
  target — offer ID in, clippable URI out: `Offer` + opaque `offer_token`
  → landing page → clip action generates a GS1 AI(8112) data string with a
  unique pincode, deposits it via `tcb_integration.services.issue_and_deposit_clip`
  (mock TCB client), renders the barcode/PIN, and enforces the pincode is
  never reused for that offer (`CouponClip`).
- Nothing implemented yet — planning/handoff docs only. No code, migrations,
  or models touched.
- Next: Objective 1 (account creation via the `internal/` intake form) needs
  to land first since Objective 3 needs a real `Tenant`+`Offer` to run
  against.

---

## 2026-08-24 — Claude (with Justin)

- Produced two executive/onboarding artifacts at Justin's request: a CEO
  pitch one-pager ("The Redemption Layer") and an ERD reference page
  ("Coupon Platform Data Model"), both published as private Claude
  artifacts (not repo files). Then wrote a plain-English developer
  onboarding explanation of the coupon domain in chat.
- **Justin corrected a real domain-model error across all three**: TCB is
  not a "clearinghouse" and does not settle payments — it's a neutral
  validation service only (registers/locks offers, validates codes at
  checkout), funded by the CPG paying TCB $0.01 per clip. He also
  corrected a second, subtler mistake: "Clearing House" and "Manufacturer
  Agent" are not TCB-defined roles either — the **Retailer Clearing
  House** (chosen by the retailer) and the CPG's own **Settlement
  Provider/Agent** are two independent third parties with no relationship
  to TCB at all, who deal directly with each other for the actual
  claims/audit/payment chain (retailer → Retailer Clearing House →
  Settlement Provider → CPG, money flowing back the same path). Confirmed
  this doesn't change any already-built code — `tcb_integration/services.py`
  only ever modeled TCB's two real touchpoints (origination + checkout
  validation/audit-pull), which turns out to be exactly right; the error
  was in the surrounding narrative docs and diagrams, not the
  implementation.
- Fixed the pitch artifact's diagram/copy (dropped "settles" from TCB's
  role everywhere it appeared) and republished it. Fixed the corresponding
  passage in `.claude/skills/cpg-engagement-workflow/SKILL.md`, which had
  previously described "the Clearinghouse role" as something TCB itself
  defines — also flagged a real naming-collision risk for future readers:
  we register with TCB *as a "Provider"* (to deposit codes), which is an
  unrelated concept to a CPG's "Settlement Provider," despite the shared
  word. Also captured a new economics fact worth remembering for the
  billing/invoicing design (still not built): TCB's $0.01/clip fee is a
  real cost floor under whatever we charge a CPG per clip.

## 2026-08-22 — Claude (with Justin), part 7

- Turned part 6's MVP-demo scope into a concrete, ordered implementation
  plan Justin's partner can pick up directly: seed demo data first (new
  management command — `Tenant`/`DistributionChannel`/`TcbManufacturerLink`/
  `Offer`/`OfferChannelConfig`), then a QR generator, then three new
  `coupons/` views (`GET /offer/<uuid>/`, `POST /offer/<uuid>/clip/`,
  `GET /c/<uuid>/barcode-8112.png`), then a manual phone-scan test. Confirmed
  by reading `tcb_integration/mock_client.py` directly (not assumed): the
  seed command must call `register_and_lock_offer(offer)` itself, or every
  clip attempt fails with `not_locked`/`not_owned_by_you` since the mock
  enforces the same lock/authorization checks the real TCB API does.
  Recorded as an "Implementation order" subsection in
  `.claude/skills/tcb-integration/SKILL.md`'s "Current milestone" section —
  no code written yet, this is purely the handoff plan. Justin is handing
  this off to his partner to implement while he continues writing up
  broader architecture/workflow details himself.

## 2026-08-22 — Claude (with Justin), part 6

- Planning-only session (no code changes), resuming the CPG engagement
  workflow discussion from part 5. Walked through accounts (creation/
  maintenance/security), the offer-publication mix (self-service vs.
  internal-registered), offer storage/presentation, and the backend
  mechanics of the public clip endpoint. Decided: internal offer
  registration is a dedicated internal intake form (not session
  impersonation); `ownership_mode` is per-offer, not per-tenant (no schema
  change needed — already modeled that way); clip abuse-prevention is a
  two-axis design (always-on bot detection + a per-offer friction tier,
  `soft` vs. `identity_verified`) — recorded in
  `.claude/skills/cpg-engagement-workflow/SKILL.md`.
- Justin then scoped the actual next build target much narrower: an MVP
  demo proving the full consumer loop end-to-end against the mock TCB
  client — QR code → public offer page → clip → mock deposit → real GS1
  DataBar barcode → scan it and confirm it decodes. Documented the concrete
  technical breakdown in `.claude/skills/tcb-integration/SKILL.md`'s new
  "Current milestone" section: three new views (`GET /offer/<uuid>/`,
  `POST /offer/<uuid>/clip/`, `GET /c/<uuid>/barcode-8112.png`), a new QR
  generator (distinct from the existing GS1 barcode renderer — a plain
  `qrcode` dependency encoding the offer URL, not a GS1 data string), and
  demo fixture data (no onboarding UI exists yet). Caught a real naming
  collision before anyone hit it: `config/urls.py` already routes `/o/` to
  `oauth2_provider.urls`, so the public offer route can't reuse the Node
  POC's old `/o/:offerId` shape — needs `/offer/` or similar instead. Also
  noted `Offer.id`/`CouponClip.id` are already UUIDs, so the opaque-token
  concern from the abuse-prevention discussion is already satisfied by the
  existing primary keys — no new field required. Added a pointer section to
  `backend/README.md` so this is the first thing a partner reads.

## 2026-08-22 — Claude (with Justin), part 5

- Walked Justin through every model currently registered in Django admin
  (confirmed the actual live list via `admin.site._registry`, not just
  grepping `admin.py` files — caught that a naive grep would've included
  inactive `venv` packages like `flatpages`/`redirects` that aren't even in
  `INSTALLED_APPS`). Then added those same descriptions as real in-admin
  help text: `config/admin.py` patches `admin.site.get_app_list` with a
  `MODEL_DESCRIPTIONS` lookup dict (covers our own models and the
  third-party ones — allauth, oauth2_provider, sites, auth — since none of
  those have admin classes we control to attach a description to directly),
  and `templates/admin/app_list.html` overrides Django's own template to
  render it under each model name on the `/admin/` index page. Verified via
  a logged-in test client hitting `/admin/` directly (not just eyeballing
  HTML) that descriptions actually render; full test suite (23) still
  passes.

## 2026-08-22 — Claude (with Justin), part 4

- Committed and merged the Django backend foundation: branched
  `feature/django-backend-foundation` off `staging`, committed everything
  from parts 1-3 below (backend/, updated `LLM_HANDOFF.md`, this file, plus
  `project-docs/AI (8112) Coupon Data SpecificationsV1.1.pdf` which had been
  sitting untracked), merged into `staging`. Caught and removed a stray
  0-byte `smoke_test.sqlite3` before staging — broadened
  `backend/.gitignore`'s `db.sqlite3` to `*.sqlite3` so this class of file
  can't sneak into a commit again.
- Wrote `backend/README.md` — the primary practical handoff doc (setup,
  architecture-by-app, current status, what's not built yet). Added a
  superseded-notice at the top of `LLM_HANDOFF.md` pointing to it, since
  that file previously described only the Node POC with no indication a
  rewrite had happened.
- Justin pushed `staging` and `feature/django-backend-foundation` to
  `origin` (GitHub) — first time either has existed remotely; previously
  local-only. Cleaned up local branches: `feature/django-backend-foundation`,
  `feature/skills-qr-flow-and-wallet`, and `feature/wallet-save-fix-and-docs`
  were all fully merged into `staging` (confirmed via `git branch --merged`
  before deleting) and never pushed anywhere, so `git branch -d` was safe.
  Local branch list is now just `main`/`staging`. The remote
  `feature/django-backend-foundation` branch was deliberately left alone
  (redundant now, but deleting a remote branch is more consequential —
  Justin's call, not made this session).
- Drafted a getting-started message for Justin to send his colleague
  (repo/branch, `backend/README.md` pointer, exact setup commands, note that
  no real credentials are needed to get a working local instance).
- Added two new skills for the Django backend's new domain logic:
  `tcb-integration` (the TCB client seam, mock vs. real, GS1 8112 encoding,
  known gotchas including the pyzint failure and the `@transaction.atomic`
  bug) and `tenancy-and-auth` (tenant isolation mechanism, invite-only SSO,
  the `_EmailUserManager` gotcha). Updated `dev-environment` with Django
  boot instructions and the Postgres-port gotcha; added superseded-pointers
  to `google-wallet` and `qr-coupon-flow` (both still Node-POC-only content)
  noting the Django equivalents, plus documented the wallet class-id and
  barcode-value decisions from the port in `google-wallet`'s TODO.

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
