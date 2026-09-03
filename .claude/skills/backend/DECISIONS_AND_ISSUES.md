# Backend — segment-level decisions & known issues

Policy decisions and known issues that apply across more than one backend
skill doc (`backend/tcb-integration`, `backend/tenancy-and-auth`,
`backend/google-wallet`), rather than to just one. See
`.claude/skills/skills-organization/SKILL.md` for what belongs here vs. on
an individual skill doc. Newest on top.

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
