from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import InternalOperator
from gs1.data_string import build_base_data_string
from offers.models import DistributionChannel, Offer, OfferChannelConfig, TcbManufacturerLink
from tcb_integration.mock_client import MockTcbClient
from tenancy.models import Tenant, TenantMembership


User = get_user_model()


class OfferAutofillTests(TestCase):
    def setUp(self):
        from .forms import OfferIntakeForm
        self.form_class = OfferIntakeForm
        self.zulu = Tenant.objects.create(name="Zulu")
        self.alpha = Tenant.objects.create(name="alpha")
        self.link = TcbManufacturerLink.objects.create(
            tenant=self.alpha, manufacturer_email_domain="a.example", brand_id="brand-a",
        )
        TcbManufacturerLink.objects.create(
            tenant=self.alpha, manufacturer_email_domain="z.example", brand_id="brand-z",
        )
        self.other = TcbManufacturerLink.objects.create(
            tenant=self.zulu, manufacturer_email_domain="other.example", brand_id="",
        )
        self.data = {
            "tenant": str(self.alpha.pk), "manufacturer_email_domain": "a.example",
            "offer_title": "Test", "coupon_funder_id": "123456", "offer_code": "000001",
            "total_circulation": 100, "max_clips": 50, "campaign_days": 30,
            "redemption_days": 60, "brand_id": "forged",
        }

    def test_alphabetical_defaults_and_explicit_account(self):
        form = self.form_class()
        self.assertEqual(str(form["tenant"].value()), str(self.alpha.pk))
        self.assertEqual(form["manufacturer_email_domain"].value(), "a.example")
        self.assertEqual(form["brand_id"].value(), "brand-a")
        form = self.form_class(initial={"tenant": str(self.zulu.pk)})
        self.assertEqual(form.fields["manufacturer_email_domain"].choices, [("other.example", "other.example")])
        self.assertEqual(form["brand_id"].value(), "")

    def test_post_uses_selected_link_and_preserves_selection_on_error(self):
        form = self.form_class({**self.data, "manufacturer_email_domain": "z.example"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["tcb_link"].brand_id, "brand-z")
        self.assertEqual(form.cleaned_data["brand_id"], "brand-z")
        form = self.form_class({**self.data, "manufacturer_email_domain": "z.example", "offer_title": ""})
        self.assertFalse(form.is_valid())
        self.assertEqual(form["manufacturer_email_domain"].value(), "z.example")
        self.assertEqual(form["brand_id"].value(), "brand-z")

    def test_foreign_or_deleted_domain_rejected(self):
        for domain in ("other.example", "deleted.example"):
            form = self.form_class({**self.data, "manufacturer_email_domain": domain})
            self.assertFalse(form.is_valid())
            self.assertIn("manufacturer_email_domain", form.errors)

    def test_empty_and_invalid_accounts(self):
        empty = Tenant.objects.create(name="Empty")
        for tenant_id in (str(empty.pk), "invalid", ""):
            form = self.form_class({**self.data, "tenant": tenant_id})
            self.assertFalse(form.is_valid())
            self.assertEqual(form.links, [])
        Tenant.objects.all().delete()
        self.assertEqual(self.form_class().links, [])

    def test_service_rejects_foreign_link_before_writing(self):
        from .services import create_offer_for_tenant
        with self.assertRaisesMessage(ValueError, "does not belong"):
            create_offer_for_tenant(tenant=self.alpha, data=self.data, tcb_link=self.other)
        self.assertFalse(Offer.objects.exists())


@override_settings(TCB_USE_MOCK=True, TCB_PLATFORM_EMAIL_DOMAIN="test-platform.example")
class InternalUiTests(TestCase):
    def setUp(self):
        MockTcbClient.reset()
        self.operator = User.objects.create_user(
            username="ops@example.com",
            email="ops@example.com",
            password="test-pass-123",
        )
        InternalOperator.objects.create(user=self.operator, role=InternalOperator.Role.OPS)

    def test_dashboard_requires_internal_operator(self):
        tenant = Tenant.objects.create(name="Acme CPG")
        user = User.objects.create_user(
            username="client@example.com",
            email="client@example.com",
            password="test-pass-123",
        )
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            invited_email=user.email,
            role=TenantMembership.Role.ADMIN,
            status=TenantMembership.Status.ACTIVE,
        )

        self.client.login(email=user.email, password="test-pass-123")
        response = self.client.get(reverse("internal:dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_account_intake_creates_tenant_offer_and_invite(self):
        self.client.login(email=self.operator.email, password="test-pass-123")

        response = self.client.post(
            reverse("internal:account_intake"),
            data={
                "tenant_name": "New Demo CPG",
                "tenant_legal_name": "New Demo CPG, Inc.",
                "billing_contact_email": "billing@new-demo.example",
                "manufacturer_email_domain": "new-demo.example",
                "brand_id": "brand-456",
                "offer_title": "Save $2 on Demo Salsa",
                "offer_description": "Internal intake test offer.",
                "coupon_funder_id": "123456789013",
                "offer_code": "000002",
                "total_circulation": 500,
                "max_clips": 250,
                "campaign_days": 30,
                "redemption_days": 60,
                "invite_email": "admin@new-demo.example",
                "invite_role": TenantMembership.Role.ADMIN,
            },
        )

        self.assertRedirects(response, reverse("internal:dashboard"))
        tenant = Tenant.objects.get(name="New Demo CPG")
        channel = DistributionChannel.objects.get(code="gs1_8112_barcode")
        offer = Offer.objects.get(tenant=tenant, offer_code="000002")

        self.assertEqual(offer.status, Offer.Status.LOCKED)
        self.assertEqual(offer.tcb_manufacturer_link.manufacturer_email_domain, "new-demo.example")
        self.assertTrue(OfferChannelConfig.objects.filter(offer=offer, channel=channel).exists())
        self.assertTrue(
            TenantMembership.objects.filter(
                tenant=tenant,
                invited_email="admin@new-demo.example",
                status=TenantMembership.Status.INVITED,
            ).exists()
        )

    def test_offer_intake_creates_offer_for_existing_tenant(self):
        tenant = Tenant.objects.create(
            name="Existing Demo CPG",
            legal_name="Existing Demo CPG, Inc.",
            billing_contact_email="billing@existing-demo.example",
        )
        link = TcbManufacturerLink.objects.create(
            tenant=tenant, manufacturer_email_domain="existing-demo.example",
            brand_id="saved-brand", connection_status="authorized", verified_at=timezone.now(),
        )
        verified_at = link.verified_at
        self.client.login(email=self.operator.email, password="test-pass-123")

        response = self.client.post(
            reverse("internal:offer_intake"),
            data={
                "tenant": str(tenant.id),
                "manufacturer_email_domain": "existing-demo.example",
                "brand_id": "brand-789",
                "offer_title": "Save $3 on Demo Chips",
                "offer_description": "Second offer for an existing account.",
                "coupon_funder_id": "123456789015",
                "offer_code": "000004",
                "total_circulation": 750,
                "max_clips": 500,
                "campaign_days": 30,
                "redemption_days": 60,
            },
        )

        self.assertRedirects(response, reverse("internal:dashboard"))
        channel = DistributionChannel.objects.get(code="gs1_8112_barcode")
        offer = Offer.objects.get(tenant=tenant, offer_code="000004")

        self.assertEqual(offer.status, Offer.Status.LOCKED)
        self.assertEqual(offer.title, "Save $3 on Demo Chips")
        self.assertEqual(offer.tcb_manufacturer_link_id, link.id)
        link.refresh_from_db()
        self.assertEqual(link.brand_id, "saved-brand")
        self.assertEqual(link.verified_at, verified_at)
        self.assertEqual(offer.tcb_manufacturer_link.manufacturer_email_domain, "existing-demo.example")
        self.assertTrue(OfferChannelConfig.objects.filter(offer=offer, channel=channel).exists())

    def test_offer_intake_is_not_available_to_tenant_user(self):
        tenant = Tenant.objects.create(name="Client CPG")
        user = User.objects.create_user(
            username="client2@example.com",
            email="client2@example.com",
            password="test-pass-123",
        )
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            invited_email=user.email,
            role=TenantMembership.Role.ADMIN,
            status=TenantMembership.Status.ACTIVE,
        )

        self.client.login(email=user.email, password="test-pass-123")
        response = self.client.get(reverse("internal:offer_intake"))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_lists_recent_offers(self):
        tenant = Tenant.objects.create(name="Existing CPG")
        link = TcbManufacturerLink.objects.create(
            tenant=tenant,
            manufacturer_email_domain="existing.example",
        )
        now = timezone.now()
        Offer.objects.create(
            tenant=tenant,
            tcb_manufacturer_link=link,
            ownership_mode=Offer.OwnershipMode.PARTNER_MANAGED,
            coupon_funder_id="123456789014",
            offer_code="000003",
            base_gs1=build_base_data_string("0", "123456789014", "000003"),
            title="Existing Offer",
            campaign_start_at=now,
            campaign_end_at=now + timedelta(days=30),
            redemption_start_at=now,
            redemption_end_at=now + timedelta(days=60),
            total_circulation=100,
            max_clips=100,
        )
        self.client.login(email=self.operator.email, password="test-pass-123")

        response = self.client.get(reverse("internal:dashboard"))

        self.assertContains(response, "Existing CPG")
        self.assertContains(response, "Existing Offer")
