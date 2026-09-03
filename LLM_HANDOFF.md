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

# Partner handoff — objectives (2026-09-02)

Justin is bringing a partner onto the Django backend (`backend/`). This is
the punch list for that work — everything below builds on the architecture
in `backend/README.md` and the planning discussion in
`.claude/skills/product/cpg-engagement-workflow/SKILL.md`, both worth
reading first. See `.claude/skills/skills-organization/SKILL.md` for how
skill docs are now grouped into segment folders (`backend/`, `frontend/`,
`legacy/`, `product/`, `domain/`, `infra/`).
Do not touch `server.js` (see superseded notice above) — all new work goes
in `backend/`.

## Objective 1 — account creation

We need a way to create accounts. In this codebase "account" = `Tenant`
(see `backend/tenancy/`). Concretely:
- A way to create a new `Tenant` and add `Offer`s under it (`backend/offers/`).
- Must support **multiple** tenants, each with their own offers, with
  offer/clip data staying correctly scoped per tenant (the existing
  tenant-isolation guarantee — every tenant-scoped model carries a `tenant`
  FK and every query takes `tenant` as a mandatory argument; see
  `.claude/skills/backend/tenancy-and-auth/SKILL.md`).
- The mechanism already agreed on for this (see "Follow-up decisions" in
  the `cpg-engagement-workflow` skill doc) is a **dedicated internal intake
  form** in the `internal/` app — an `InternalOperator` picks/creates a
  `Tenant` and creates `Offer` rows against it directly. Not session
  impersonation, not a special mode of the tenant-facing panel.

## Objective 2 — UI for users and superusers

Two distinct UI surfaces, kept structurally separate (this separation is a
deliberate existing principle, not incidental):
- **Users** — the CPG tenant-facing panel. Not built yet; see
  `cpg-engagement-workflow`'s "UI plan, by actor" section for the intended
  shape (offer list/detail, self-service offer submission, distribution
  assets, performance dashboard).
- **Superusers** — internal ops, gated by `InternalOperator`
  (`backend/internal/`), separate from Django's own `/admin/` (which
  already exists and has every model registered — see `backend/README.md`
  "Quick start"). This is where Objective 1's intake form lives.

## Objective 3 (first concrete build target) — offer ID → clippable URI

The first real objective to fulfill end-to-end: **a user gives us an offer
ID, and we turn that into a working clip URI.** Broken into the actual
steps, mapped to what already exists in `backend/`:

1. Take a client's offer ID and create/attach an `Offer`
   (`backend/offers/`), generating its public **URI** — an opaque
   `offer_token` (not the sequential PK — prevents offer enumeration).
   **Route prefix correction (2026-09-02)**: the original plan proposed
   `GET /o/<offer_token>/`, but that collides with `django-oauth-toolkit`,
   already mounted at `/o/` in `config/urls.py` — use a different prefix
   (e.g. `/offer/<offer_token>/`). See
   `backend/docs/HANDOFF_offer_clip_flow.md` for the corrected, verified
   spec (routes, exact current function signatures, migration needed) —
   that doc supersedes the route paths below and in
   `product/cpg-engagement-workflow`'s "Public clip endpoint flow,
   concretized" section.
2. When a user clicks/opens that URI, it's just the landing page — **no
   TCB call yet**, renders the offer + a clip action. Viewing alone never
   issues a clip.
3. The clip action is where the backend process runs:
   - Generate the GS1 AI(8112) **data string** with a **unique pincode**
     for this offer — `backend/gs1/data_string.py` already does the
     encoding/parsing.
   - **Deposit that pincode into TCB** for the offer — call
     `tcb_integration.services.issue_and_deposit_clip(offer, channel)`,
     which already exists and is tested against `MockTcbClient`
     (`TCB_USE_MOCK=True` — no real TCB credentials needed to build/test
     this). Do **not** wrap this in `@transaction.atomic` — see
     `backend/README.md`'s TCB integration seam section for why (it's a
     deliberate design, broke a test once already).
   - **Present the offer for clipping** — render the resulting real GS1
     DataBar barcode (`backend/gs1/barcode.py`) and/or the
     `CouponFetchCode` PIN so the shopper can actually redeem.
   - **Ensure the pincode is never reused for that offer** — this is
     `CouponClip`'s job (`backend/coupons/`), one row per issued/deposited
     serial; confirm the uniqueness constraint is actually enforced
     per-offer, not just per-database, before calling this done.

This is the same flow already scoped as the "MVP clip demo" milestone in
both `backend/README.md` ("Current milestone") and
`.claude/skills/backend/tcb-integration/SKILL.md`. Objectives 1 and 2 above
are new scope layered on top of that milestone (per the
`cpg-engagement-workflow` skill's 2026-09-02 update) —
Objective 3 needs at least one real `Tenant`+`Offer` (Objective 1) to run
against, so build the minimal account-creation path first even if the
rest of Objective 1/2's UI stays rough.

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