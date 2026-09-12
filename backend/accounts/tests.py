from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import InternalOperator
from tenancy.models import Tenant, TenantMembership


class AuthRoutingTests(SimpleTestCase):
    def test_default_login_urls_target_allauth(self):
        self.assertEqual(settings.LOGIN_URL, "/accounts/login/")
        self.assertEqual(settings.LOGIN_REDIRECT_URL, "post_login_redirect")
        self.assertEqual(settings.ACCOUNT_LOGOUT_REDIRECT_URL, "account_login")

    def test_short_login_alias_exists(self):
        response = self.client.get("/login/")

        self.assertEqual(reverse("account_login"), "/accounts/login/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/login/")


class PostLoginRoutingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="routing@example.com", email="routing@example.com"
        )
        self.client.force_login(self.user)

    def test_superuser_lands_on_internal_dashboard(self):
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        self.assertRedirects(
            self.client.get(reverse("post_login_redirect")),
            reverse("internal:dashboard"),
        )

    def test_internal_operator_lands_on_internal_dashboard(self):
        InternalOperator.objects.create(user=self.user, role=InternalOperator.Role.OPS)
        self.assertRedirects(
            self.client.get(reverse("post_login_redirect")),
            reverse("internal:dashboard"),
        )

    def test_active_tenant_member_lands_on_tenant_panel(self):
        TenantMembership.objects.create(
            tenant=Tenant.objects.create(name="Routing Test"),
            user=self.user,
            invited_email=self.user.email,
            role=TenantMembership.Role.VIEWER,
            status=TenantMembership.Status.ACTIVE,
        )
        self.assertRedirects(
            self.client.get(reverse("post_login_redirect")),
            reverse("tenancy:dashboard"),
            fetch_redirect_response=False,
        )

    def test_anonymous_user_is_sent_to_allauth(self):
        self.client.logout()
        self.assertRedirects(
            self.client.get(reverse("post_login_redirect")),
            reverse("account_login") + "?next=/post-login/",
        )
