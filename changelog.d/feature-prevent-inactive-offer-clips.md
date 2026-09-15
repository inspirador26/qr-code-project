## Prevent ineligible offers from issuing clips

**Branch:** feature/prevent-inactive-offer-clips
**Author:** coryrhodes

Implement consumer-offer-delivery A2. Clip issuance checks ACTIVE status,
inclusive campaign dates and the non-VOID clip count before initializing
TCB or creating rows. Typed exceptions provide consumer-friendly messages.
Registration still leaves offers LOCKED; activation remains explicit.

### Files touched
- `backend/offers/exceptions.py` — eligibility exception hierarchy and messages.
- `backend/offers/services.py` — central status/window/cap guard.
- `backend/tcb_integration/services.py` — guard at the start of issuance.
- `backend/tcb_integration/tests.py` — eligibility and side-effect tests;
  explicitly activate fixtures for TCB failure tests and preserve external-cap coverage.
- `backend/offers/tests.py` — explicitly activate the seeded offer before clipping.
- `backend/README.md` — document activation after seeding.
- `SKILL/backend/consumer-offer-delivery/SKILL.md` — A2 behavior and remaining scope.
- `SKILL/backend/tcb-integration/SKILL.md` — new issuance contract and demo prerequisite.
- `SKILL/backend/DOSSIER.md` — current state, limits, and remaining work.
- `SKILL/backend/DECISIONS_AND_ISSUES.md` — service-boundary and activation rationale.

### Verified
- Baseline `venv/bin/python manage.py test --noinput`: 40 tests passed on PostgreSQL.
- Final `venv/bin/python manage.py test --noinput`: 47 tests passed on
  PostgreSQL, with no system-check issues.
- `venv/bin/python manage.py makemigrations --check --dry-run`: no changes detected.

### Not done / known gaps
- A1 token work is not present on this branch; A2 is independent of it.
- A3 consumer pages/error rendering, A4 link builder and Phase B remain future work.
- No schema change or migration needed; development data was not modified.
- Concurrent eligibility checks are not locked, per the plan. Callers supply
  a current Offer; TCB's circulation cap remains the external backstop.
- No automatic activation; LOCKED demo offers must be explicitly made ACTIVE.
