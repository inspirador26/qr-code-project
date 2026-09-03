---
name: tcb-integration
description: How the Django backend talks to The Coupon Bureau (TCB) -- the client seam, mock vs real implementation, GS1 AI(8112) data-string encoding, and the deposit/redemption flow. Load this when touching backend/tcb_integration/, backend/gs1/, offer registration, coupon clip issuance, or anything about TCB credentials/mock mode.
---

# TCB Integration

Living architecture doc for the backend's TCB (The Coupon Bureau) integration
— the core of the actual product (distributing GS1 AI(8112) coupon barcodes
for CPG clients). See `backend/README.md` for setup and `dev-environment` for
running the server. This is Django-only; the Node POC never had this.

## The mental model

Redemption authority lives at TCB, not us. A retailer's POS scans a barcode
encoding a GS1 data string and calls TCB directly to validate — we're never
in that call path. Our job: register/lock offers with TCB, deposit a unique
serialized code per consumer "clip," render that as a barcode, and later
pull redemption data back from TCB's audit API. Full spec grounding is in
`project-docs/AI (8112) Coupon Data SpecificationsV1.1.pdf` and was cross-
checked against TCB's real Developer Portal
(`portal.thecouponbureau.org/developer/api_docs`, Manufacturer API v2.0).

## The client seam

`backend/tcb_integration/client.py` defines `BaseTcbClient` (an ABC) and
`get_tcb_client()` — **the only way anything in the app should reach TCB.**
Never import `RealTcbClient`/`MockTcbClient` directly at a call site.

- `settings.TCB_USE_MOCK` (default `True`) picks which implementation
  `get_tcb_client()` returns. Flip to `False` once real TCB credentials
  exist (`TCB_AUTHORIZED_PARTNER_ACCESS_KEY`/`SECRET_KEY`,
  `TCB_PROVIDER_ACCESS_KEY`/`SECRET_KEY` in `.env`) — no call-site changes
  needed.
