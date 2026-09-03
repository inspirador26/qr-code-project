# Handoff: Offer ID → Clippable URI flow

**Status:** not started. No code, migrations, or views for this exist yet.
**Written:** 2026-09-02, by Claude (Sonnet 5) working with Justin, for a new
partner joining this project. This doc is meant to be handed to that
partner's own LLM/assistant as a self-contained spec — it doesn't assume
you have any other context from this repo's chat history, only the repo
itself.

## What this repo is

Django backend (`backend/`) for a multi-tenant service that distributes
GS1 AI(8112) digital coupon barcodes on behalf of CPG (consumer packaged
goods) manufacturer clients, via **The Coupon Bureau (TCB)** — an external
validation service that registers/locks offers and validates codes at
checkout. Read `backend/README.md` in full before starting; it has the
architecture table, the tenant-isolation model, and the TCB integration
seam explained. This doc assumes you've read it.

There is also an older Node/Express proof-of-concept at the repo root
(`server.js`). **Ignore it** — it's kept only as a behavioral reference,
not something being migrated. All new work goes in `backend/`.

## The objective

A user (internally, for now — see "Out of scope" below) gives us an offer
ID. We need to turn that into a **working, shareable URI** such that:

1. Visiting the URI shows a public offer landing page.
2. Clicking a "clip" action on that page triggers a backend process that:
   - generates a GS1 AI(8112) **data string** containing a **unique
     pincode/serial** for this specific offer,
   - **deposits that pincode into TCB** for the offer,
   - **presents the offer for clipping** — renders the real barcode (and/or
     PIN) the shopper uses,
   - and guarantees that **exact pincode is never issued again for that
     offer**.

This is the "MVP clip demo" milestone already referenced in
`backend/README.md` ("Current milestone") — you're building the actual
implementation of it.

## What already exists (verified against the current codebase — use these,
## don't rebuild them)

- **`offers.models.Offer`** (`backend/offers/models.py`) — has `id` (UUID
  PK), `tenant` FK, `base_gs1` (unique), `title`, `description`, `status`
  (draft/pending_tcb_registration/locked/active/paused/expired/void), plus
  campaign/redemption date fields and `total_circulation`/`max_clips`.
  **It has no public-facing token/slug field yet** — you need to add one
  (see "What you need to build," step 1).
- **`offers.models.OfferChannelConfig`** — join table between `Offer` and
  `DistributionChannel`, per-channel JSON config (e.g. where a Google
  Wallet class id lives). Unique on `(offer, channel)`.
- **`tenancy.models.Tenant`** (`backend/tenancy/models.py`) — `id` (UUID),
  `name`, `legal_name`, `status`, `billing_contact_email`. No slug field
  either.
- **`gs1.data_string`** (`backend/gs1/data_string.py`), pure functions, no
  DB — encoding/decoding the AI(8112) data string:
  ```python
  def build_base_data_string(coupon_format: str, funder_id: str, offer_code: str) -> str
  def build_serialized_data_string(coupon_format: str, funder_id: str, offer_code: str, serial_number: str) -> str
  def parse_data_string(data_string: str) -> ParsedDataString
  ```
- **`gs1.barcode`** (`backend/gs1/barcode.py`) — barcode rendering:
  ```python
  def render_gs1_databar_png(serialized_data_string: str) -> bytes
  ```
  Takes the **full serialized string** (e.g. `CouponClip.serialized_gs1`),
  not a raw serial — it reformats internally to GS1-parens form and renders
  via `zint` (`DBAR_EXPSTK` symbology). Returns raw PNG bytes.
- **`tcb_integration.services`** (`backend/tcb_integration/services.py`) —
  the seam you call, never the raw client:
  ```python
  def register_and_lock_offer(offer: Offer) -> Offer          # line 46
  def issue_and_deposit_clip(offer: Offer, distribution_channel, *, created_via=None) -> CouponClip   # line 102
  ```
  `issue_and_deposit_clip` is confirmed **not** wrapped in
  `@transaction.atomic`, deliberately — its own docstring explains this is
  so a failure-log record (`TcbSyncLog`) survives the exception it raises
  on a non-success outcome. **Read this function's full body before calling
  it** — this doc has its signature and intent but you should verify
  exactly what it populates on the returned `CouponClip` (in particular,
  whether it already sets `serialized_gs1`/`serial_number` for you, or
  whether your view needs to build the data string itself via
  `gs1.data_string` and pass it in). Do not guess; read the code.
  Currently backed by `MockTcbClient` (`TCB_USE_MOCK=True` in `.env` by
  default) — stateful, in-memory, exercises the full
  register→lock→deposit→redeem lifecycle including failure modes
  (circulation exhausted, not authorized, not locked, already deposited).
  You do not need real TCB credentials to build or test this.
