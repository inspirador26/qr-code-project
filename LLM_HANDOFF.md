# Universal Digital Coupon Project

## Developer / LLM Handoff

---

# ⚠ Superseded as of 2026-08-22 — read this first

**Active development moved to a new Python/Django backend at `backend/`.**
See `backend/README.md` for the current architecture, how to run it, and
what's built vs. not. Everything below this notice describes the original
Node/Express proof-of-concept (`server.js` at the repo root), which is now
kept only as a **behavioral reference** during the Django rewrite — not
something being incrementally migrated, and not where new work should go.

Why: the real product is a multi-tenant service distributing GS1 AI(8112)
coupons for CPG clients via The Coupon Bureau — substantially bigger in
scope than this POC (strict tenant isolation, OAuth SSO, an external TCB API
integration, admin/reporting-heavy UI). See `CHANGELOG.md` entries dated
2026-08-22 for the full narrative of the decision and everything built so
far.

If you're an LLM picking up this repo: check `backend/README.md` and recent
`CHANGELOG.md` entries before assuming `server.js` is still the thing to
change.

---

# Changelog

This is the standing brief. `CHANGELOG.md` is the running session-by-session log.

**Any assistant (human or LLM) that makes a change in this repo should append an entry to `CHANGELOG.md` before ending the session.**

---

# Current Status (Node POC — superseded, see notice above)

The application has moved beyond a proof-of-concept.

The project now uses a persistent SQLite database instead of in-memory JavaScript objects.

The database is now considered the source of truth.

---

# Development Philosophy

Every feature should:

- survive application restarts
- store state in the database
- expose functionality through APIs
- avoid hardcoded data
- remain modular

Avoid creating additional in-memory state whenever possible.

---

# Business Objects

Merchant

Represents one participating company.

Owns exactly one Google Wallet OfferClass.

Can own many Offers.

---

Offer

Represents a marketing campaign.

Examples:

20% Off

Buy One Get One

Free Shipping

Offers define:

- active dates
- redemption limits
- merchant ownership

Offers never represent customers.

---

Coupon (Code)

Represents a single issued coupon.

Coupons only exist after a customer scans a QR code.

Each coupon has its own lifecycle.

States

issued

redeemed

void

---

Google Wallet

OfferClass

One per Merchant.

OfferObject

One per Coupon.

Never create multiple OfferClasses for the same merchant.

---

Current Endpoints

GET

/admin/qr/:offerId

/o/:offerId

/barcode/:codeId.png

/wallet/google/:codeId

/wallet/apple/:codeId

/admin/dump

/ping

POST

/admin/merchant

/admin/offer

/redeem/:codeId

---

Current Flow

Merchant

↓

Offer

↓

Generate QR

↓

Customer Scan

↓

Validate JWT

↓

Lookup Offer

↓

Issue Coupon

↓

Generate Barcode

↓

Wallet Pass

↓

Redeem API

---

Coding Standards

Keep Express routes lightweight.

Business logic belongs in service layers.

Eventually organize:

controllers/

services/

wallet/

database/

models/

routes/

middleware/

Avoid hardcoded merchant information.

Database first.

Memory second.

---

Known Issues

Google Wallet OfferClass metadata is cached.

Google Wallet passes display a "[TEST ONLY]" banner. This is governed by the
Issuer account's own publish/review status in the Google Pay & Wallet Business
Console — it is independent of each OfferClass's `reviewStatus` field, which is
already `approved` for all seeded merchants. Getting rid of the banner requires
completing Google's issuer-account review, not a code change.

Apple Wallet has not yet been implemented.

---

Future Goals

Merchant CRUD

Offer CRUD

Analytics

Authentication

Rate Limiting

Fraud Detection

Merchant Dashboard

Apple Wallet

POS Integration