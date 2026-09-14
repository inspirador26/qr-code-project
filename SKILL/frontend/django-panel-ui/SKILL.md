---
name: django-panel-ui
description: Conventions for the Django template UI surfaces under backend/templates, including the tenant-facing app panel and internal ops screens.
---

# Django Panel UI

Use this when adding or changing Django-rendered UI in `backend/templates/`,
`backend/internal/`, or the tenant-facing `backend/tenancy/` panel.

## Current shape

The first UI slice is deliberately server-rendered Django templates on the
existing `base.html`, not a separate SPA. Tailwind, htmx, and Alpine are
loaded by CDN as a Phase 0 scaffold; do not add a frontend build system
until there is a concrete need.

Two surfaces must stay distinct:

- `/internal/` is for internal sales/ops work. It is gated by
  `accounts.InternalOperator` with Django superuser access allowed as a
  local bootstrap path. It creates/edits tenant-scoped rows directly.
- `/app/` is the CPG tenant-facing panel. It resolves the active tenant via
  `TenantMembership` and `TenantContextMiddleware`, and must never show data
  for a tenant the logged-in user is not an active member of.

## UI style

The internal dashboard links to `/internal/accounts/new/` for a new
account and initial offer, and `/internal/offers/new/` for an existing
account. Per-account Add Offer links preselect the tenant. Both intake
paths share the backend offer registration service.

Allauth login returns through `post_login_redirect`: internal users land
on `/internal/`, active tenant members on `/app/`. Keep that role-based
routing and the shared navigation gates when extending either panel.

Keep the product UI quiet and operational: dense tables, compact forms,
plain headings, restrained borders, and predictable navigation. Avoid
marketing-style hero layouts for app screens. Use server-side validation
errors and Django messages for feedback.

## Tenant isolation

Any tenant-facing view must filter tenant-scoped models by the selected
tenant. Internal views may query across tenants, but they must live under
`/internal/` and use the internal-operator gate.