- **`coupons.models.CouponClip`** (`backend/coupons/models.py`) — one row
  per issued/deposited serial. Fields include `offer` FK, `tenant` FK,
  `distribution_channel` FK, `serialized_gs1`, `serial_number`, `state`
  (issued/pending_deposit/deposited/redeemed/expired/void), timestamps,
  `created_via` (qr_scan/direct_link/api). **Constraint that already
  enforces "never reuse this pincode for this offer":**
  ```python
  models.UniqueConstraint(
      fields=["serialized_gs1"],
      name="unique_serialized_gs1",
      condition=models.Q(serialized_gs1__gt=""),
  )
  ```
  This is global uniqueness on the full serialized string, not scoped to
  `offer` explicitly — but since `serialized_gs1` always embeds the
  offer's own unique `base_gs1` prefix plus the serial, a global-uniqueness
  constraint on the full string already guarantees per-offer serial
  uniqueness as a side effect (two clips for the same offer with the same
  serial number would produce the identical `serialized_gs1` value and
  collide). **Confirm this understanding by writing a test that tries to
  create two `CouponClip`s with the same offer+serial and asserts the
  second raises `IntegrityError`** — don't just trust this doc, prove it.
- **`coupons.models.CouponFetchCode`** — a separate PIN-based redemption
  mechanism (TCB's `time_bound_fetch_code`), for POS/e-comm channels where
  a barcode isn't practical. Has a `fetch_code` field with **no uniqueness
  constraint at all today** — if your offer's distribution channel needs
  PIN-based redemption (check `DistributionChannel`/`OfferChannelConfig`
  for the channel you're building against), that's a real gap you'd need
  to close. If you're only building the barcode path for the MVP demo, you
  can leave this alone and flag it as follow-up.
- **`GET /wallet/google/<uuid:clip_id>/`** (`backend/wallet/urls.py`,
  `backend/wallet/views.py`) — already built and working. `clip_id` is a
  `CouponClip` pk. Looks up the clip, redirects to the Google Wallet save
  URL. Reuse this as-is for the "save to wallet" option on your landing
  page — don't rebuild it.
- **`reporting.models.ClipEvent`** (`backend/reporting/models.py`) — funnel
  telemetry, `tenant`/`offer`/`coupon_clip` (nullable) FKs, `event_type`
  choices already defined exactly as needed:
  `link_opened`, `clip_confirmed`, `wallet_saved`, `barcode_viewed`. Log one
  of these at each corresponding step in your new views (see step 3 below).
  Check whether the existing `wallet` view already logs `wallet_saved` —
  if not, add it there too.

## What you need to build

### 1. Add a public token field to `Offer`

`Offer` currently has no way to be looked up from an untrusted public URL
without leaking sequential/enumerable info (its PK is a UUID already, which
is not sequential, but using the PK directly in a public URL still isn't
great practice for this kind of consumer-facing surface — prefer a
separate opaque token you control the generation of). Add something like:

```python
offer_token = models.CharField(max_length=32, unique=True, db_index=True, editable=False)
```

generated with `secrets.token_urlsafe(16)` (or similar) at creation time —
either a default callable or set in `save()`/a `pre_save` signal if it's
unset. Write the migration. Backfill isn't a concern since no `Offer` rows
exist in any real environment yet.

### 2. New views + routes for the landing page and clip action

**Route prefix — do not use `/o/`.** The root `backend/config/urls.py`
already mounts `django-oauth-toolkit` there:
```python
path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
```
A public offer route at `/o/<token>/` would collide with that namespace
(`/o/authorize/`, `/o/token/`, etc. are already real routes). Pick a
different prefix — e.g. `/offer/<token>/` — and put the app-level routes in
a new `backend/offers/urls.py` (the `offers` app already exists and owns
`Offer`, but currently has no `urls.py` and only a stub `views.py`), then
wire it into root urls:
```python
path("offer/", include("offers.urls")),
```
Full current root urlpatterns for reference (`backend/config/urls.py`):
```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("internal/", include("internal.urls")),
    path("wallet/", include("wallet.urls")),
    path("api/v1/", include("api.urls")),
    path("", include("coupons.urls")),
]
```
Note `coupons.urls` already owns the site root (`""`) with a placeholder
`health` view whose docstring explicitly says the real clip landing page
was planned to land here — that plan predates the `/o/` collision being
noticed. Building it in `offers` instead (as above) is the cleaner choice
now; just make sure whichever app you pick, you're not fighting
`coupons`'s existing root mount.

**View 1 — landing page**, `GET /offer/<token>/`:
- Look up `Offer` by `offer_token`, 404 if missing.
- **No TCB call here.** Render the offer (title, description, an image if
  you have one, a "Clip this offer" button/form that POSTs to view 2).
- Log a `ClipEvent(event_type=LINK_OPENED, ...)`.

**View 2 — clip action**, `POST /offer/<token>/clip`:
- Look up the same `Offer`.
- Determine the `distribution_channel` to pass to
  `issue_and_deposit_clip` — check how `DistributionChannel` /
  `OfferChannelConfig` are meant to be selected here (read
  `offers/models.py` for those models); for the MVP demo this can likely
  be a single hardcoded/default channel per offer.
- Call `tcb_integration.services.issue_and_deposit_clip(offer, channel,
  created_via=CouponClip.CreatedVia.DIRECT_LINK)` (check the actual enum
  name/value in `coupons/models.py` — don't guess the exact member name).
- On success: log `ClipEvent(event_type=CLIP_CONFIRMED, coupon_clip=clip)`,
  then render/redirect to a result page showing:
  - the barcode: `gs1.barcode.render_gs1_databar_png(clip.serialized_gs1)`
    served as an image (log `ClipEvent(event_type=BARCODE_VIEWED, ...)`
    when this is actually displayed — decide whether that's the same
    request or a separate image-serving endpoint you hit from an `<img
    src>`, which is more accurate for "viewed"),
  - a link to `GET /wallet/google/<clip.id>/` for "Save to Google Wallet",
  - a `CouponFetchCode` PIN only if the channel requires it (see the note
    above about the missing uniqueness constraint there).
- On failure (the service raises — this is by design, not a bug): catch
  it in the view, show the user a friendly error, **do not** wrap the
  service call in your own `transaction.atomic()` block either, for the
  same reason described in its docstring.

### 3. Tests

- Unit/integration tests against `MockTcbClient` (already the default) for
  the full landing → clip → barcode path, including the "second clip
  attempt with a forced-duplicate serial fails" case described above.
- Then a manual physical test: run the dev server, hit the landing page
  from a phone (see `backend/README.md` / the `dev-environment` skill doc
  for LAN/dev-server setup if you need your phone on the same network),
  clip, and **scan the rendered barcode with a real barcode scanner app**
  to confirm it decodes to the expected AI(8112) string. This physical
  scan is the actual acceptance bar for this milestone, not just green
  tests.

## Prerequisite: you need a real `Tenant` + `Offer` to test against

The proper way to create these (an internal intake form, gated by
`InternalOperator`, in the `internal/` app) is a **separate, not-yet-built
objective** — don't build it as part of this work. For now, create a test
`Tenant` and `Offer` (and a `DistributionChannel` /
`OfferChannelConfig` if your clip view needs one) via the Django admin
(`/admin/` — already fully registered, see `backend/README.md` "Quick
start") or a `python manage.py shell` session / a throwaway management
command. Don't block this objective on the intake form existing.

## Out of scope for this objective (explicitly deferred elsewhere, not

## forgotten)

- Bot/scripted-traffic detection in front of the clip endpoint, and the
  per-offer friction-tier (`soft` vs `identity_verified`) model. Real
  requirement, deliberately deferred until after this core loop is proven.
- The internal intake form / `Tenant`+`Offer` creation UI, and the
  tenant-facing self-service panel. Separate objective.
- Real TCB credentials / `RealTcbClient` — keep building and testing
  against `MockTcbClient`.
- Billing/metering on clips.

## Quick self-check before calling this done

- [ ] `Offer.offer_token` field + migration exists, generated opaquely
      (not sequential/guessable).
- [ ] New routes do **not** live under `/o/` (collides with
      `oauth2_provider`).
- [ ] Landing page GET issues zero TCB calls.
- [ ] Clip POST calls `tcb_integration.services.issue_and_deposit_clip`
      (not a raw TCB client import).
- [ ] Clip POST is not wrapped in `transaction.atomic`.
- [ ] A test proves the same offer can't produce two `CouponClip`s with
      the same serial/pincode.
- [ ] `ClipEvent` rows get created for `link_opened` and `clip_confirmed`
      at minimum; ideally `barcode_viewed` and `wallet_saved` too.
- [ ] You've physically scanned a rendered barcode with a phone and
      confirmed it decodes correctly.
