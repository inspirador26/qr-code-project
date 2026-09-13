## Add tenant-safe offer detail and editing pages

**Branch:** codex/offer-detail-edit
**Author:** Cory Rhodes

Existing-account New Offer intake is already present in staging. This branch
extends its internal and tenant dashboards with offer detail and editing.
This fragment replaces the stale feature/new-offer fragment that mixed the
existing intake implementation with the pending detail/edit work.

Offer titles in the internal and tenant dashboards now link to full detail
pages. The pages expose the offer configuration, schedule, identifiers,
usage, distribution channels, TCB connection, MOF snapshot, and recent sync
status while preserving tenant isolation. Internal operators and tenant
Admin/Editor users can edit partner-managed offers; tenant Viewers and all
users viewing client-managed offers are read-only. Locked TCB-controlled
fields are disabled server-side, leaving only local title and distribution
cap edits until a verified MOF update path exists.

The branch starts from staging commit 91e53fb (Docs cleanup + consumer offer
delivery design, #1), fetched September 13. Pending changes were restored
without conflicts; the backend dossier retains the new masked-domain and
active-offer-guard plans alongside the detail/edit documentation. Existing
login routing and runtime configuration remain in place. The consumer
delivery design remains future work.

Restore digital-only intake after an unintended coupon-format selector was
added to both account and existing-account intake. The shared service fixes
the format to digital, so omitted fields and crafted paper-format requests
produce a consistent digital offer and GS1 identity. Keep the stored format
visible on offer detail pages; paper intake remains deferred.

### Files touched
- `backend/internal/{forms,views,urls,tests}.py` and
  `backend/templates/internal/` - detail/edit routes, dashboard links,
  digital-only intake regressions, and form layout.
- `backend/tenancy/{views,urls,tests}.py`, dashboard templates, and
  `backend/templates/offers/` - tenant-safe offer detail/edit pages, role
  checks, dashboard links, and locked-field protections.
- Backend dossier, frontend decisions and panel skill - behavior and limitations.

### Verified
`DATABASE_URL=sqlite:///:memory: ./venv/bin/python -B manage.py test --noinput`
passed all 46 tests on September 13 after restoring the work onto 91e53fb,
with no Django system-check issues. Includes offer-detail
tenant isolation, Viewer read-only access, locked-field tampering protection,
existing-account offer creation/access restrictions, and role-based routing.
Intake regressions cover omission of the selector from both pages, account
creation without a format field, and a crafted paper-format POST producing
a digital offer with the matching base GS1 string.

### Not done / known gaps
- Intake currently creates partner-managed digital GS1 8112 offers with
  fixed expiration; additional offer types are not exposed by the form.
- Tests use mock TCB; no live TCB account verification or browser walkthrough.
- Failed TCB registration can leave local intake rows behind; it remains
  outside an atomic wrapper to preserve failure logs.
- Editing TCB-controlled fields on locked offers remains unavailable until
  the real MOF update behavior is verified and implemented.
- Changes are not yet committed or merged. The retained stash is a backup
  of the pre-integration work; future staging changes require a fresh check.
