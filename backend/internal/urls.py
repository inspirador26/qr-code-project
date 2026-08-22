from django.http import JsonResponse
from django.urls import path

app_name = "internal"


def placeholder(request):
    """Ops-only surface, gated by accounts.InternalOperator — not
    tenancy.TenantMembership. Architecturally separate from tenant-facing
    routes so there's no session-scope bleed; see the plan's Auth
    architecture section."""
    return JsonResponse({"status": "not_implemented"}, status=501)


urlpatterns = [
    path("", placeholder, name="placeholder"),
]
