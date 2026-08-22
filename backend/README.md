# Coupon Platform — Backend

Django backend for a multi-tenant service that distributes **GS1 AI(8112)
digital coupon barcodes** on behalf of CPG (consumer packaged goods)
manufacturer clients, via The Coupon Bureau (TCB), and reports offer
performance back to them.

This supersedes the Node/Express proof-of-concept at the repo root
(`server.js`), which is kept only as a behavioral reference during the
rewrite (QR generation logic, the Google Wallet JWT construction) — not
something being incrementally migrated. See `../CHANGELOG.md` (search for
"2026-08-22") for the full narrative of how/why this rewrite happened, and
`../LLM_HANDOFF.md` for the pointer from the old docs to here.

## Why Django, why a rewrite

The product is admin/CRUD/reporting-heavy (CPG offer management, internal
ops tooling, multi-tenant dashboards) and needs strict tenant data
isolation, real OAuth SSO, and background job processing for an external
API integration (TCB). Django's built-in admin, migrations, mature OAuth
libraries (`django-allauth`), DRF, and Celery cover essentially all of that
out of the box — a better fit than continuing to hand-roll it in Express.
The switch happened early (foundation phase), before there was any
production deployment or real client data to migrate.

## Quick start

Requires: Python 3.13+, Docker Desktop.

```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash; venv\Scripts\activate.bat on cmd
pip install -r requirements.txt

docker compose up -d                # Postgres (host port 5433, not 5432 — see note below) + Redis
python manage.py migrate
python manage.py createsuperuser    # for /admin/ login
python manage.py runserver
```

Then:
- `http://127.0.0.1:8000/` — health check (no consumer-facing pages exist
  yet — see "Current status" below)
- `http://127.0.0.1:8000/admin/` — full Django admin, all models registered,
  each with a short description of what it's for right on the index page
  (see `config/admin.py` if you need to add/update one — it's a lookup dict,
  not per-model boilerplate)

**Postgres port note**: `docker-compose.yml` maps the container to host port
**5433**, not the default 5432. This is deliberate — if your machine already
runs a native Postgres service on 5432 (common if you've installed Postgres
directly before), mapping there would silently connect Django to the wrong
database instead of this container. If your machine has no conflicting
Postgres, you can change this back to `5432:5432`, but there's no need to.

Copy `.env.example` to `.env` and fill in real values as they become
available (OAuth credentials, TCB credentials, Google Wallet service
account path) — everything has a safe default for local dev in the
meantime, and `TCB_USE_MOCK=True` means the whole TCB integration works
without any real TCB credentials at all (see below).

## Running tests

```bash
python manage.py test
```

23 tests as of this writing, all passing — covers the GS1 data-string
encoder/parser, barcode rendering, the Google Wallet JWT signing, and the
full TCB register→lock→deposit→redeem flow against the mock client.

## Architecture — Django apps

