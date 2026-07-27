# Universal Digital Coupon Platform

## Project Summary

This project is a proof-of-concept for a Universal Digital Coupon platform centered around QR codes, dynamic coupon issuance, mobile wallet integration, and REST APIs.

Unlike traditional printed coupons, QR codes do **not** contain the coupon barcode.

Instead, every QR code points to our server, where a unique coupon is generated on demand.

This architecture allows:

- unique coupons for every customer
- real-time validation
- merchant branding
- fraud prevention
- redemption tracking
- expiration enforcement
- Google Wallet integration
- future Apple Wallet support
- compatibility with GS1 8112 Universal Digital Coupons

---

# Current Architecture

Current Technology

- Node.js
- Express
- SQLite (better-sqlite3)
- QRCode
- bwip-js
- jsonwebtoken
- uuid
- Google Wallet API

Future

- Apple Wallet
- PostgreSQL
- Merchant Portal
- Admin Dashboard

---

# Database

SQLite is currently used for development.

Reasons:

- no installation
- portable database file
- extremely fast
- easy backup
- ideal for proof-of-concept work

The architecture intentionally isolates database access so PostgreSQL can replace SQLite later.

Current Tables

merchants

Stores merchant information.

One merchant owns one Google Wallet OfferClass.

offers

Stores offers owned by merchants.

Contains:

- title
- active dates
- redemption limits
- merchant relationship

codes

Stores every issued coupon.

Each QR scan generates one record.

States:

- issued
- redeemed
- void

api_logs

Reserved for future API logging.

---

# Overall Flow

Merchant

↓

Offer

↓

Generate QR

↓

Customer Scan

↓

Server Endpoint

↓

Validate JWT

↓

Load Offer

↓

Issue Coupon

↓

Generate Barcode

↓

Display Coupon

↓

Google Wallet

↓

Apple Wallet (future)

↓

Retail POS

↓

Redeem API

---

# Current Features

✓ QR Generation

✓ SQLite persistence

✓ Merchant API

✓ Offer API

✓ Barcode generation

✓ Google Wallet integration

✓ Coupon issuance

✓ Coupon redemption

✓ REST API

---

# Future Features

Merchant Portal

Analytics

Coupon clipping

Rate limiting

Fraud detection

Retail POS integration

GS1 8112 barcode generation

Apple Wallet

Authentication

Reporting