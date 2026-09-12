# Backend — dossier

State, not history. See `CHANGELOG.md` (grep it) for how things got here,
and the individual `SKILL.md` files in this segment for deep-dive detail on
a specific subsystem. This file is the front door, not the whole reference.
Whoever finishes work on the backend updates §5–§8 in the same commit as
that work — see `DOCUMENTATION_POLICY.md`.

## 1. Scope

Django backend (`backend/`) for a multi-tenant service that distributes
GS1 AI(8112) digital coupon barcodes on behalf of CPG manufacturer clients,
via The Coupon Bureau (TCB), and reports offer performance back to them.

**Explicitly OUT of this dossier's scope:** the legacy Node/Express POC at
the repo root (`server.js`) — see `.claude/skills/legacy/qr-coupon-flow/
SKILL.md`. It's kept only as a behavioral reference during the rewrite,
not something being incrementally migrated.

## 2. Policy

- Every tenant-scoped query must go through code that takes `tenant` as a
  mandatory argument — no client can ever see another client's data. Row-
  Level Security is a planned defense-in-depth layer, not yet implemented.
- Never import a concrete TCB client directly — always go through
  `tcb_integration.client.get_tcb_client()`. See `backend/tcb-integration/
  SKILL.md`.
- Service-layer functions that log an outcome (success or failure) as their
  primary side effect must not be wrapped in `transaction.atomic` — see
  `DECISIONS_AND_ISSUES.md`'s entry on this.
- `/o/` is claimed by `django-oauth-toolkit` — never use it as a prefix for
  a new public route.
- SSO only (Google/Microsoft) — no local username/password signup;
  passwordless email-code login is allauth's fallback until real OAuth
  credentials exist (see §6).

## 3. Where the code is

| App | Responsibility |
|---|---|
| `tenancy` | `Tenant`, `TenantMembership`, `TenantContextMiddleware` — the isolation boundary. Tenant selection always explicit (session), never inferred. |
| `accounts` | Custom email-based `User`, `UserIdentity` (SSO linkage), `InternalOperator` (our ops staff, structurally separate from tenant roles), invite-only `django-allauth` adapter, `post_login_redirect` (role-based routing), `role_flags` context processor. |
| `offers` | `Offer`, `TcbManufacturerLink`, `DistributionChannel`, `OfferChannelConfig`. |
| `coupons` | `CouponClip`, `CouponFetchCode`. |
| `gs1` | AI(8112) VLI encoder/parser + GS1 DataBar rendering. Pure logic, no models. |
| `tcb_integration` | The TCB API seam — `client.py` (interface + mock/real implementations), `services.py` (what callers actually use), `TcbSyncLog`. |
| `wallet` | Google Wallet "Save to Wallet", ported from `server.js`. |
| `reporting` | `ClipEvent`, `RedemptionEvent`, `PromoReport`. |
| `api` | CPG programmatic API scaffolding (`ApiClient` / `django-oauth-toolkit`). Not yet exposing real endpoints. |
| `internal` | Ops-only surface (`InternalOperator`-gated), architecturally separate from tenant routes. |

## 4. Library reliance

- **Postgres** via Docker, host port **5433** (not 5432 — collides with a
  native install on this machine).
