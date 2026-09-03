---
name: tenancy-and-auth
description: How multi-tenant isolation and SSO auth work in the Django backend -- Tenant/TenantMembership, TenantContextMiddleware, the invite-only django-allauth adapter, and InternalOperator. Load this when adding a model that needs tenant scoping, touching auth/SSO/invites, or working on anything where "which tenant can see this" matters.
---

# Tenancy & Auth

Living architecture doc for the Django backend's multi-tenancy and auth
model. Node-only concepts (JWT scan tokens, `server.js`) don't apply here —
see `qr-coupon-flow` for that legacy context if needed.

## Why this exists / how strict it is

The client stated, with real emphasis, that **no CPG client may ever see
another client's data or have offers pushed to the wrong TCB account.**
This isn't a soft preference — treat any change that could blur tenant
boundaries as a correctness bug, not a style nit.

## The isolation mechanism

Every tenant-scoped model (`Offer`, `CouponClip`, `TcbSyncLog`, `ClipEvent`,
etc.) carries a **denormalized `tenant` FK directly**, not just reachable
via a join — this is deliberate, so `.filter(tenant=...)` is always a single
flat clause, and so Postgres Row-Level Security (planned, not yet
implemented) can key off it later without schema changes.

`tenancy/middleware.py`'s `TenantContextMiddleware` resolves
`request.tenant` from `request.session["active_tenant_id"]` — **explicit
selection only, never inferred.** A user with memberships in multiple
tenants must have chosen one via a tenant-switch view (not yet built — see
TODO) before `request.tenant` is set. Any stale/invalid session tenant_id
(e.g. a revoked membership) is cleared rather than trusted.

**Rule for new code**: any view or service function touching a tenant-scoped
model should take `tenant` as an explicit, mandatory argument — never query
a tenant-scoped model without a tenant filter, even "just for now."

## Auth flow

`accounts` app: custom `User` (email as `USERNAME_FIELD`, via a custom
`_EmailUserManager` — plain `AbstractUser`'s manager assumes username-based
auth and breaks `createsuperuser` otherwise), `UserIdentity` (links a `User`
to one SSO login, unique on `(provider, provider_subject)`),
`InternalOperator` (our own ops staff — see below).

**Invite-only, not self-service signup** — confirmed explicitly with the
client (2026-08-22): anyone can *authenticate* via Google/Microsoft once
real OAuth credentials exist, but only an *invited* email actually gets
tenant access. Mechanism: `tenancy.TenantMembership` rows start as
`status="invited"` with an `invited_email` (no `user` yet).
`accounts/adapters.py`'s `InviteOnlySocialAccountAdapter`
(`SOCIALACCOUNT_ADAPTER` in settings) gates `is_open_for_signup()` on a
matching pending invite, and on `save_user()` promotes any matching
`TenantMembership` rows to `status="active"` and links the new `User`.

`InternalOperator` is deliberately **separate** from `TenantMembership` —
not a pseudo-tenant — so our own ops/support access is structurally
distinct and auditable, never confusable with a client role. Resolve
internal access through it, in an architecturally separate `/internal/`
namespace, never through the tenant-membership path.

## Known problems & solutions

- **`AbstractUser` + `USERNAME_FIELD = "email"` needs a custom manager.**
  Django's default `UserManager.create_superuser` calls `create_user`
  assuming a username-first signature; without `_EmailUserManager`
  overriding `_create_user`, `createsuperuser` breaks. Already fixed in
  `accounts/models.py` — don't remove it if refactoring the User model.
- **No real OAuth credentials yet.** `django-allauth` and the adapter are
  fully wired at the settings/code level, but there are no `SocialApp`
  records (client ID/secret) for Google or Microsoft — Justin needs to
  provision these from each provider's console (steps were given directly
  in chat, not committed anywhere yet — worth writing down properly if this
  keeps coming up).

## TODO

- No tenant-switch view exists — a user in >1 tenant currently has no UI
  path to pick which one they're acting as.
- Postgres Row-Level Security as defense-in-depth (independent of the
  service-layer guarantees above) — planned, not started.
- Real Google/Microsoft `SocialApp` credentials.
- Programmatic API auth (`api.ApiClient` wraps a `django-oauth-toolkit`
  `Application`) has models but no real client-credentials token endpoint
  wired up yet.
