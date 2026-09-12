from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import InternalOperator


def _is_internal_operator(user) -> bool:
    return user.is_superuser or InternalOperator.objects.filter(user=user).exists()


@login_required
def post_login_redirect(request):
    """Single shared login page for everyone (allauth's /accounts/login/);
    this is where we route people differently *after* that, based on role,
    instead of everyone landing on the same LOGIN_REDIRECT_URL.

    - Internal operators / superusers -> the internal ops dashboard.
    - Tenant members -> the tenant-facing app (handles its own tenant-select
      step if the user belongs to more than one, or none selected yet).
    - Anyone else (e.g. invited but not yet an active member of any tenant)
      -> falls back to the health-check root rather than a 403, since a
      logged-in user with no role yet isn't an error, just a dead end for
      now — there's no dedicated "no access" page yet.
    """
    user = request.user

    if _is_internal_operator(user):
        return redirect("internal:dashboard")

    if user.tenant_memberships.filter(status="active").exists():
        return redirect("tenancy:dashboard")

    return redirect("/")