- **Redis** via Docker, host port **6380** (not 6379 — collides with an
  unrelated project's container on this machine).
- **`django-allauth`** — SSO-only login; `ACCOUNT_LOGIN_METHODS = {"email"}`
  with no password field means the login-by-code flow is the fallback
  today (see §6). `LOGIN_REDIRECT_URL`/`ACCOUNT_LOGOUT_REDIRECT_URL` point
  at `accounts.views.post_login_redirect` / the login page respectively.
- **`zint-bindings`** for GS1 DataBar barcode rendering.
- **Celery** — configured but `CELERY_TASK_ALWAYS_EAGER=True` locally; no
  async worker actually deployed yet (see §7).
- TCB integration defaults to the in-memory mock
  (`settings.TCB_USE_MOCK = True`); no real TCB credentials exist yet.

## 5. Current state

**Live / built and tested:**
- Full data model, migrated cleanly against Postgres.
- GS1 AI(8112) encoding/parsing + barcode rendering.
- Google Wallet save flow.
- TCB integration framework, mock-backed, full lifecycle including failure
  modes.
- Tenant isolation at middleware/service layer.
- `/internal/` account intake + ops dashboard; `/app/` tenant dashboard +
  explicit tenant selection; role-based post-login redirect; role-gated
  nav; working logout.
- `python manage.py seed_demo_offer` for one-command demo data.

**Built but not wired / read-only on purpose:**
- `RealTcbClient` exists against TCB's documented API but has never been
  smoke-tested against a live account (no credentials yet).
- `api.ApiClient` / DRF scaffolding exists but exposes no real endpoints.

## 6. Known issues

- **`TenantMembership.invited_email` uniqueness bug.** The model has a
  `UniqueConstraint(fields=["tenant", "invited_email"])` that doesn't
  exclude blank values — two memberships on the same tenant can't both
  leave `invited_email` empty. Hit twice seeding local test users. **Fix:**
  make the field nullable and use a conditional/partial unique constraint
  (only enforce uniqueness when non-blank), or exclude blanks explicitly.
- **No real OAuth yet.** Google/Microsoft `SocialApp` credentials aren't
  provisioned, so login falls back to allauth's passwordless email-code
  flow, which prints "sent" emails to the console (dev `EMAIL_BACKEND`) —
  easy to miss if you're not watching the terminal the server is actually
  bound to. Watch for **stale orphaned `runserver` processes** holding
  port 8000 silently (check `Get-NetTCPConnection -LocalPort 8000` on
  Windows) if requests seem to vanish with no log output.
- **No dedicated "no access yet" page.** A logged-in user with no role
  (no `InternalOperator`, no active `TenantMembership`) falls back to the
  bare health-check root via `post_login_redirect` — not an error, just a
  dead end today.

## 7. TO DO

- Real Google/Microsoft OAuth credentials — blocked on Justin provisioning
  client IDs/secrets from each provider's console.
- Real TCB credentials/account — `RealTcbClient` unverified against a live
  account, blocked on Justin getting a TCB dev account.
- The consumer-facing "clip" landing page (scan → clip → barcode) — pieces
  exist (`gs1`, `tcb_integration.services`, `CouponClip`) but nothing ties
  them together yet. Left for last because it's the actual MVP demo
  centerpiece and needed the foundation pieces done first — see
  `backend/docs/HANDOFF_offer_clip_flow.md`.
- Celery-driven async outbox worker — `issue_and_deposit_clip` deposits
  synchronously today; fine for exercising the framework, not the final
  design.
- Fix the `TenantMembership.invited_email` uniqueness bug (§6).

## 8. Feature plans and ideas

- Full CPG-facing dashboard/panel UI, DRF API endpoints, polished invite
  email flow — deferred past the MVP clip demo milestone.
- Postgres Row-Level Security as defense-in-depth on top of the existing
  ORM/service-layer tenant isolation — not urgent while the ORM-layer
  enforcement holds, but the stated ceiling before this is "done."
- A role-aware "no access yet" landing page instead of the current
  fallback-to-root behavior in `post_login_redirect`.

## 9. History pointers

| Date | Entry | Still worth reading because |
|---|---|---|
| 2026-08-22 | Django rewrite decision | Full narrative of why the Node POC was superseded |
| 2026-09-02 | `/o/` route collision found | The reasoning behind the route-prefix policy in §2 |
| 2026-09-03 | First `/internal/` + `/app/` UI slice | What "Objective 2" originally shipped, before role-based routing existed |
| 2026-09-11 | Branch merge + role-based login/nav | This dossier's own origin — see full entry in `CHANGELOG.md` |

## 10. Working on this backend

1. Read this dossier's §5–§8 first — don't trust memory of "what's built."
2. `.claude/skills/infra/dev-environment/SKILL.md` for how to actually boot
   it locally (Postgres/Redis ports, env vars, gotchas).
3. Check `changelog.d/` for any in-flight branch fragments touching this
   segment before assuming the dossier is fully current.
4. Run `python manage.py test` before and after any change — 32 tests as
   of 2026-09-11.
5. Finishing a change here? Update this dossier's §5–§8, the relevant
   `DECISIONS_AND_ISSUES.md` entry if the decision matters beyond one
   feature, and the `changelog.d/<branch>.md` fragment — same commit as
   the code change, not a follow-up.