| App | Responsibility |
|---|---|
| `tenancy` | `Tenant`, `TenantMembership`, and `TenantContextMiddleware` — the tenant-isolation boundary. Tenant selection is always explicit (via session), never inferred. |
| `accounts` | Custom `User` (email-based), `UserIdentity` (SSO login linkage), `InternalOperator` (our own ops staff, kept structurally separate from tenant roles), and the invite-only `django-allauth` adapter. |
| `offers` | `Offer`, `TcbManufacturerLink` (a CPG's TCB identity), `DistributionChannel`, `OfferChannelConfig` (per-offer, per-channel config — e.g. where the Google Wallet class id lives). |
| `coupons` | `CouponClip` (one per issued/deposited serial), `CouponFetchCode` (short-lived PIN redemption, TCB's `time_bound_fetch_code`). |
| `gs1` | `data_string.py` (AI 8112 VLI encoder/parser) and `barcode.py` (GS1 DataBar Expanded Stacked rendering via `zint-bindings`). Pure logic, no DB models. |
| `tcb_integration` | The TCB API seam — see below. `TcbSyncLog`/`TcbSyncLogClip` record every call made. |
| `wallet` | Google Wallet "Save to Wallet" — ported from `server.js`. |
| `reporting` | `ClipEvent` (raw funnel telemetry), `RedemptionEvent` (from TCB's audit feed), `PromoReport`. |
| `api` | CPG programmatic API scaffolding (`ApiClient`, wraps a `django-oauth-toolkit` `Application`). Not yet exposing real endpoints. |
| `internal` | Ops-only surface, gated by `InternalOperator`, architecturally separate from tenant-facing routes. |

### Tenant isolation

Every tenant-scoped model carries a denormalized `tenant` FK. The design
intent (stated with real emphasis by the client) is that **no client can
ever see another client's data** — enforced today at the ORM/service layer
(every tenant-scoped query goes through code that takes `tenant` as a
mandatory argument); Postgres Row-Level Security is planned as a defense-in-
depth layer later, not yet implemented.

### The TCB integration seam

This is the part most worth understanding before touching it.
`tcb_integration/client.py` defines `BaseTcbClient`, an interface every part
of the app should go through via `get_tcb_client()` — never import a
concrete implementation directly. Two implementations exist:

- **`mock_client.MockTcbClient`** — stateful, in-memory, realistic enough to
  exercise the full offer→lock→deposit→redemption flow including the
  failure modes (circulation exhausted, not authorized, not locked, already
  deposited). Has a test-only `simulate_redemption()` helper since there's
  no real POS in dev. **This is what's active right now**
  (`settings.TCB_USE_MOCK = True`).
- **`real_client.RealTcbClient`** — actual HTTP calls against TCB's real
  Developer Portal API. Built from TCB's documented API but **not yet
  tested against a live account** — Justin is getting a TCB test/dev
  account; the moment credentials exist, this needs a real smoke test
  before anyone trusts it.

Switching from mock to real is one setting: `TCB_USE_MOCK=False` in `.env`,
plus filling in `TCB_AUTHORIZED_PARTNER_ACCESS_KEY`/`SECRET_KEY` and
`TCB_PROVIDER_ACCESS_KEY`/`SECRET_KEY`. No code changes, no call-site
changes.

`tcb_integration/services.py` sits above the client — this is what the rest
of the app should actually call (`register_and_lock_offer`,
`issue_and_deposit_clip`, `pull_and_reconcile_redemptions`), since it
handles the `TcbSyncLog` bookkeeping uniformly. One thing worth knowing if
you're extending this: these functions are deliberately **not** wrapped in
`@transaction.atomic` — they raise on failure by design, and the whole point
is that the "this failed" log entry survives the exception. Wrapping them in
one atomic block was an actual bug caught by the test suite (silently rolled
back the failure record on the exact path it exists to capture) — don't
reintroduce it.

## Current status (as of this writing)

**Built and tested:**
- Full data model, migrated cleanly against Postgres.
- GS1 AI(8112) data-string encoding/parsing + barcode rendering.
- Google Wallet save flow (ported from the Node POC).
- TCB integration framework, mock-backed, exercising the full coupon
  lifecycle.
- Tenant isolation at the middleware/service layer; invite-only SSO
  provisioning (adapter-level; no real OAuth credentials wired in yet).

**Not yet built:**
- Real Google/Microsoft OAuth credentials — needs `SocialApp` records once
  Justin provisions client IDs/secrets from each provider's console.
- Real TCB credentials/account — `RealTcbClient` exists but is unverified
  against a live account.
- The consumer-facing "clip" landing page (the actual scan → clip → barcode
  flow a shopper would hit) — the pieces it needs (gs1, tcb_integration
  services, CouponClip) all exist, but no view ties them together yet.
- A Celery-driven async outbox worker — `issue_and_deposit_clip` deposits
  synchronously today, which works for exercising the framework but isn't
  the final design (see the plan's TCB integration seam section for the
  intended batched/retried worker).
- Tenant-switch view, CPG-facing dashboard/panel UI, DRF API endpoints.

## A note on the wider plan

This backend was built against a fairly detailed architecture plan (data
model rationale, TCB API specifics, phase sequencing) that currently lives
only in Justin's local Claude Code session, not in this repo. If you need
that level of detail and don't have it, ask Justin — worth getting a copy
into the repo (e.g. `backend/docs/`) if this project continues past this
handoff.
