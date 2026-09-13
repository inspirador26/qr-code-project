---
name: consumer-offer-delivery
description: Design for serving individual offers to consumers at scale (hundreds of offers across hundreds of tenants) — the masked/white-label public link, the short opaque offer token, and the currently-missing "is this offer still active" guard before depositing a clip with TCB. Not yet built. Load this before starting the consumer-facing clip landing page work, or touching offers/urls.py, offers/views.py, or tcb_integration.services.issue_and_deposit_clip's guard logic.
---

# Consumer offer delivery: masked links, active-check gap, scale

**Status: design only, nothing in this doc is built yet.** This is the
detailed design behind the "consumer-facing clip landing page" item in
`.claude/skills/backend/DOSSIER.md` §7, written up for discussion before
implementation starts. It supersedes the two-token idea from the now-
retired `backend/docs/HANDOFF_offer_clip_flow.md` (folded into
`tcb-integration/SKILL.md`'s milestone checklist) with a single public
token field, and adds the masked-domain requirement, which no prior doc
covered.

## Context

The backend can already register an offer with TCB and issue/deposit a
clip (`tcb_integration.services.issue_and_deposit_clip`), but nothing
serves that to an actual consumer yet — `offers/urls.py` doesn't exist,
`offers/views.py` is a stub, and `Offer` has no public identifier.

Two requirements drove this design:

1. **Every offer link must avoid branding with our platform.** Clients
   don't want their marketing material pointing at our domain — we operate
   invisibly in the background. Decided direction: a neutral shared domain
   by default for every tenant, with an optional per-tenant custom domain
   (CNAME white-label) for clients who want their own domain on the link.
2. **A confirmed, real gap**: `issue_and_deposit_clip`
   (`backend/tcb_integration/services.py:102`) has zero guard today
   checking whether an offer is still active before depositing — it'll
   happily attempt a deposit for a `PAUSED`/`EXPIRED`/`VOID` offer, or one
   outside its campaign window, or one that's already hit `max_clips`.

Given no real tenants or TCB credentials exist yet, this is **phased**:
**Phase A** is scoped to land as part of the current MVP milestone
(alongside the rest of `tcb-integration/SKILL.md`'s scan→clip→barcode
loop). **Phase B** (per-tenant custom domains) is fully spec'd here but
deliberately not built until an actual client asks for white-labeling.

---

## Phase A — build as part of the current milestone

### A1. Short opaque public token on `Offer`

`backend/offers/models.py` — add:
```python
public_token = models.CharField(
    max_length=12, unique=True, db_index=True, editable=False,
)
```
New `backend/offers/tokens.py`:
```python
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # no 0/O/1/I/L
_LENGTH = 10

def generate_public_token() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))
```
Used as the field's callable `default`; retry-on-`IntegrityError` in
`save()` is a nice-to-have, not required at hundreds-of-offers scale (the
unique constraint is the real backstop). This is a compact, QR-friendly
replacement for the raw-UUID/`token_urlsafe(16)` idea floated in the
now-retired `backend/docs/HANDOFF_offer_clip_flow.md` — **one** token
field, not two. New migration
`offers/migrations/0002_offer_public_token.py`; no backfill needed (no
real `Offer` rows exist anywhere yet).

### A2. Fix the active-check gap

New `backend/offers/exceptions.py`:
```python
class OfferNotClippable(Exception):
    user_message = "This offer isn't available right now."

class OfferWindowNotStarted(OfferNotClippable):
    user_message = "This offer isn't live yet — check back soon."

class OfferWindowClosed(OfferNotClippable):
    user_message = "This offer has ended."

class OfferSoldOut(OfferNotClippable):
    user_message = "This offer has reached its clip limit."
```
New `backend/offers/services.py`:
```python
def ensure_offer_clippable(offer: Offer) -> None:
    if offer.status != Offer.Status.ACTIVE:
        raise OfferNotClippable(...)
    now = timezone.now()
    if now < offer.campaign_start_at:
        raise OfferWindowNotStarted(...)
    if now > offer.campaign_end_at:
        raise OfferWindowClosed(...)
    issued = CouponClip.objects.filter(offer=offer).exclude(
        state=CouponClip.State.VOID
    ).count()
    if issued >= offer.max_clips:
        raise OfferSoldOut(...)
```
Gate on `campaign_start_at`/`campaign_end_at`, not the redemption window —
campaign dates govern whether a consumer can obtain a clip *right now*;
redemption dates govern whether an already-issued clip is later accepted
at POS, which is TCB's concern at scan time, not ours at clip time.

**Call this as the first line of `tcb_integration.services.issue_and_deposit_clip`**,
not only from the view — that protects every current and future caller
(view, future API endpoint, management command), matching this codebase's
existing policy of never bypassing the service layer. No circular-import
risk (that module already imports from `offers.models`). The `max_clips`
count query reuses the existing `Index(fields=["offer"])` on `CouponClip`
— no new index needed. Known accepted race: the count isn't
`select_for_update`-locked, so two concurrent requests near the boundary
could both pass; TCB's own `total_circulation` cap remains the hard
backstop, same reasoning already accepted elsewhere in this codebase for
similar eventual-consistency tradeoffs.

Everything else in the "generate a pincode → deposit it into an active
set → deposit to TCB" chain is **already implemented** —
`issue_and_deposit_clip` has TCB itself generate the serial (deliberate:
avoids our own collision handling), and the `CouponClip` table *is* the
active-pincode set, scoped by the `offer` FK with a unique constraint on
`serialized_gs1` that already guarantees no pincode is issued twice for an
offer. No redesign needed there — only the missing guard above.

### A3. Neutral masked domain serving the whole consumer flow

Key design point: a redirect-then-land-on-our-real-domain approach defeats
masking, since the consumer interacts with a multi-step flow (landing →
clip → barcode/wallet). The masked domain must serve the **entire** flow,
not just an initial hop.

New `backend/offers/public_urls.py` (a *second* urlconf, not `include()`'d
into `config/urls.py`):
```python
app_name = "offers_public"
urlpatterns = [
    path("<str:token>/", views.offer_landing, name="offer_landing"),
    path("<str:token>/clip", views.offer_clip, name="offer_clip"),
    path("barcode/<uuid:clip_id>.png", views.offer_barcode_png, name="offer_barcode_png"),
    path("wallet/google/<uuid:clip_id>/", wallet_views.google_wallet_save, name="offer_wallet_save"),
]
```
The wallet route reuses `wallet.views.google_wallet_save` directly, just
mounted under the masked urlconf so that hop never reveals our internal
domain either.

New `backend/offers/views.py` content:
- `offer_landing(request, token)` — `Offer.objects.get(public_token=token)`,
  404 on miss, no TCB call, logs `ClipEvent(LINK_OPENED)`.
- `offer_clip(request, token)` (POST only) — calls
  `tcb_integration.services.issue_and_deposit_clip(...)`; catches
  `OfferNotClippable` and `TcbApiError` separately for distinct user
  messaging; not wrapped in `transaction.atomic` (existing policy); logs
  `ClipEvent(CLIP_CONFIRMED)` on success.
- `offer_barcode_png(request, clip_id)` — reuses
  `gs1.barcode.render_gs1_databar_png(clip.serialized_gs1)` unchanged,
  returns `image/png`, logs `ClipEvent(BARCODE_VIEWED)`.
- One addition to `backend/wallet/views.py::google_wallet_save`: log
  `ClipEvent(WALLET_SAVED)` — already flagged as a should-do in
  `tcb-integration/SKILL.md`'s milestone checklist.

**Domain routing** — new `backend/offers/middleware.py`, first entry in
`MIDDLEWARE` (must run before URL resolution):
```python
class OfferDomainRoutingMiddleware:
    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        if host == settings.OFFERS_SHARED_DOMAIN:
            request.urlconf = "offers.public_urls"
        elif host in settings.INTERNAL_HOSTS:
            pass  # falls through to config.urls, unchanged
        else:
            return HttpResponseBadRequest("Unrecognized host")
        return self.get_response(request)
```
Settings (`backend/config/settings/base.py`):
- `OFFERS_SHARED_DOMAIN` — the neutral, brand-free domain (a short generic
  name Justin registers; in dev, use a **distinct** local hostname like
  `offers.local` via a hosts-file entry so `localhost` keeps serving
  `config.urls` for admin/app testing).
- `INTERNAL_HOSTS` — renamed pointer to today's `DJANGO_ALLOWED_HOSTS`.
- Do **not** set `ALLOWED_HOSTS = ["*"]` in this phase — with only one
  fixed neutral domain plus fixed internal hosts, a normal static
  `ALLOWED_HOSTS` list covering both is sufficient and keeps Django's own
  Host-header protection intact. (`["*"]` only becomes necessary in Phase
  B, once hostnames are added dynamically per tenant.)

This is why the same URLconf can't just serve both domains despite the
path prefixes differing — without this middleware, Django's routing is
Host-agnostic, so the masked domain would also resolve `/admin/`,
`/internal/`, `/o/` (oauth2_provider), etc. The middleware is what keeps
those off the masked domain entirely.

### A4. Building the link

New `backend/offers/links.py`:
```python
def build_offer_url(offer: Offer) -> str:
    return f"https://{settings.OFFERS_SHARED_DOMAIN}/{offer.public_token}/"
```
Single source of truth — QR generation and any future "copy link" UI call
this, never `request.build_absolute_uri()` on our internal domain.
QR-image rendering itself (`offers/qr.py`, `qrcode` dependency) is small
follow-on work already scoped in `tcb-integration`'s "Current milestone"
section — not re-specified here.

---

## Phase B — per-tenant custom domains (spec'd, build on first real request)

- New model `tenancy.models.TenantDomain`: `tenant` FK, `hostname`
  (unique), `verification_status` (pending/verified/failed),
  `verification_token`, `verified_at`. Verification: tenant publishes a
  DNS TXT record at `_coupon-verify.<hostname>`; a `verify_tenant_domain()`
  check (new `dnspython` dependency) confirms it, triggered via a Django
  admin action for now (no self-service UI yet, consistent with how
  `Offer`/`Tenant` creation works today).
- `OfferDomainRoutingMiddleware` gains an `elif` branch: any Host matching
  a `TenantDomain` with `verification_status=VERIFIED` also routes to
  `offers.public_urls`.
- At that point `ALLOWED_HOSTS` must become `["*"]`, because a static list
  can't express "any hostname a future tenant might verify" — this is
  safe **only** because the middleware becomes the sole gatekeeper,
  rejecting anything not in `{shared domain} ∪ {verified TenantDomain} ∪
  {internal hosts}`. Ship that setting change and the middleware change
  together, never independently.
- `build_offer_url()` extends to prefer a tenant's verified domain over
  `OFFERS_SHARED_DOMAIN` when one exists.
- TLS for arbitrary custom domains is an infra/reverse-proxy concern (e.g.
  Caddy on-demand TLS querying "is this domain verified") — not a
  Django-level task, flagged here so it isn't forgotten when Phase B
  starts.

---

## Explicitly out of scope (already tracked elsewhere, not re-litigated)

- Celery async TCB outbox/retry worker.
- Bot/abuse detection and per-offer friction tiers in front of the clip
  endpoint.
- Multi-channel selection logic on the clip view (default/first channel
  is fine for now, per `tcb-integration/SKILL.md`'s milestone section).
- `CouponFetchCode` uniqueness gap, `register_and_lock_offer`'s own
  missing status guard — separate known issues.
- Tenant self-service domain-verification UI (Phase B ships with an admin
  action only).

## Verification (once built)

1. `python manage.py test` — add cases: offer lookup by `public_token`
   404s on unknown token; `offer_clip` returns the friendly message (not a
   500) for `PAUSED`/`EXPIRED`/pre-campaign/post-campaign/`max_clips`-
   exhausted offers; a successful clip creates one `CouponClip` and a
   second attempt at the same offer produces a different serial (proves
   no reuse).
2. Manual end-to-end per the existing milestone doc: run the dev server
   with the masked hostname resolving locally (hosts-file entry for
   `OFFERS_SHARED_DOMAIN`'s dev value), hit the landing page, clip, and
   confirm the browser's address bar never shows the internal/admin
   domain at any point in the flow — then scan the rendered barcode with
   a phone scanner app and confirm it decodes to the expected AI(8112)
   string.
3. Confirm the guard: manually flip a seeded offer's `status` to `paused`
   (or set `campaign_end_at` in the past) via admin and verify `POST
   .../clip` now fails with the friendly message instead of attempting a
   TCB deposit.
