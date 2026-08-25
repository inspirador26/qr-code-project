---
name: coupon-industry-roles
description: Glossary of who's who in the digital coupon industry and how they relate to each other and to us — CPG, Retailer, TCB, Authorized Partner, Provider, Retailer Clearing House, Settlement Provider/Agent. Load this whenever a term like "clearinghouse," "settlement provider," "authorized partner," "manufacturer agent," or "who pays/validates whom" comes up and needs disambiguating — the vocabulary in this industry overlaps in confusing, load-bearing ways, and got corrected multiple times before landing here.
---

# Coupon Industry Roles & Relationships

Domain glossary, not implementation detail. For what our own code actually
calls and how (`tcb_integration/client.py`, mock vs. real), see the
`tcb-integration` skill instead — this doc is purely "who is who and who
talks to whom," so a wrong assumption here doesn't quietly become a wrong
assumption in the data model or a pitch deck again.

This took three corrected passes to get right (2026-08-22 through
2026-08-24 — see `CHANGELOG.md`'s 2026-08-24 entries for the blow-by-blow).
Read this before explaining the business model to anyone new, rather than
re-deriving it from memory.

## The players

- **CPG** — the brand running the promotion (TCB's own term: "manufacturer").
- **Retailer** — accepts the coupon at checkout.
- **TCB (The Coupon Bureau)** — a **neutral validation service, nothing
  more**. It does exactly two things: registers/locks offers, and confirms
  at checkout whether a presented code is real. It is paid **$0.01 per
  clip** (per code deposited into an offer's valid list) by whoever holds
  the Authorized Partner role for that offer. TCB never touches the money
  for the discount itself, and does not define, name, or operate a
  "Clearinghouse" or "Manufacturer Agent" role — those aren't TCB
  constructs (an earlier draft of this thought they were; wrong).
- **Authorized Partner** — a **real TCB role**: whoever registers/locks an
  offer's Master Offer File (MOF) on a CPG's behalf. For our
  `partner_managed` offers, that's **us**. For `client_managed` offers,
  it's some other company the CPG already has this relationship with — we
  are not it, and (confirmed 2026-08-24) we're not building tooling to
  become one for clients who lack it. That's real future scope
  ("smaller clients"), not current scope.
- **Provider** — a second, separate **real TCB role**: whoever deposits
  individual serialized codes ("clips"). This is **always us**, regardless
  of `ownership_mode` — for `client_managed` offers, the CPG's Authorized
  Partner has to explicitly call TCB's `assign_provider` on their side to
  authorize us before we can deposit anything.
- **Retailer Clearing House** — chosen by the **retailer**. Receives the
  retailer's own captured redemption data, sorts it by brand, invoices each
  brand's Settlement Provider. Has zero relationship with TCB.
- **Settlement Provider** (aka **Settlement Agent**) — chosen by the
  **CPG**. Invoiced by the Retailer Clearing House, audits those claims,
  consolidates them into one "retailer pass-through invoice," and invoices
  the CPG. Also has zero relationship with TCB *in this financial
  capacity* — but see the naming-collision note below, since the same
  real-world company sometimes also happens to be a CPG's Authorized
  Partner.

## Two chains that only touch at the very start

**TCB's actual involvement (two touchpoints, nothing else):**
1. Offer registration/locking — Authorized Partner role.
2. Checkout-time validation of a deposited code — the thing the $0.01/clip
   fee pays for.

**The financial settlement chain (TCB is never in this at all):**

```
Retailer → Retailer Clearing House → Settlement Provider → CPG      (invoices flow this way)
CPG → Settlement Provider → Retailer Clearing House → Retailer      (money flows back this way)
```

Everything after "the retailer's scanner checks the code against TCB" is
this second chain — invisible to us and to TCB both.

## Naming collisions — the actual source of confusion in this industry

- **"Provider" (TCB role, us) vs. "Settlement Provider" (CPG's financial
  contractor)** — unrelated concepts, same word. Watch for this in code too:
  `TCB_PROVIDER_ACCESS_KEY`, `assign_provider` mean the TCB role, never the
  financial one.
- **"Authorized Partner"** — a real TCB role (MOF registration), held by us
  for `partner_managed` offers and by someone else for `client_managed`
  ones. Not the same thing as "Settlement Provider," even though the same
  real-world vendor commonly holds both for a given CPG.
- **"Clearinghouse"** — not a TCB-defined term at all. It's specifically
  the **Retailer Clearing House**, chosen by the retailer, and has nothing
  to do with TCB.

## How this maps onto `Offer.ownership_mode`

- `partner_managed` — we hold **both** TCB roles: Authorized Partner
  (register/lock the MOF) and Provider (deposit clips).
- `client_managed` — the CPG's own existing Authorized Partner registers/
  locks the MOF; they call `assign_provider` to authorize us before we can
  deposit clips. We never hold Authorized Partner ourselves on this path.

## Open, deliberately not decided

- Whether a given CPG's Settlement Provider and Authorized Partner happen
  to be the same company varies per client — don't assume either way.
- Acting as a stand-in Authorized Partner for CPGs who don't have one is
  real, plausible future scope — explicitly not part of the current build.
