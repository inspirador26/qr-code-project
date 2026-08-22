from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("internal/", include("internal.urls")),
    path("wallet/", include("wallet.urls")),
    path("api/v1/", include("api.urls")),
    path("", include("coupons.urls")),
]
