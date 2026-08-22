---
name: qr-coupon-flow
description: The merchant/offer/coupon lifecycle in this app -- how a QR code becomes a redeemable code and how it's structured in the DB. Load this when working on offer creation, QR generation, the scan/landing page, redemption, or the codes/offers/merchants schema.
---

# QR Coupon Flow

Living architecture doc for the core business flow. See `CHANGELOG.md` for
session history and `dev-environment` for local setup.

## Business objects

- **Merchant** — one participating company. Owns exactly one Google Wallet
  `OfferClass` (`merchants.class_id`, format `${ISSUER_ID}.offer_<id>`). Can
  own many Offers.
- **Offer** — a marketing campaign (e.g. "20% off"). Defines `starts_at`,
  `expires_at`, `max_redemptions`, and merchant ownership. Never represents a
  customer.
- **Coupon / Code** — a single issued redemption code. Only created once a
  customer actually scans a QR (`codes` table row). States: `issued` →
  `redeemed` (no `void` state implemented yet despite being mentioned as a
  planned state).

## Flow (server.js)

```
Admin creates Merchant  (POST /admin/merchant)
        |
Admin creates Offer     (POST /admin/offer)
        |
GET /admin/qr/:offerId  -- signs a short-lived JWT (offerId, 15 min expiry,
        |                  HS256 with JWT_SECRET), embeds it as ?t= in a URL,
        |                  renders that URL as a PNG QR code (qrcode package)
        v
Customer scans QR -> GET /o/:offerId?t=...
        |  - verifies JWT signature/expiry
        |  - checks offer.is_active and starts_at/expires_at window
        |  - on success: mints a new codes row (uuidv4, state='issued')
        |  - renders an HTML page with a barcode image + wallet save buttons
        v
GET /barcode/:codeId.png -- CODE_128 barcode via bwip-js, encodes the code UUID
        v
Customer taps "Save to Google/Apple Wallet" -- see `google-wallet` skill
        v
POST /redeem/:codeId  -- merchant-side; flips state to 'redeemed', idempotent
                          (returns already_redeemed if called twice)
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/qr/:offerId` | Render a QR PNG for an offer |
| GET | `/o/:offerId?t=` | Scan landing page; issues a code |
| GET | `/barcode/:codeId.png` | Barcode image for a code |
| GET | `/wallet/google/:codeId` | Google Wallet save redirect (see `google-wallet` skill) |
| GET | `/wallet/apple/:codeId` | Apple Wallet — **stub only**, returns plain text |
| GET | `/admin/dump` | Dumps all merchants/offers/codes as JSON — debug only, no auth |
| GET | `/ping` | Health check |
| POST | `/admin/merchant` | Create a merchant |
| POST | `/admin/offer` | Create an offer |
| POST | `/redeem/:codeId` | Redeem a code |

## Known problems & solutions

- **Every seeded demo offer expires eventually** (they're dated relative to
  when the DB was seeded, not relative to "now"). Check `/admin/dump` for a
  currently-valid offer before demoing, or create a fresh one via
  `POST /admin/offer`.
- **No admin auth on any `/admin/*` route or `/redeem/:codeId`** — anyone who
  can reach the server can create merchants/offers or redeem arbitrary codes.
  Fine for local proof-of-concept, not fine to expose beyond LAN.
- **`codes.state` has no `void`** despite it being listed as a planned state
  in the original notes — only `issued`/`redeemed` exist in the code today.

## TODO

- Add auth to `/admin/*` routes before this goes anywhere near a public
  network.
- Decide whether `void` state is actually needed, and if so implement it
  (fraud/cancellation path).
- `/admin/dump` should not exist in anything resembling production.
