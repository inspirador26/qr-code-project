---
name: google-wallet
description: How Google Wallet save-to-wallet integration works in this app -- OfferClass/OfferObject structure, the save JWT, the Issuer account, and key rotation. Load this when touching /wallet/google/:codeId, wallet-sa.json, the [TEST ONLY] banner, or anything IAM/GCP related to the wallet service account.
---

# Google Wallet Integration

Living architecture doc. See `qr-coupon-flow` for how a code gets here and
`dev-environment` for local env/credential setup mechanics.

## Model

Google Wallet's object model, as used in `server.js`:

- **Issuer** — the org account in the Google Pay & Wallet Business Console.
  Fixed for this app: `ISSUER_ID = 3388000000023034731`, `ISSUER_NAME =
  'Valor'` (the platform's own identity, *not* a merchant).
- **OfferClass** — one per Merchant (`merchants.class_id`, e.g.
  `3388000000023034731.offer_valor`). Defines the chip title, provider name,
  redemption channel. **Never create more than one class per merchant** —
  classes are meant to be stable/reused across all that merchant's offers.
- **OfferObject** — one per issued Code (`${ISSUER_ID}.${codeId}`). Carries
  the offer title, barcode, and valid time interval. This is what actually
  gets saved to the user's wallet.

## The save flow (`GET /wallet/google/:codeId`)

1. Look up the code → offer → merchant.
2. Build a JWT (`aud: 'google'`, `typ: 'savetoandroidpay'`) containing an
   `offerClasses` array (the merchant's class, redeclared inline) and an
   `offerObjects` array (this code's object).
3. Sign it **RS256** with the service account's `private_key`
   (`keys/wallet-sa.json`), `iss` set to `walletKey.client_email`.
4. Redirect to `https://pay.google.com/gp/v/save/<jwt>`. Google decodes the
   JWT, upserts the class/object it describes, and prompts the signed-in user
   to save it.

Because the class is redeclared inline on every single save, whatever fields
you put in `offerClasses` here get applied as an upsert against Google's
stored copy of that class — which is the source of the bug below.

## Known problems & solutions

- **"Unable to load this pass" (fixed 2026-08-22)** — the JWT was sending
  `reviewStatus: 'underReview'` inline in `offerClasses`. The class already
  existed server-side as `approved` (created at some point, likely through
  the Wallet Business Console or an earlier one-time API call — not something
  `server.js` does itself). A save JWT can't downgrade an approved class'
  review status, so Google rejected the whole save. Fix: don't send
  `reviewStatus` at all when the class already exists and is approved.
- **"[TEST ONLY]" banner persists even on approved classes** — this is a
  separate, expected thing. It's controlled by the **Issuer account's own**
  publish/review status in the Wallet Business Console, independent of any
  individual `OfferClass.reviewStatus`. Clearing it requires completing
  Google's review of the issuer account itself, not a code change.
- **Leaked/rotated keys** — `keys/wallet-sa.json` is gitignored and must never
  be pasted through chat. Whoever owns the GCP project (`wallet-qr-project`)
  should mint their own key directly via `gcloud iam service-accounts keys
  create`, rather than the file being transferred. See `dev-environment` for
  the exact commands and current key-holder note.

## TODO

- Apple Wallet (`/wallet/apple/:codeId`) is a stub — returns plain text, no
  `.pkpass` generation. Not started.
- Confirm how/where the merchant `OfferClass`es actually get their initial
  `approved` status set today (doesn't appear to happen in `server.js`) —
  worth documenting the real provisioning step once we trace it.
- `ISSUER_NAME`/`ISSUER_ID` are hardcoded constants; revisit if this app ever
  needs to support more than one issuer account.
