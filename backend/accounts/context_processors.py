from .models import InternalOperator


def role_flags(request):
    """Exposes role flags to every template so shared UI (nav, etc.) can
    show/hide links by role, instead of showing every authenticated user
    every link regardless of whether they're allowed through it.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"is_internal_operator": False, "has_tenant_access": False}

    return {
        "is_internal_operator": user.is_superuser
        or InternalOperator.objects.filter(user=user).exists(),
        "has_tenant_access": user.tenant_memberships.filter(status="active").exists(),
    }
