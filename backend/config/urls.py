from django.contrib import admin
from django.urls import include, path

from . import admin as admin_descriptions  # noqa: F401 — applies the admin app-list description patch on import
from accounts.views import post_login_redirect

urlpatterns = [
    path("admin/", admin.site.urls),
    # Must be registered before allauth.urls so LOGIN_REDIRECT_URL (which
    # points here by name) resolves — this is the shared post-login router:
    # same login page for everyone, role-based redirect after.
    path("post-login/", post_login_redirect, name="post_login_redirect"),
    path("accounts/", include("allauth.urls")),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
    path("internal/", include("internal.urls")),
    path("app/", include("tenancy.urls")),
    path("wallet/", include("wallet.urls")),
    path("api/v1/", include("api.urls")),
    path("", include("coupons.urls")),
]