- **`mock_client.MockTcbClient`** — stateful, in-memory (class-level dicts,
  reset per-process — it's a test double, not a data store). Realistic
  enough to exercise the full offer→lock→deposit→redemption flow *and* the
  failure buckets (`not_locked`, `no_copies_available`, `not_owned_by_you`,
  `invalid_gs1s`, `already_added`). Has a test/dev-only
  `MockTcbClient.simulate_redemption(serialized_gs1)` helper — no real-TCB
  equivalent, since there's no real POS in dev.
- **`real_client.RealTcbClient`** — actual HTTP calls (`requests`) against
  TCB's documented endpoints, including the `access_key`/`secret_key` →
  24h-token exchange (cached via Django's cache framework). **Not yet
  tested against a live TCB account** as of 2026-08-22 — Justin is
  requesting a TCB test/dev account. Smoke-test this the moment credentials
  exist, before trusting it in any real flow.

TCB identifies stakeholders (manufacturers, us) by **email_domain**, not an
opaque account ID — see `offers.TcbManufacturerLink.manufacturer_email_domain`
and `settings.TCB_PLATFORM_EMAIL_DOMAIN` (our own identity). We hold one
platform-level credential pair per role (Authorized Partner, Provider), not
per-tenant — tenant scoping happens via which manufacturer domains have
authorized us, not via separate secrets.

## The service layer

`backend/tcb_integration/services.py` — call these, not the client directly,
so every call is uniformly logged to `TcbSyncLog`/`TcbSyncLogClip`:

- `register_and_lock_offer(offer)` — **partner_managed offers only** (raises
  `ValueError` for `client_managed` — that path is the CPG's/their partner's
  job, not ours). Creates+locks the MOF, assigns us as Provider.
- `issue_and_deposit_clip(offer, distribution_channel)` — creates a
  `CouponClip`, deposits via `mode="base_gs1"` (TCB generates the serial, we
  don't — avoids our own collision handling). Raises `TcbApiError` on any
  non-`newly_added` outcome; **the clip row still exists** in `ISSUED` state
  either way — never silently lost.
- `pull_and_reconcile_redemptions()` — paginated audit pull →
  `RedemptionEvent` creation → `CouponClip.state` update. Idempotent
  (`get_or_create` on `RedemptionEvent`).

## GS1 AI(8112) data strings and barcodes

`backend/gs1/data_string.py` — VLI (variable length indicator) encoder/
parser matching the spec exactly: `build_base_data_string`,
`build_serialized_data_string`, `parse_data_string`. Pure functions, no DB.

`backend/gs1/barcode.py` — renders GS1 DataBar Expanded Stacked via
`zint-bindings` (`Symbology.DBAR_EXPSTK`, `InputMode.GS1PARENS`, in-memory
PNG via `BARCODE_MEMORY_FILE` + `Symbol.memfile`). **No human-readable text**
(`show_hrt = False`) — deliberate, per spec section 4.1 (fraud mitigation).

## Known problems & solutions

- **`pyzint` (PyPI) does not work for GS1 DataBar encoding.** No
  `input_mode`/GS1-mode flag exposed; fails to encode any GS1 element string
  (`Error 252: Data does not start with an AI`), even for a control AI
  unrelated to 8112. A malformed constructor call also **segfaults** the
  process. Use `zint-bindings` (PyPI: `zint-bindings`, imports as `zint`) —
  confirmed working, has `InputMode.GS1PARENS` and the modern `DBAR_*`
  symbology names. Both packages install a top-level module literally named
  `zint` and will silently shadow each other if both get installed — only
  `zint-bindings` should ever be a dependency.
- **Don't wrap the service functions in `@transaction.atomic`.** Caught by
  the test suite: `register_and_lock_offer`/`issue_and_deposit_clip` are
  designed to raise on failure while leaving the "this failed" `TcbSyncLog`/
  `CouponClip` row behind for investigation. Atomic-wrapping them silently
  rolled back that exact record on the exact path it exists to capture.
  Deliberately not atomic — rely on Django's default autocommit.
- **Local Postgres port conflict**: if `docker compose up` seems to work but
  Django can't authenticate, check whether a *native* (non-Docker) Postgres
  service is already bound to 5432 on the host — `docker-compose.yml` maps
  to **5433** specifically to avoid this; don't "fix" it back to 5432
  without checking `netstat`/`Get-NetTCPConnection` first.

## TODO

- `RealTcbClient` needs a real smoke test against a live TCB account — not
  yet possible, blocked on Justin provisioning credentials.
- No async outbox worker yet — `issue_and_deposit_clip` deposits
  synchronously. The intended design (Celery, batching up to 20 per call,
  retrying 5XX on TCB's documented 10s/20s schedule) isn't built.
- The deposit-response `stakeholders_email_domain` field implies a webhook
  mechanism exists for real-time notification, separate from the polling
  `pull_audit_data` — registration/config for it wasn't found in the API
  reference (may live on TCB's Enterprise Settings page). Unconfirmed, not
  designed around yet.
- `create_fetch_code` (the short-lived PIN / `CouponFetchCode` — likely the
  actual mechanism behind "deposit a unique pincode" from the original
  product discussion) is implemented in both clients but not yet wired into
  any service function or view.
- No consumer-facing view calls any of this yet (`issue_and_deposit_clip`
  etc. are only exercised by tests). The scan→clip→barcode landing page is
  the natural next piece — **now the active build target, see below.**

## Current milestone (2026-08-22): MVP clip demo

Justin's definition of success right now, scoped intentionally narrow: wire
existing pieces together into one physically-demoable loop — **QR code →
public offer page → clip → "deposit" against `MockTcbClient` → render a
real GS1 DataBar barcode → scan it with a phone and confirm it decodes
correctly.** Everything below is new glue around code that already exists
and is already tested; no new business logic, no abuse prevention, no
internal/self-service UI yet (see `cpg-engagement-workflow`'s "Immediate
next milestone" note for what's deliberately deferred).

**New views needed** (none exist yet — `coupons/views.py` only has a health
check, `coupons/urls.py` only routes `""`):
- `GET /offer/<uuid:offer_id>/` — public, unauthenticated landing page.
  Loads the `Offer`, shows title/description/terms, one "Clip this offer"
  button. No TCB call on a plain view.
- `POST /offer/<uuid:offer_id>/clip/` — calls
  `tcb_integration.services.issue_and_deposit_clip(offer, channel)`
  (already built, already hits `MockTcbClient` when
  `TCB_USE_MOCK=True`, the default). Redirects to the resulting clip's
  barcode/detail view.
- `GET /c/<uuid:clip_id>/barcode-8112.png` — wires the already-built
  `gs1/barcode.py` renderer to an HTTP response for the first time. This is
  what actually gets physically scanned to close the loop.

  **Naming collision to avoid**: `config/urls.py` already routes
  `path("o/", include("oauth2_provider.urls", ...))` — the OAuth2 token
  endpoints. Don't reuse `/o/` for the offer landing page (that was the
  Node POC's route shape, `GET /o/:offerId`, but it's now taken). Use
  `/offer/` or similar instead.

- **No new opaque-token field needed.** Both `Offer.id` and
  `CouponClip.id` are already `UUIDField`s (see `offers/models.py`,
  `coupons/models.py`), not sequential integers — the enumeration concern
  raised in the abuse-prevention discussion is already satisfied by the
  existing primary keys. Just use them directly in the URL path.

**New non-view work**:
- **QR code generation** — genuinely new, distinct from `gs1/barcode.py`
  (which renders the *deposited GS1 data string* as a GS1 DataBar for
  scanning at POS). The QR code instead encodes the **offer's public URL**
  (`/offer/<offer_id>/`) — a normal QR, any standard library (e.g. PyPI
  `qrcode`, MIT-licensed) works, no GS1/zint involvement. Natural home:
  `gs1/qr.py` or a small addition to `offers/`, exposed as e.g.
  `GET /offer/<uuid:offer_id>/qr.png`.
- **Demo fixture data** — no onboarding/intake UI exists yet, so a demo
  `Tenant` + `TcbManufacturerLink` + `Offer` (`partner_managed`, since that's
  the path that doesn't require external TCB authorization first) +
  `DistributionChannel` needs to exist to point a QR at. A management
  command or plain Django admin data entry is enough; not worth building a
  form for this milestone.

### Implementation order (start here)

1. **Seed demo data first — everything else depends on it.** New management
   command, e.g. `offers/management/commands/seed_demo_offer.py`:
   `get_or_create` a demo `Tenant`, a `DistributionChannel`
   (`code="gs1_8112_barcode"` — table exists, nothing seeds it yet), a
   `TcbManufacturerLink` (fake domain, `connection_status=authorized`); build
   a `base_gs1` via `gs1.data_string.build_base_data_string(...)`; create the
   `Offer` (`ownership_mode=partner_managed`, valid future campaign/
   redemption windows, `total_circulation`/`max_clips` e.g. 1000) and its
   `OfferChannelConfig`.
   **Sequencing gotcha, confirmed by reading `mock_client.py` directly**:
   the seed command must also call
   `tcb_integration.services.register_and_lock_offer(offer)` right there —
   `MockTcbClient.deposit_serials` checks `mof.locked` and
   `provider_domain in mof.authorized_providers` and raises `not_locked`/
   `not_owned_by_you` otherwise (see `mock_client.py` lines ~145-150). Skip
   this step and every clip attempt will fail before you even get to see a
   barcode. Print the seeded offer's UUID/URL at the end.
2. **QR generator** — add `qrcode` to `requirements.txt`; new small module
   (e.g. `offers/qr.py`) that builds the absolute URL to the offer landing
   page and returns a PNG. Distinct from `gs1/barcode.py`, which encodes the
   *deposited GS1 string*, not a URL.
3. **The three views + urls** described above, in `coupons/`.
4. **Manual end-to-end test**: `runserver` with `LISTEN_HOST=0.0.0.0` (see
   `dev-environment` skill) so a phone on the same LAN can reach it, scan
   the QR, tap clip, scan the resulting barcode with a scanner app, confirm
   it decodes.
5. **Optional but recommended**: a few view-level tests (landing page 200,
   POST clip creates a `CouponClip`, barcode view returns `image/png`) —
   consistent with how the rest of the project is tested (23 passing tests
   as of this writing), not required to hit the manual success bar.

**Verification is manual, not automated**: scan the rendered barcode PNG
with a phone/barcode-scanner app and confirm it decodes to the expected
AI(8112) string (cross-check with `gs1.data_string.parse_data_string`) and
that the serial matches what `MockTcbClient` actually deposited. This is a
physical/visual check, not a new automated test — the encoder/decoder logic
already has unit test coverage.

**Explicitly out of scope for this milestone** (deferred per the
`cpg-engagement-workflow` discussion, not forgotten): bot/abuse detection,
per-offer verification tiers, the internal intake form, self-service offer
creation UI, `ClipEvent` telemetry (cheap to add later, not required to
prove the loop), Celery outbox (synchronous deposit is fine for a demo),
real TCB credentials.
