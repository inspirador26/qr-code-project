# changelog.d — one file per branch

This folder is the anti-merge-conflict mechanism for `CHANGELOG.md`: two
people never edit the same file mid-branch. See `DOCUMENTATION_POLICY.md`
for the full system this is part of.

## Workflow

1. Working on a branch that changes anything worth recording? Create
   `changelog.d/<branch-name-with-slashes-replaced-by-dashes>.md` using the
   format below, and update it as the branch evolves.
2. When the branch merges, fold its fragment into `CHANGELOG.md` (top of
   file, matching the existing entry format there — date, author, what/why/
   gotchas) and delete the fragment.
3. An empty `changelog.d/` (aside from this README) is the healthy,
   expected state — it means nothing is silently sitting on a branch
   waiting to be documented.

## Format

```
## <headline: what changed, in a sentence>

**Branch:** <branch-name>
**Author:** <username>

<why, in a paragraph or two>

### Files touched
- `path` — what changed in it

### Verified
<what you actually ran or clicked, and what it returned>

### Not done / known gaps
- <the most useful section at review time — say what you didn't do rather
  than leaving it to be discovered>
```

## Worked example

```
## Fix Redis port collision, add role-based post-login redirect + nav gating

**Branch:** feature/role-based-login-and-nav
**Author:** justin (with Claude)

Local dev testing surfaced that every logged-in user landed on the bare
health-check root regardless of role, and the shared nav showed
Internal/Admin links to normal tenant users with no logout button at all.

### Files touched
- `backend/accounts/views.py` — new `post_login_redirect`: routes
  superusers/InternalOperators to `/internal/`, active tenant members to
  `/app/`, everyone else falls back to `/`.
- `backend/accounts/context_processors.py` — new `role_flags` context
  processor (`is_internal_operator`, `has_tenant_access`) so templates can
  gate links by role.
- `backend/config/urls.py`, `backend/config/settings/base.py` — wired the
  new view in as `LOGIN_REDIRECT_URL`; added
  `ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"`.
- `backend/templates/base.html` — hid Internal/Admin nav links from
  non-internal users, added a working logout button (POST to allauth's
  `account_logout`).
- `backend/docker-compose.yml`, `backend/.env.example` — remapped Redis to
  host port 6380; 6379 collided with an unrelated project's container on
  this machine.

### Verified
`python manage.py test` — 32/32 passing. Manually logged in as a seeded
demo tenant user end to end: login by code -> role-based redirect to
`/app/` -> logout -> back to login page.

### Not done / known gaps
- No dedicated "no access yet" landing page for a logged-in user with no
  role — falls back to the bare health-check root.
- `TenantMembership.invited_email` has a uniqueness constraint that
  doesn't exclude blank values, so two memberships on the same tenant can't
  both leave it empty (hit this seeding test users) — worth a real fix.
```
