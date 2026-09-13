# Backend — segment-level decisions & known issues

Policy decisions and known issues that apply across more than one backend
skill doc (`backend/tcb-integration`, `backend/tenancy-and-auth`,
`backend/google-wallet`, `backend/consumer-offer-delivery`), rather than to
just one. See `.claude/skills/skills-organization/SKILL.md` for what
belongs here vs. on an individual skill doc. Newest on top.

---

## 2026-09-13 — Consumer offer links serve the whole flow from the masked domain; no redirect hop

**Requested as**: "ideally this is a masked tiny url style url that allow[s]
our clients to avoid branding directly with us in the marketing material,
we should [b]e operating in the background."

**Decision/finding**: the masked/neutral domain must serve the entire
consumer flow (landing page, clip POST, barcode image, wallet-save link) —
not just an initial redirect that then hands off to our real domain. A
classic bit.ly-style single redirect hop would satisfy the QR/link itself
looking neutral, but the browser address bar would reveal our real domain
the moment the redirect resolves, which defeats the actual ask since this
is a multi-step interactive flow (clip, then view barcode, then optionally
save to wallet), not a one-shot link. Implemented via Host-header-based
`request.urlconf` switching (`offers.middleware.OfferDomainRoutingMiddleware`),
not `django.contrib.sites` — `Site` has no per-domain verification state
and isn't built for routing across many independently-verified hostnames.

**Why it matters beyond one feature**: any future consumer-facing surface
(not just offers) that needs to avoid our branding must follow the same
rule — serve it end-to-end from the masked domain, don't redirect into it.

**How to apply**: see `.claude/skills/backend/consumer-offer-delivery/
SKILL.md` §A3 for the full middleware/urlconf design before adding any new
consumer-facing route.

---

## 2026-09-13 — Per-tenant custom domains (white-label) are spec'd but deliberately not built yet

**Requested as**: asked whether to phase the masked-domain work (shared
neutral domain now, custom domain later) or build both together now, given
no real tenants or TCB credentials exist in any environment. Answer:
"Phase it (Recommended)."

**Decision/finding**: Phase A (shared neutral domain, short opaque
`Offer.public_token`, the active-check guard) is scoped into the current
MVP milestone. Phase B (per-tenant custom domain via CNAME + DNS TXT
verification, `tenancy.models.TenantDomain`, `ALLOWED_HOSTS = ["*"]`) is
fully designed in `consumer-offer-delivery/SKILL.md` but explicitly not
built until an actual client asks for white-labeling.

**Why it matters beyond one feature**: `ALLOWED_HOSTS = ["*"]` is a real
security-relevant setting change (it hands Host-header validation entirely
to our own middleware) — it should only ship alongside the middleware
branch that actually needs it, never speculatively.

**How to apply**: don't add `TenantDomain`, the DNS-verification flow, or
the `ALLOWED_HOSTS` change as part of unrelated work — that's Phase B,
gated on a real white-label request.

---

## 2026-09-13 — Clip eligibility gates on the campaign window, not the redemption window

**Decision/finding**: `offers.services.ensure_offer_clippable` (new guard
closing the gap where `tcb_integration.services.issue_and_deposit_clip` had
zero check on offer status/dates/circulation before depositing) checks
`campaign_start_at`/`campaign_end_at`, not `redemption_start_at`/
`redemption_end_at`.

**Why it matters beyond one feature**: these are two different questions —
the campaign window governs whether a consumer can obtain a clip *right
now*; the redemption window governs whether an already-issued clip is
later accepted at POS, which is TCB's/the retailer's concern at scan time,
not ours at clip time. A clip issued near campaign end should still be
redeemable if the redemption window extends beyond it. Any future code
that needs to check "is this offer still giving out clips" vs. "is this
specific clip still redeemable" should reach for the matching window, not
assume they're interchangeable.

**How to apply**: see `consumer-offer-delivery/SKILL.md` §A2 for the full
guard logic.

---

## 2026-09-02 — `CouponClip.serialized_gs1`'s global unique constraint already prevents pincode reuse per offer

