## Shorten the default 2-week Django session lifetime

**Branch:** fix/session-lifetime
**Author:** Claude (with Justin)

While testing the colleague's new `/internal/offers/new/` form, Justin
asked why he could reach it without logging in. The view is correctly
gated (`internal_operator_required` wraps `login_required`), but Django's
default session lasts 2 weeks with no idle timeout — a superuser session
from earlier testing was still valid, silently. Justin asked to fix the
session lifetime itself, not just verify the gate.

### Files touched

- `backend/config/settings/base.py` — `SESSION_COOKIE_AGE = 60 * 60 * 8`
  (8-hour idle timeout), `SESSION_SAVE_EVERY_REQUEST = True` (sliding, so
  active use doesn't get interrupted), `SESSION_EXPIRE_AT_BROWSER_CLOSE =
  True`. Applies to both `/internal/` and `/app/` — one shared Django
  session mechanism, not per-namespace.
- `SKILL/backend/tenancy-and-auth/SKILL.md` — documented the trap (a
  view can look unprotected when it's really just an already-authenticated
  browser) and the fix, under "Known problems & solutions."

### Verified

`python manage.py test` — 40/40 passing, no regressions from the settings
change.

### Not done / known gaps

- 8 hours / sliding-idle was picked as a reasonable default for an
  internal ops + tenant dashboard product; not something Justin or the
  client explicitly specified a number for. Revisit if it turns out to be
  too aggressive or too lax in practice.
