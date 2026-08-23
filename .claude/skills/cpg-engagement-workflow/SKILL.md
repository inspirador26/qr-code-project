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
   profile and the invoice processor: a retailer accepts the digital offer,
   then invoices the settlement provider, who processes the claim on behalf
   of the CPG. Offers therefore often originate from this third party, not
   from the CPG directly and not from us.
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
- Settlement/clearing (financial claims processing, chosen by the CPG) is a
  **different TCB actor than the Clearinghouse role** (chosen/authorized by
  the retailer to settle with the manufacturer) — don't conflate them. Even
  when a CPG's settlement provider can't publish to TCB, we can still
  register the offer ourselves as Authorized Partner; the CPG's own
  settlement provider keeps handling retailer invoicing independently,
  since that's a separate mechanism from MOF registration.
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

## UI plan, by actor (not yet built)

**Internal sales/ops** (nothing like this exists today):
- Client onboarding: create `Tenant`, capture settlement-provider info +
  whether they're TCB-capable, track contract/agreement status.
- Offer intake: receive the client's offer ID, trigger the TCB
  lookup/verify, review pulled terms before activating.
- Usage/billing dashboard: clip counts per client per offer per period —
  what an invoice gets built from.

**CPG client panel** (extends the plan's existing "Panel UI" section):
- Offer list/detail — status, TCB sync status, and for `client_managed`
  offers, terms as last verified against TCB (read-only).
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

## Where to resume

This is a planning/discussion task, not an implementation one — matches how
the original architecture plan was worked through (`EnterPlanMode`/
`AskUserQuestion`) before any code was touched. Next session: pick up with
Justin's follow-up questions on this workflow (he said he wanted to ask more
before closing out), then decide which of the TODO items above are ready to
fold into `i-am-working-on-compressed-valiant.md` and the data model versus
still blocked on his input (items 1 and 4 in particular need him, not just
research).

Nothing in this doc has touched code, the data model, or the plan file
itself — no migrations, no new apps, no edits to `offers/models.py` etc.
have happened as a result of this discussion yet.
