## Add internal offer intake for existing tenant accounts

**Branch:** feature/new-offer
**Author:** Cory Rhodes

Internal operators can add an offer to an existing tenant without repeating
account creation or using Django admin. The dashboard provides New Offer
and per-account Add Offer links. Both intake paths use the same service to
create the manufacturer link, barcode channel, offer, and channel config,
then register and lock the offer through TCB.

Rebased against staging's role-based login work: preserve its post-login
router, logout destination, navigation gates, and Redis configuration. Keep
the feature's `/login/` and `/logout/` aliases to allauth. Move the feature
history out of CHANGELOG.md into this fragment under the new docs policy.

### Files touched
- `backend/internal/{forms,services,views,urls,tests}.py` and
  `backend/templates/internal/` - existing-account offer intake and access tests.
- `backend/config/settings/base.py`, `backend/config/urls.py`, and
  `backend/accounts/tests.py` - combined login routing and regression tests.
- `backend/README.md`, backend dossier/decisions, frontend panel skill,
  and product workflow skill - behavior, limitations, and rebase decisions.

### Verified
`cd backend && ./venv/bin/python -B manage.py test --noinput` passed all
40 tests against local Postgres, with no Django system-check issues. Includes
existing-account offer creation/access restrictions and role-based routing
for superusers, internal operators, tenant members, and anonymous users.

### Not done / known gaps
- Intake currently creates partner-managed digital GS1 8112 offers with
  fixed expiration; additional offer types are not exposed by the form.
- Tests use mock TCB; no live TCB account verification or browser walkthrough.
- Failed TCB registration can leave local intake rows behind; it remains
  outside an atomic wrapper to preserve failure logs.
- The rebase must still be continued and the branch merged into staging.
