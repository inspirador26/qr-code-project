## Autofill manufacturer fields for existing-account offer intake

**Branch:** feature/offer-autofill-fields
**Author:** Cory Rhodes

Select the account and manufacturer domain alphabetically, honoring dashboard
account preselection. Changing either selection updates the dependent fields;
Brand ID is read-only because each manufacturer link has one stored brand.
Reuse the saved link without changing its brand or verification metadata.

### Files touched
- `backend/internal/forms.py` — defaults, scoped choices, authoritative Brand ID.
- `backend/internal/views.py` — internal-only option data and selected link handoff.
- `backend/internal/services.py` — tenant-scoped link reuse.
- `backend/templates/internal/offer_intake.html` — dependent dropdowns and empty state.
- `backend/internal/tests.py` — defaults, tampering, empty accounts and link reuse.
- Backend dossier/decisions and frontend panel skill — behavior and constraints.

### Verified
`DATABASE_URL=sqlite:///:memory: ./venv/bin/python -B manage.py test --noinput`
passes all 45 tests with no system-check issues (baseline: 40). Tests cover
alphabetical and explicit defaults, domain changes, blank brands, invalid
POST selection preservation, missing/foreign links, malformed/empty accounts,
service-level tenant validation, and saved link metadata preservation.
The template's JavaScript passed Node DOM-stub checks for domain changes,
account changes, blank brands, no-link accounts, and returning to a valid account.

### Not done / known gaps
- No schema changes. Account onboarding retains free-text link creation.
- No last-used preference; defaults are alphabetical.
- JavaScript is required to refresh choices after changing accounts.
- Option data is loaded with the internal-only page; refresh to see newly added links.
- No live TCB verification.
- No visual browser walkthrough performed during implementation.
