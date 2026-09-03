from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from gs1.data_string import build_base_data_string
from offers.models import Offer, TcbManufacturerLink
from tenancy.models import Tenant, TenantMembership


User = get_user_model()


class TenantDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="client@example.com",
            email="client@example.com",
            password="test-pass-123",
        )
        self.tenant = Tenant.objects.create(name="Visible CPG")
        self.other_tenant = Tenant.objects.create(name="Hidden CPG")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            invited_email=self.user.email,
            role=TenantMembership.Role.ADMIN,
            status=TenantMembership.Status.ACTIVE,
        )
        self.visible_offer = self._create_offer(self.tenant, "Visible Offer", "123456789015", "000004")
        self._create_offer(self.other_tenant, "Hidden Offer", "123456789016", "000005")

    def _create_offer(self, tenant, title, funder_id, offer_code):
        link = TcbManufacturerLink.objects.create(
            tenant=tenant,
            manufacturer_email_domain=f"{tenant.name.lower().replace(' ', '-')}.example",
        )
        now = timezone.now()
        return Offer.objects.create(
            tenant=tenant,
            tcb_manufacturer_link=link,
            ownership_mode=Offer.OwnershipMode.PARTNER_MANAGED,
            coupon_funder_id=funder_id,
            offer_code=offer_code,
            base_gs1=build_base_data_string("0", funder_id, offer_code),
            title=title,
            campaign_start_at=now,
            campaign_end_at=now + timedelta(days=30),
            redemption_start_at=now,
            redemption_end_at=now + timedelta(days=60),
            total_circulation=100,
            max_clips=100,
        )

    def test_dashboard_requires_membership(self):
        outsider = User.objects.create_user(
            username="outsider@example.com",
            email="outsider@example.com",
            password="test-pass-123",
        )
        self.client.login(email=outsider.email, password="test-pass-123")

        response = self.client.get(reverse("tenancy:dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_without_selected_tenant_redirects_to_selector(self):
        self.client.login(email=self.user.email, password="test-pass-123")

        response = self.client.get(reverse("tenancy:dashboard"))

        self.assertRedirects(response, reverse("tenancy:tenant_select"))

    def test_dashboard_shows_only_active_tenant_offers(self):
        self.client.login(email=self.user.email, password="test-pass-123")
        session = self.client.session
        session["active_tenant_id"] = str(self.tenant.id)
        session.save()

        response = self.client.get(reverse("tenancy:dashboard"))

        self.assertContains(response, "Visible Offer")
        self.assertNotContains(response, "Hidden Offer")
        self.assertEqual(self.client.session["active_tenant_id"], str(self.tenant.id))

    def test_user_can_switch_between_active_tenants(self):
        TenantMembership.objects.create(
            tenant=self.other_tenant,
            user=self.user,
            invited_email="client+other@example.com",
            role=TenantMembership.Role.VIEWER,
            status=TenantMembership.Status.ACTIVE,
        )
        self.client.login(email=self.user.email, password="test-pass-123")

        response = self.client.get(reverse("tenancy:dashboard"))
        self.assertRedirects(response, reverse("tenancy:tenant_select"))

        response = self.client.post(reverse("tenancy:select_tenant", args=[self.other_tenant.id]))

        self.assertRedirects(response, reverse("tenancy:dashboard"))
        self.assertEqual(self.client.session["active_tenant_id"], str(self.other_tenant.id))
