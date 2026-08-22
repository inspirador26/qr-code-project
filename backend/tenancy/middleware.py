from .models import Tenant, TenantMembership

SESSION_KEY = "active_tenant_id"


class TenantContextMiddleware:
    """Resolves the acting tenant for the request and attaches it as
    `request.tenant`. Deliberately explicit, not inferred: an authenticated
    user with memberships in more than one tenant must have selected one via
    the tenant-switch view (tenancy/views.py) before `request.tenant` is set.
    No view outside `/internal/` should query tenant-scoped models without
    checking `request.tenant` first — see the plan's "Tenant isolation
    guarantee" section.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None

        if request.user.is_authenticated:
            tenant_id = request.session.get(SESSION_KEY)
            if tenant_id:
                membership = (
                    TenantMembership.objects.filter(
                        tenant_id=tenant_id,
                        user=request.user,
                        status=TenantMembership.Status.ACTIVE,
                    )
                    .select_related("tenant")
                    .first()
                )
                if membership:
                    request.tenant = membership.tenant
                else:
                    # Stale/invalid selection (e.g. membership revoked since
                    # the session was set) — clear it rather than trust it.
                    del request.session[SESSION_KEY]

        return self.get_response(request)


def set_active_tenant(request, tenant: Tenant) -> None:
    """Explicit tenant selection — call only from a view where the user has
    just chosen which tenant to act as (e.g. after login, or a tenant
    switcher). Never call this implicitly.
    """
    request.session[SESSION_KEY] = str(tenant.id)
