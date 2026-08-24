# Handoff: MVP Clip Demo

For whoever's picking up the next chunk of backend work. This is a
standalone summary — the living detail lives in the two skill docs linked
at the bottom, which this doc will drift from over time, so treat those as
the source of truth if anything here looks stale.

## Setup

Everything you need is in `backend/README.md`. Short version:

```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash
pip install -r requirements.txt
docker compose up -d                # Postgres (host port 5433) + Redis
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

No real credentials needed — `TCB_USE_MOCK=True` is the default, so the
whole TCB integration works against an in-memory mock.

## The goal

Prove one physical, demoable loop end-to-end, using pieces that already
exist and are already tested:

**QR code → public offer page → clip action → "deposit" against the mock
TCB client → render a real, scannable GS1 DataBar barcode → scan it with a
phone and confirm it decodes correctly.**

No abuse prevention, no internal/self-service offer UI, no real TCB account
— all of that is designed (see `cpg-engagement-workflow` skill) but
deliberately out of scope for this pass.

## What already exists (don't rebuild these)

- Full data model, migrated: `Tenant`, `Offer`, `CouponClip`,
  `DistributionChannel`, `OfferChannelConfig`, `TcbManufacturerLink`.
- `tcb_integration.services.register_and_lock_offer(offer)` and
  `issue_and_deposit_clip(offer, channel)` — the actual business logic,
  already hitting `MockTcbClient`, already covered by tests.
- `gs1.barcode.py` — renders a GS1 DataBar Expanded Stacked PNG from a
  serialized AI(8112) string, via `zint-bindings`.
- `gs1.data_string.py` — the encoder/parser/validator for that string.

## Data model reference

Full ER diagram, generated from the actual `models.py` files (not a
proposal): https://claude.ai/code/artifact/dc68d8e9-3b09-48e5-b5a9-b9bf607f1eea
— overview diagram first, then six domain-scoped diagrams (Tenancy &
Identity, Offers & TCB Linkage, Coupons, TCB Sync/Outbox, Reporting, API
Access) with full attributes and a caption on each calling out the one
design decision that matters there. Useful before touching the seed command
in step 1 below, since it shows every FK the seeded rows need to satisfy.

Note: this is a private Claude artifact — share it from the page's share
menu if the link doesn't open for you.

## What's missing — build in this order

1. **Seed demo data first.** New management command (e.g.
   `offers/management/commands/seed_demo_offer.py`) that creates a demo
   `Tenant`, a `DistributionChannel` (`code="gs1_8112_barcode"` — nothing
   seeds this table yet), a `TcbManufacturerLink`, and an `Offer`
   (`ownership_mode="partner_managed"`) + its `OfferChannelConfig`.

   **Important, verified by reading `mock_client.py` directly**: the seed
   command must also call `register_and_lock_offer(offer)` itself. The mock
   checks `mof.locked` and `provider_domain in mof.authorized_providers`
   before accepting a deposit — skip this and every clip attempt fails with
   `not_locked`/`not_owned_by_you` before you ever see a barcode.

   Have the command print the seeded offer's UUID/URL when it's done.

2. **QR generator.** Add `qrcode` to `requirements.txt`. Small new module
   (e.g. `offers/qr.py`) that takes an offer, builds the absolute URL to its
   landing page, and returns a PNG. This is a plain URL-encoding QR, not
   GS1-related — don't route it through `gs1/barcode.py`, that's for the
   deposited coupon string specifically.

3. **Three new views, in `coupons/`** (`coupons/views.py` currently only
   has a health check; `coupons/urls.py` only routes `""`):
   - `GET /offer/<uuid:offer_id>/` — public landing page: offer info + the
     QR embedded + a "Clip this offer" button. No TCB call on a plain GET.
   - `POST /offer/<uuid:offer_id>/clip/` — calls
     `issue_and_deposit_clip(offer, channel)`, redirects to the barcode.
   - `GET /c/<uuid:clip_id>/barcode-8112.png` — wires `gs1/barcode.py` to an
     HTTP response for the first time.

   **Watch out**: `/o/` is already routed to `oauth2_provider.urls` in
   `config/urls.py`. Don't reuse the old Node POC's `/o/:offerId` shape —
   use `/offer/` instead, or you'll collide with the OAuth2 token endpoints.

   No new "opaque token" field is needed for the URLs above — `Offer.id`
   and `CouponClip.id` are already `UUIDField`s, not sequential integers, so
   they're already safe to expose directly in a path.

4. **Manual end-to-end test.** Run the server with `LISTEN_HOST=0.0.0.0` (see
   `dev-environment` skill for why) so a phone on the same LAN can reach it.
   Scan the QR → land on the offer page → tap clip → scan the resulting
   barcode with a scanner app → confirm it decodes.

5. **Optional, recommended**: a few view-level tests (landing page 200,
   POST clip creates a `CouponClip`, barcode view returns `image/png`) to
   match how the rest of the project is tested (23 passing tests as of this
   writing). Not required to hit the manual success bar above.

## Full detail / living docs

- `.claude/skills/tcb-integration/SKILL.md` — "Current milestone" section
  has the same breakdown as above plus the TCB client architecture, mock
  vs. real, and known gotchas (e.g. the `pyzint` vs `zint-bindings` issue).
- `.claude/skills/cpg-engagement-workflow/SKILL.md` — the broader product
  workflow this milestone is a deliberately narrow slice of (accounts,
  offer-ownership modes, abuse prevention design, still not built).
- `CHANGELOG.md` — session-by-session narrative if you want the "why" behind
  any of the above.
