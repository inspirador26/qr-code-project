---
name: cpg-engagement-workflow
description: Planning doc for the real-world CPG client engagement workflow (sales pitch through billing and reporting) and the resulting UI plan + open evaluation items. Load this when designing onboarding, offer intake, billing/metering, the public clip endpoint, or the CPG-facing panel — none of this is implemented yet, it's a discussion to resume.
---

# CPG Engagement Workflow — Planning (not yet implemented)

This captures a planning discussion from 2026-08-22 that has **not** been
turned into code, data model changes, or an updated architecture plan yet —
Justin's PC restarted mid-session before we could act on it. Pick up here in
a new session rather than re-deriving it. The base architecture this builds
on is `C:\Users\Justin McMahon\.claude\plans\i-am-working-on-compressed-valiant.md`
(still the authoritative plan doc) and `backend/README.md`.

## The workflow, as Justin described it

A digital-media-marketing-driven client engagement:

1. We pitch a CPG on a digital coupon to target shoppers likely to buy at
   specific retailers. Part of the pitch is taking the client's **existing**
   ad creative and adding a QR/coupon layer to it, then distributing to a
   subset of their already-targeted audience.
2. **Billing is per "clip"** — a clip is the pincode/serial we deposit into
   the offer's TCB registry when a shopper generates their own unique
   barcode. This is usage-based metering, not flat-rate.
3. Client signs a coupon agreement, then registers the offer with their
   existing **clearing agent** (Justin's term, synonymous with "settlement
   provider").
4. **Key business fork**: some clearing agents can't register offers to TCB
   at all. We need to determine, per client, whether *their* clearing agent
   can publish to TCB directly, or whether the offer has to be published
   through us instead.
5. A settlement provider is the CPG's source of truth for their offer
   profile and the invoice processor — but the retailer doesn't invoice the
   settlement provider directly. The real chain (corrected 2026-08-24, see
   below): the retailer's own system captures the redemption at checkout,
   sends that data to the retailer's own **Retailer Clearing House**, which
   parses it out by brand and invoices each brand's **Settlement Provider**
   (aka Settlement Agent). The Settlement Provider audits/validates those
   claims, consolidates them into one "retailer pass-through invoice" for
   the CPG, and money flows back down the same chain (CPG → Settlement
   Provider → Retailer Clearing House → Retailer). Offers therefore often
   originate from the Settlement Provider, not from the CPG directly and
   not from us.
6. Client sends us the offer ID. We look up the offer's actual terms in the
   client's TCB account (face value, purchase requirement, offer ID, funder
   ID, valid stores, etc.) to confirm our records are in sync — TCB is the
   source of truth here, not whatever the client types into our panel.
7. We build the offer on our backend and generate the public clip endpoint.
   **Problem, explicitly flagged**: this endpoint needs abuse prevention —
   nothing should be able to burn through thousands of clips by hitting it
   programmatically. Need to maximize unique-clips-per-unique-device as much
   as realistically possible.
8. Distribution is either: (a) we hand the client a DataBar/QR for them to
   insert into their own existing digital media, or (b) the client hands us
   a QR and builds their own creative, and *we* distribute it to a
   client-predetermined audience dataset.
9. Reporting: real-time-ish offer performance via API, likely a daily
   scheduled job plus an on-demand "refresh now" the client can trigger from
   the UI.

## How this refines the existing data model / plan

- **`Offer.ownership_mode`** (`partner_managed` / `client_managed`) already
  captures the right axis, but the *decision driver* is now clearer: it's
  determined by whether the CPG's settlement provider/clearing agent is
  TCB-capable, not just an arbitrary choice on our onboarding form. Worth
  adding a `SettlementProvider`-shaped concept (name, is_tcb_capable) that
  onboarding checks before deciding the ownership_mode.
