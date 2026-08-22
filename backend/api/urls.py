from django.http import JsonResponse
from django.urls import path

app_name = "api"


def placeholder(request):
    """CPG programmatic API (/api/v1/reports/*, /api/v1/offers/*) lands in
    Phase 3 — see the plan's phase sequence."""
    return JsonResponse({"status": "not_implemented"}, status=501)


urlpatterns = [
    path("", placeholder, name="placeholder"),
]
