## Add stable public offer tokens with an existing-row migration

**Branch:** feature/add-public-offer-token
**Author:** coryrhodes

Implement consumer-offer-delivery A1: every new offer automatically receives
a random 10-character public identifier from an unambiguous alphabet using
Python's `secrets` module. Database uniqueness protects against collisions;
the identifier is excluded from model forms and persists through updates.
Existing offers receive individual tokens before uniqueness is enforced.

### Files touched
- `backend/offers/tokens.py` — secure token generator.
- `backend/offers/models.py` — unique, non-editable field with callable default.
- `backend/offers/migrations/0002_offer_public_token.py` — staged schema/data migration.
- `backend/offers/tests.py` — generation, persistence, uniqueness, form and migration tests.
- `SKILL/backend/consumer-offer-delivery/SKILL.md` — mark A1 implemented and document migration.
- `SKILL/backend/DOSSIER.md` — current state and remaining scope.
- `SKILL/backend/DECISIONS_AND_ISSUES.md` — existing-row migration rationale.

### Verified
- Baseline: `venv/bin/python manage.py test --noinput` — 40 tests passed on local PostgreSQL.
- After change: `venv/bin/python manage.py test --noinput` — 44 tests passed
  on local PostgreSQL, including migration of multiple existing offers.
- `venv/bin/python manage.py makemigrations --check --dry-run` — no changes detected.
- Django system checks reported no issues. Database tests required sandbox
  escalation to connect to local PostgreSQL.

### Not done / known gaps
- A2–A4 (active guard, consumer pages/domain routing, link builder) and Phase B remain planned.
- Automatic retry for a newly generated token collision is deferred as allowed by the design; the database rejects duplicates.
- Migration tested against the test database; the development database has not been migrated.
