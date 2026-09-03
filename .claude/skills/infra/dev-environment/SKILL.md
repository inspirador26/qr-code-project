---
name: dev-environment
description: How local dev, branching, and GCP/Wallet credentials are set up and operated for the QR coupon app -- both the active Django backend and the legacy Node POC. Load this when starting either server locally, testing on a phone/LAN, rotating the Google Wallet key, or deciding which branch to work on.
---

# Dev Environment

This is a living operational doc — update it whenever we hit a new gotcha or
change how something is set up. `CHANGELOG.md` is the historical session log;
this skill is the current-state summary distilled from it.

**As of 2026-08-22, active development is the Django backend at `backend/`
(see below).** The Node instructions further down describe `server.js` at
the repo root, kept only as a behavioral reference — don't assume it's what
"the server" means without checking which one a task actually needs.

## Branching model

- `main` — stable. Only staging merges here, when we're happy with it.
- `staging` — integration branch. Feature branches merge here first.
- `feature/*` — one branch per unit of work, cut from `staging`, merged back
  into `staging` (not `main`) when done. As of 2026-08-22, both `staging`
  and `feature/django-backend-foundation` exist on `origin` (GitHub) —
  earlier branches were local-only and have been cleaned up after merging.

## Booting the Django backend locally

Requires Python 3.13+ and Docker Desktop. Full detail in `backend/README.md`
— summary:

```bash
cd backend
python -m venv venv && source venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
docker compose up -d          # Postgres + Redis
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then `http://127.0.0.1:8000/` (health check) and `/admin/` (full admin, all
models registered, each with a short description on the index page — see
`config/admin.py`'s `MODEL_DESCRIPTIONS` dict to add/update one; it patches
`admin.site.get_app_list` since Django admin has no built-in per-model
description). `python manage.py test` should show all tests passing (23 as
of 2026-08-22).

**Gotcha: Postgres port 5432 may already be taken by a native (non-Docker)
Postgres install.** Hit this exact issue on 2026-08-22 — the container was
silently losing the port conflict, and Django was authenticating against the
wrong Postgres instance entirely (confusing "password authentication
failed" errors that had nothing to do with the actual password). Fixed by
mapping the container to host port **5433** in `docker-compose.yml` — this
is already done, don't "fix" it back to `5432:5432` without checking
`netstat -ano | grep :5432` (or `Get-NetTCPConnection -LocalPort 5432` in
PowerShell) first.

No real credentials are needed to get a working local instance — TCB
defaults to a mock implementation (`settings.TCB_USE_MOCK = True`, see the
`tcb-integration` skill) and Google Wallet fails gracefully with a clear
503 if unconfigured rather than crashing. Real credentials (Google/Microsoft
OAuth, TCB `access_key`/`secret_key`, the wallet service account file) all
go in `backend/.env` (copy from `.env.example`) — see `tenancy-and-auth` and
`tcb-integration` skills for what each actually gates.

## Booting the legacy Node server locally

Requirements before `node server.js` will even start:

- `npm install`, then **always** `npm rebuild better-sqlite3` on a fresh
  clone/machine — the committed `node_modules` binary is platform-specific and
  will fail with "not a valid Win32 application" on a mismatched OS.
- `keys/wallet-sa.json` must exist (gitignored, never committed). It's the
  Google Wallet Issuer service-account key. The server hard-requires it at
  boot.

### Env vars

| Var | Default | Notes |
|---|---|---|
| `PORT` | `3000` | |
| `LISTEN_HOST` | `127.0.0.1` | Must be `0.0.0.0` to accept LAN connections (e.g. phone testing) |
| `HOST` | `http://localhost:$PORT` | Gets baked into every QR code and wallet save link — must match the machine's actual current LAN IP for a phone to reach it |
| `JWT_SECRET` | dev default | |

**PowerShell gotcha:** `set VAR=value` in PowerShell is aliased to
`Set-Variable` and does **not** create an environment variable — the server
silently falls back to defaults. Use `$env:VAR="value"` in PowerShell, or
`set VAR=value` only in `cmd.exe`.

### Testing from a phone on the LAN

1. Re-check the current LAN IP every session — it changes on DHCP lease
   renewal, which has bitten us more than once mid-session.
2. Start with `LISTEN_HOST=0.0.0.0` and `HOST` set to that IP.
3. Windows Firewall needs an inbound allow rule for the port (requires an
   elevated shell to create).
4. The network connection profile must be **Private**, not Public — Windows
   blocks inbound connections on Public profiles regardless of firewall
   rules. Home networks sometimes default to Public after a cable/adapter
   change; check with `Get-NetConnectionProfile`.

## Google Wallet / GCP

Shared between both servers — the Node POC reads `keys/wallet-sa.json`
directly; the Django backend reads the same key via
`GOOGLE_WALLET_SERVICE_ACCOUNT_FILE` in `backend/.env` (defaults to
`keys/wallet-sa.json`, i.e. the same file, no need to duplicate it).

- Project: `wallet-qr-project`
- Service account: `wallet-service@wallet-qr-project.iam.gserviceaccount.com`
- Issuer ID: `3388000000023034731` (tied to the Wallet Business Console
  account, not to any specific key)
- Justin's collaborator owns the GCP project and mints keys himself when
  rotation is needed — key material should never be pasted through chat.
  Rotate with:
  ```
  gcloud iam service-accounts keys create keys/wallet-sa.json \
    --iam-account=wallet-service@wallet-qr-project.iam.gserviceaccount.com
  gcloud iam service-accounts keys delete OLD_KEY_ID \
    --iam-account=wallet-service@wallet-qr-project.iam.gserviceaccount.com
  ```
- The `[TEST ONLY]` banner on saved passes is controlled by the **Issuer
  account's** publish/review status in the Wallet Business Console — it is
  independent of each `OfferClass`'s `reviewStatus` field.

## TODO

- Justin's own IAM grant on the project is currently the broad `roles/editor`
  (came through that way from the collaborator) — narrow it to
  `roles/iam.serviceAccountKeyAdmin` scoped to just the wallet service account
  once convenient.
- Consider auto-detecting the LAN IP at server boot instead of requiring it in
  `HOST` manually.

## Known problems & solutions

See above sections — each gotcha is paired with its fix inline. Add new ones
here as they come up rather than only in `CHANGELOG.md`, so this stays the
single current-state reference.