**Decision/finding**: `CouponClip` has `UniqueConstraint(fields=["serialized_gs1"], condition=Q(serialized_gs1__gt=""))` — global uniqueness, not scoped to `offer`. No *additional* per-offer uniqueness constraint is needed: `serialized_gs1` always embeds the offer's own unique `base_gs1` prefix plus the serial, so two clips for the *same* offer with the *same* serial would produce an identical `serialized_gs1` and collide on the existing global constraint anyway. Don't add a redundant `unique_together(["offer", "serial_number"])` — it would be enforcing the same invariant twice.

**Why it matters beyond one feature**: this is the actual mechanism behind "never issue the same pincode twice for an offer," referenced from the consumer-offer-delivery design and the tcb-integration milestone checklist — anyone re-deriving this from scratch might reasonably assume a per-offer constraint is still needed and add a second one.

**How to apply**: if you're ever tempted to add offer-scoped uniqueness on `CouponClip`, don't — confirm this reasoning still holds (i.e. `serialized_gs1` still always embeds `base_gs1`) instead. Write a test asserting `IntegrityError` on two clips for the same offer+serial if one doesn't already exist — this was flagged as a should-do in the now-retired `backend/docs/HANDOFF_offer_clip_flow.md` and doesn't yet have a confirmed test covering it (checked: no `IntegrityError` references exist in `backend/coupons/` or `backend/tcb_integration/` tests as of 2026-09-13).

---

## 2026-09-11 — preserve shared role routing when combining internal intake work

**Decision/finding**: rebasing `feature/new-offer` onto `staging` exposed
competing login defaults: the older feature sent everyone to `/app/`, while
staging introduced `post_login_redirect`. Keep the role-based router and
logout destination from staging, alongside the feature's allauth URL aliases.

**Why it matters beyond one feature**: internal operators must land in the
internal UI, while active tenant members land in the tenant panel. A fixed
redirect to either surface breaks the other actor's login experience.

**How to apply**: keep one shared post-login router. New internal offer
intake stays under the internal-operator gate and calls
`create_offer_for_tenant(tenant=..., data=...)` directly, without changing
tenant session selection. Account intake reuses that same service; keep
TCB registration outside atomic wrappers so failure logs survive.

---

## 2026-09-02 — `/o/` prefix is already claimed, avoid it for new public routes

**Decision/finding**: `config/urls.py` mounts `django-oauth-toolkit` at
`path("o/", include("oauth2_provider.urls", ...))`. Any new public-facing
route (e.g. the planned offer-clip landing page) must **not** use `/o/` as
its prefix — it collides with real existing routes (`/o/authorize/`,
`/o/token/`, etc.).

**Why it matters beyond one feature**: this was discovered while spec'ing
the offer-clip-flow work (see `backend/docs/HANDOFF_offer_clip_flow.md`),
but it's a general constraint on **any** future top-level route choice in
`config/urls.py`, not specific to that feature.

**How to apply**: before adding a new top-level `path()` in
`config/urls.py`, check the existing urlpatterns list there for collisions.
Current top-level prefixes in use: `admin/`, `accounts/`, `o/` (oauth2),
`internal/`, `wallet/`, `api/v1/`, and `""` (root, owned by `coupons.urls`).

---

## 2026-09-02 — service-layer functions that log failures must not be wrapped in `transaction.atomic`

**Decision/finding**: `tcb_integration.services.issue_and_deposit_clip`
(and similar) are deliberately **not** wrapped in `@transaction.atomic`.
They raise on failure by design, and the point is that the "this failed"
log record (`TcbSyncLog`) survives the exception. Wrapping the call in an
atomic block — at the call site or inside the function — silently rolls
back the failure record on exactly the path it exists to capture. This was
an actual bug once, caught by the test suite.

**Why it matters beyond one feature**: this is a pattern, not a one-off —
any future service-layer function in `backend/` that logs an outcome
(success or failure) to a DB row as its primary side effect should follow
the same rule: don't wrap it in atomic unless the log write is meant to be
rolled back with everything else.

**How to apply**: when writing or calling a service function that writes an
audit/log row on failure, check whether that row is supposed to survive a
raised exception. If yes, don't wrap it (or the caller's use of it) in
`transaction.atomic`.
