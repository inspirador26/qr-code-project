from django.contrib import admin
from django.urls import include, path

from . import admin as admin_descriptions  # noqa: F401 — applies the admin app-list description patch on import

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("internal/", include("internal.urls")),
    path("app/", include("tenancy.urls")),
    path("wallet/", include("wallet.urls")),
    path("api/v1/", include("api.urls")),
    path("", include("coupons.urls")),
]
