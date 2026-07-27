# Universal Digital Coupon Project

## Developer / LLM Handoff

---

# Current Status

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

Google Wallet review status displays "[TEST ONLY]" until approved.

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