- **Corrected 2026-08-24 — TCB is not a party to settlement at all**, and
  "Clearinghouse"/"Manufacturer Agent" are not TCB-defined roles (earlier
  drafts of this doc implied they were — wrong). TCB is a **neutral
  validation service only**: it registers/locks offers and validates codes
  at checkout, funded by the CPG paying TCB **$0.01 per clip** (per pincode
  added to an offer's valid list). Full stop — no money for the discount
  itself moves through TCB. The actual reimbursement chain is two
  independent third parties whose *financial/claims relationship* has
  nothing to do with TCB: the **Retailer Clearing House** (chosen by the
  retailer, receives the retailer's captured redemption data) and the
  CPG's own **Settlement Provider/Agent** (chosen by the CPG, invoiced by
  the Retailer Clearing House, audits claims, invoices the CPG). See "The
  workflow, as Justin described it" above (item 5) for the corrected full
  chain.

  **Refined further (2026-08-24, same day)**: the company fulfilling that
  Settlement Provider role for a CPG *may also* separately hold a real TCB
  role — **Authorized Partner** — which is TCB-facing and covers exactly
  one thing: depositing the offer into TCB's Positive Offer File on the
  CPG's behalf. This isn't a new concept — it's the same "Authorized
  Partner" role the plan already uses for *our own* `partner_managed` path
  (`register_offer` in `tcb_integration/client.py`). Settlement Provider
  and Authorized Partner are functionally separate (one's financial/claims,
  one's TCB registration/deposit) — but the *same real-world company* often
  wears both hats for a given CPG, which is exactly the kind of
  industry-language overlap worth staying alert to. **Product scoping
  decision, confirmed by Justin**: for `client_managed` offers, assume the
  CPG already has a working Authorized Partner actively depositing for
  them — building tooling to act as a stand-in Authorized Partner for
  clients who don't have one yet ("smaller clients") is real future scope,
  explicitly **not** part of the current build.
- **Naming collision to watch for in our own docs/code**: we register with
  TCB *as a "Provider"* (to deposit codes — see `TCB_PROVIDER_ACCESS_KEY`,
  `assign_provider` in `tcb_integration`). That is a completely different
  thing from a CPG's "Settlement Provider." Same word, unrelated concepts —
  be explicit about which one is meant anywhere both could appear.
- **New, useful economics fact**: TCB's $0.01/clip fee is a real unit cost
  that lands on whoever registers the offer. For `partner_managed` offers
  that's us — worth factoring into the billing/invoicing design (TODO item
  3 below) as a known cost floor under our own per-clip pricing to the CPG.
- For `client_managed` offers, `Offer.mof_snapshot` should be **populated by
  pulling from TCB** (a read call against the MOF), not hand-entered by the
  client into our form — and this implies a drift-detection concern: the
  client's settlement provider could edit offer terms at TCB later, and we
  won't know unless we re-sync. No re-sync job exists yet.
- **Billing/metering doesn't exist as a concept anywhere yet.** Clips are
  billable units (per the workflow, billed on successful deposit). Needs a
  new model/subsystem — not designed yet, see TODO list below.
- The consumer-facing clip endpoint (never built — see `backend/README.md`
  "Not yet built") now has a concrete new requirement: abuse/fraud
  prevention, not just "build the happy path."

## UI plan, by actor (partially started 2026-09-03)

**Internal sales/ops** (first slice exists in `/internal/`):
- Client onboarding: create `Tenant`, capture manufacturer/TCB link info,
  create an initial partner-managed offer, and optionally create an invited
  `TenantMembership`. Still missing settlement-provider capability capture
  and contract/agreement tracking.
- Offer intake: first slice creates a local partner-managed offer and locks
  it through the mock-backed TCB service path. Still missing real client
  offer-ID lookup/verify and review of pulled TCB terms.
- Usage/billing dashboard: clip counts per client per offer per period —
  what an invoice gets built from.

**CPG client panel** (first slice exists in `/app/`):
- Offer list/detail — a minimal tenant-scoped offer list exists; full detail
  pages, TCB sync status, and read-only `client_managed` term display are
  still missing.
- Self-service "submit an offer ID" flow.
- Distribution assets — download QR/barcode/link, or upload their own
  creative for us to composite/distribute.
- Performance dashboard — clips, redemptions, funnel; daily auto-refresh
  plus a manual "check now."
- Usage/billing view (read-only) — clips charged this period.

**Consumer** (already planned, unchanged in shape): scan → landing page →
clip → barcode/PIN. This is the surface the abuse-prevention problem lives
on.

## TODO — needs dedicated evaluation before design/implementation

1. **Digital media marketing / ad distribution capability.** Compositing a
   QR onto existing creative is a production task; "distribute to a
   predetermined dataset" implies audience targeting and likely a DSP/ad
   platform integration. This is a distinct expertise area outside what's
   been designed so far — needs Justin's input or a specialist before
   proposing any architecture, rather than guessing at an ad-tech pipeline.
2. **Anti-abuse on the public clip endpoint.** No clean solve for "one clip
   per real device" — browsers don't offer a reliable fingerprint, and
   anything that tries harder has its own privacy/legal exposure. Options
   to weigh: IP/session rate-limiting (soft, cheap), cookie/localStorage
   dedup (soft, defeated by clearing cookies), a managed bot-detection
   vendor (Cloudflare Turnstile, HUMAN/PerimeterX, DataDome — stronger,
   adds cost + a vendor relationship), or a lightweight verification step
   (phone/email) for high-value offers (strongest, costs conversion). Real
   fraud-cost vs. friction vs. engineering-cost tradeoff, not a default
   pick.
3. **Billing/invoicing design.** Per-clip metering exists nowhere yet.
   Open questions: prepaid clip bundles vs. postpaid/invoiced monthly;
   which payment processor; whether a clip that deposits successfully but
   the offer later gets voided is still billable.
4. **How we determine settlement-provider TCB-capability.** Is there a
   known list of TCB-capable clearing agents, or do we find out per-client,
   case by case? Affects whether onboarding can be self-service or always
   needs a sales-assisted check first.
5. **MOF drift detection for `client_managed` offers.** If the CPG's
   settlement provider edits offer terms at TCB after onboarding, how/how
   often do we notice? Ties to the daily-sync job; "what do we do on a
   mismatch" (auto-update vs. alert-and-freeze) is a real decision.
6. **Contract/agreement flow.** Is "client signs a coupon agreement" a
   manual/PDF process today, or does it need e-signature tooling
   eventually?

## Follow-up decisions (2026-08-22, second session)

Resumed from the restart above. These are settled directions — still not
implemented (no migrations/views/code touched), but no longer open
questions for the items below.

- **Internal offer registration mechanism (resolves part of TODO item 3,
  the CPG offer-management UX)**: a **dedicated internal intake form**, not
  session impersonation. An `InternalOperator` picks a `Tenant` from an
  internal-only screen and creates/edits `Offer` rows directly against it.
  Explicitly chosen over an "act-as-tenant" login-switch approach, to keep
  faith with the existing principle that internal access stays structurally
  separate and auditable, never confusable with a client's own session/role.
  This lives in the `internal/` app per the existing project structure, not
  as a special mode of the tenant-facing panel.
- **`ownership_mode` granularity**: confirmed **per-offer, not per-tenant**.
  A tenant gets a default mode from onboarding (driven by whether their
  settlement/clearing agent is TCB-capable — TODO item 4 below still governs
  *how* we determine that), but individual offers can override it — e.g. a
  CPG with multiple brands or a clearing-agent change mid-relationship can
  have some offers `client_managed` and others `partner_managed`
  simultaneously. No schema change needed — `Offer.ownership_mode` already
  lives on the offer, not the tenant, in the existing data model; this just
  confirms that's intentional and the internal intake form / self-service
  form both need a per-offer mode selector rather than assuming the tenant's
  default.
- **Clip abuse-prevention model (resolves TODO item 2)**: a two-axis design,
  not a single global policy —
  1. **Always-on bot/scripted-traffic detection** (e.g. Cloudflare
     Turnstile) in front of the public clip endpoint for every offer,
     regardless of tier — this defends against automated hammering, not
     per-offer fraud risk, so it isn't a per-offer choice.
  2. **A per-offer (or per-distribution-channel) friction tier** on top of
     that: `soft` (IP/session rate-limit + cookie/localStorage dedup —
     default) vs. `identity_verified` (phone/email check before a clip
     issues — for higher face-value offers where fraud cost justifies the
     conversion hit). Needs a new field, likely
     `Offer.clip_verification_level` (or on `OfferChannelConfig` if it
     should vary per channel rather than per offer — not yet decided which).
- **Public clip endpoint flow, concretized** (the "not yet built" piece
  flagged in `tcb-integration`'s TODO and `backend/README.md`):
  1. `Offer` gets an **opaque token** (not the sequential PK) used in the
     public URL, e.g. `/o/<offer_token>/` — prevents enumerating offers
     (this tenant's or another's) by incrementing an id. This token is what
     gets encoded into the QR/DataBar/link handed to or received from the
     client.
  2. `GET /o/<offer_token>/` — public landing page, no TCB call, renders the
     offer creative + a clip action. Viewing/scanning alone never issues a
     clip.
  3. `POST /o/<offer_token>/clip` — gated by the bot-detection layer, then
     the offer's friction tier, then calls
     `tcb_integration.services.issue_and_deposit_clip(offer, channel)`.
  4. Response renders whichever channels are configured: GS1 DataBar PNG,
     `CouponFetchCode` PIN, and/or the Google Wallet save button (already
     built at `GET /wallet/google/<clip_id>/`).
  5. `ClipEvent` rows recorded at each step (`link_opened`, `clip_confirmed`,
     `wallet_saved`, `barcode_viewed`) — feeds the client performance
     dashboard.
  6. Note for tenant isolation: this whole path is unauthenticated and has
     no session-selected tenant — `tenant` is threaded through every
     service call via the offer token lookup instead. The "never see
     another tenant's data" guarantee has to hold here too, just via a
     different mechanism than the session-based one used elsewhere.

Still open, deliberately not decided today (carried forward, not blocking):
MOF drift detection/resync policy (TODO item 5), how we determine
settlement-provider TCB-capability (TODO item 4), billing/invoicing design
(TODO item 3), digital-media/ad-distribution capability (TODO item 1).

## Immediate next milestone (2026-08-22, third session; expanded 2026-09-02): scoped-down MVP demo

Justin's near-term definition of success is deliberately narrower than the
full workflow above: **build the customer-facing clip flow end-to-end
against the mock TCB client and prove it with a physical barcode scan** —
QR code → public offer page → clip action → "deposit" via
`MockTcbClient` → render a real GS1 DataBar barcode → scan it and confirm
it decodes correctly. This is the existing plan's Phase 2 "consumer-facing
clip landing page" pulled forward as the concrete next build target, with
the abuse-prevention/verification-tier model designed in the session above
**deliberately deferred, not abandoned** — none of that (bot detection,
per-offer friction tiers, the internal intake form, self-service UI) is
required to prove the core loop works. See `tcb-integration`'s skill doc for
the concrete technical breakdown of what this demo needs (routes, a real
naming collision to avoid, what already exists vs. what's new).

**Added 2026-09-02**: the MVP milestone also needs account creation —
before the QR-to-barcode loop can be demoed, we need to be able to
**create an account (`Tenant`) and add offers under it**, and the demo
should prove this works for **more than one account**, not just a single
hardcoded tenant. Concretely, in scope for this milestone:
- A way to create a `Tenant` (the internal intake form from the
  "Follow-up decisions" section above is the mechanism already agreed on —
  this milestone is the first thing that actually requires it to exist,
  even in a minimal form).
- Create multiple `Tenant` rows, each able to have its own `Offer`(s), and
  confirm offers/clips stay scoped to the right tenant (ties back to the
  existing tenant-isolation guarantee — see `tenancy-and-auth` skill).
- Add at least one `Offer` per account so the clip flow above has something
  real to run against per tenant, rather than a single seeded offer.

This doesn't pull in the rest of the internal-ops UI plan (usage/billing
dashboard, contract tracking, etc.) — just enough of the account layer to
create accounts and attach offers to them ahead of the barcode-scan demo.

## Where to resume

Next session: turn the decisions above into actual schema changes
(`Offer.clip_verification_level` or channel-level equivalent, the offer
token field) and the `internal/` app's intake views, then continue down the
still-open TODO list — items 1 and 4 still need Justin's input specifically,
not just research.

Nothing in this doc has touched code, the data model, or the plan file
itself — no migrations, no new apps, no edits to `offers/models.py` etc.
have happened as a result of this discussion yet.
