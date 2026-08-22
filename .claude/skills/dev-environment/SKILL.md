---
name: dev-environment
description: How local dev, branching, and GCP/Wallet credentials are set up and operated for the QR coupon app. Load this when starting the server locally, testing on a phone/LAN, rotating the Google Wallet key, or deciding which branch to work on.
---

# Dev Environment

This is a living operational doc — update it whenever we hit a new gotcha or
change how something is set up. `CHANGELOG.md` is the historical session log;
this skill is the current-state summary distilled from it.

## Branching model

- `main` — stable. Only staging merges here, when we're happy with it.
- `staging` — integration branch. Feature branches merge here first.
- `feature/*` — one branch per unit of work, cut from `staging`, merged back
  into `staging` (not `main`) when done.

## Booting the server locally

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
