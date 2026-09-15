# Coupon Platform — Backend

Django backend for a multi-tenant service that distributes **GS1 AI(8112)
digital coupon barcodes** on behalf of CPG (consumer packaged goods)
manufacturer clients, via The Coupon Bureau (TCB), and reports offer
performance back to them.

This supersedes the Node/Express proof-of-concept at the repo root
(`server.js`), which is kept only as a behavioral reference during the
rewrite (QR generation logic, the Google Wallet JWT construction) — not
something being incrementally migrated. See
`SKILL/legacy/qr-coupon-flow/SKILL.md` for that reference, and
`SKILL/backend/DOSSIER.md` for this backend's current state (the
front door — read that first, not this file, for "what's built"). Why the
rewrite happened at all (and why Django specifically) is recorded in
`../CHANGELOG.md`'s `2026-08-22 ... part 3` entry — grep it rather than
re-deriving the reasoning from scratch.

## Quick start

Requires: Python 3.13+, Docker Desktop.

```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash; venv\Scripts\activate.bat on cmd
pip install -r requirements.txt

docker compose up -d                # Postgres (host port 5433, not 5432 — see note below) + Redis
python manage.py migrate
python manage.py createsuperuser    # for /admin/ login
python manage.py runserver
```

Then:
- `http://127.0.0.1:8000/` — health check (no consumer-facing pages exist
  yet — see `SKILL/backend/DOSSIER.md` §5–§7 for what's built)
- `http://127.0.0.1:8000/admin/` — full Django admin, all models registered,
  each with a short description of what it's for right on the index page
  (see `config/admin.py` if you need to add/update one — it's a lookup dict,
  not per-model boilerplate)
- `http://127.0.0.1:8000/internal/` — internal ops dashboard, account
  intake form, and offer intake form for existing accounts, gated by
  `InternalOperator` or Django superuser bootstrap access.
- `http://127.0.0.1:8000/app/` — tenant-facing dashboard for active
  `TenantMembership` users, with explicit tenant selection.

**Postgres port note**: `docker-compose.yml` maps the container to host port
**5433**, not the default 5432. This is deliberate — if your machine already
runs a native Postgres service on 5432 (common if you've installed Postgres
directly before), mapping there would silently connect Django to the wrong
database instead of this container. If your machine has no conflicting
Postgres, you can change this back to `5432:5432`, but there's no need to.

Copy `.env.example` to `.env` and fill in real values as they become
available (OAuth credentials, TCB credentials, Google Wallet service
account path) — everything has a safe default for local dev in the
meantime, and `TCB_USE_MOCK=True` means the whole TCB integration works
without any real TCB credentials at all (see
`SKILL/backend/tcb-integration/SKILL.md`).

## Running tests

```bash
python manage.py test
```

40 tests as of this writing, all passing — covers the GS1 data-string
encoder/parser, barcode rendering, the Google Wallet JWT signing, and the
full TCB register→lock→deposit→redeem flow against the mock client, plus
the first internal/tenant-facing UI access and tenant-isolation checks.

## Demo data

For the MVP clip demo, seed a known-good tenant/offer/channel setup with:

```bash
python manage.py seed_demo_offer
```

The command creates or updates a demo `Tenant`, `TcbManufacturerLink`,
`DistributionChannel` (`code="gs1_8112_barcode"`), `Offer`, and
`OfferChannelConfig`, then calls `register_and_lock_offer(offer)` so the
mock TCB client will accept clip deposits for that offer in the current
process. It prints the seeded offer UUID and planned `/offer/<uuid>/` URL.
The local offer remains LOCKED after seeding. Set it ACTIVE explicitly
(for example in Django admin) before clipping; A2 now rejects inactive,
out-of-campaign, or clip-limit-exhausted offers before any TCB deposit.

## Architecture, tenant isolation, the TCB integration seam, current status

These live in `SKILL/backend/`, not here, so there's exactly one
place to keep them current:
- **`DOSSIER.md`** — the apps table, tenant-isolation policy, and the
  authoritative "what's built / what's not" (§3, §2, §5–§7).
- **`tcb-integration/SKILL.md`** — the client seam (mock vs. real),
  `services.py`, the non-atomic-by-design rule, and the current milestone
  (consumer clip landing page — not yet built).
- **`consumer-offer-delivery/SKILL.md`** — the design for masking that
  landing page's URL and the offer-active guard, once that milestone
  starts.
