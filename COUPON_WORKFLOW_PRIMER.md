# Coupon Workflow Primer

For a developer who's new to the digital coupon industry and needs the
mental model before touching the code. Plain-English version — for the
precise glossary/terminology reference, see
`.claude/skills/coupon-industry-roles/SKILL.md` in the repo.

## Start with the real-world thing

A manufacturer coupon is a promise: "if a shopper presents this at
checkout, take money off, and *someone* — not the retailer — reimburses the
retailer for that discount."

## The parties, and where we sit

- **The brand** (a "CPG") wants to run a promotion.
- **The retailer** just wants to scan something at checkout and know it's
  real.
- **TCB (The Coupon Bureau)** is a **neutral validation service** — nothing
  more. It does exactly two things: registers offers, and confirms at
  checkout whether a presented code is real. Whoever registers an offer
  pays TCB **$0.01 per unique code generated** ("clip"), whether or not
  it's ever redeemed. TCB never touches a dollar of the actual discount.
- **Us** — we sit between the brand and TCB.

Two more parties show up later, but only in the money trail — they never
talk to TCB or to us. More below.

## The vocabulary, defined once

- **Offer** — the campaign itself. "$1 off Brand X Cereal, through
  October."
- **Clip** — one shopper's unique copy of that offer, generated on the
  spot.
- **Deposit** — telling TCB "this new code exists and is good to redeem."
- **Redemption** — the retailer scanning it and TCB confirming it's real.
- **Authorized Partner** — TCB's actual term for whoever registers an
  offer and deposits its codes on a CPG's behalf. Sometimes that's us.
  Sometimes the CPG already has someone else doing it, and just hands us
  an offer ID once it's set up.

## The lifecycle, step by step

1. A brand decides on a promotion. Either we register it with TCB on
   their behalf, or the brand already has their own Authorized Partner
   doing that, and just gives us the offer ID afterward. Either way, TCB
   "locks" the offer once registered — like activating a gift card before
   anyone can use it.
2. We give the brand something to distribute — usually a QR code.
3. A shopper scans it. We generate a unique code just for them and
   **deposit** it with TCB. This is the "clip" — the thing TCB charges
   $0.01 for.
4. We hand that shopper a barcode (or a short PIN).
5. The shopper goes to a store. The retailer's checkout scanner checks the
   code directly against TCB. TCB says real/not-real — that's the entire
   extent of TCB's involvement in redemption.
6. **Getting the retailer actually paid never touches TCB or us.** The
   retailer sends its redemption data to its own **Retailer Clearing
   House**, which sorts claims by brand and invoices each brand's
   **Settlement Provider** — a company the CPG separately contracts (may
   or may not be the same company as their Authorized Partner from step 1;
   same vendor, two different jobs, is common). The Settlement Provider
   audits the claims and pays out, with money flowing back down that chain
   to the retailer.
7. Later, we ask TCB which of our codes were validated at checkout —
   that's what feeds the brand's performance dashboard. Whether the
   retailer got paid is happening in that other chain, invisible to us.

## Why any of this is technically interesting

- Steps 1 and 3 are the *only* two places we actually call TCB's API.
  Everything else is us being a normal web app: show a page, handle a
  click.
- **"Never write redeemed from a page a shopper can reach"** — concretely:
  `CouponClip` has a `state` field and a `redeemed_at` timestamp. Setting
  them is one specific piece of code:

  ```python
  clip.state = CouponClip.State.REDEEMED
  clip.redeemed_at = redeemed_at
  ```

  That line only ever runs inside the background job that just pulled
  data from TCB's audit feed — never inside a view responding to an HTTP
  request. If a shopper's browser could trigger it directly (the old Node
  POC actually had `POST /redeem/:codeId`, reachable by anyone), a shopper
  could mark their own coupon "redeemed" without ever using it. And to be
  precise about what that field means: it says "TCB confirmed this code
  was used at a retailer" — nothing about whether the retailer got paid,
  since we don't track that at all.
- **Three overlapping words, three different things** — watch for this
  constantly in code and docs: our own TCB **Provider** role (we hold
  this, for depositing codes), a CPG's **Settlement Provider**
  (financial/claims, unrelated), and **Authorized Partner** (registers
  offers — us or someone else). Same vocabulary, unrelated concepts.
- Because step 3 can be triggered by anyone with the link, the system has
  to assume people might try to spam it — that's the abuse-prevention work
  referenced elsewhere.
- We don't have real TCB access yet, so there's a stand-in ("mock") that
  behaves exactly like TCB would — the current milestone is proving steps
  2–4 work end to end against that stand-in.
