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
  the natural next piece.
