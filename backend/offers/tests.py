from io import StringIO
from datetime import timedelta

from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.forms import modelform_factory
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from coupons.models import CouponClip
from gs1.data_string import build_base_data_string
from offers.models import (
    DistributionChannel,
    Offer,
    OfferChannelConfig,
    TcbManufacturerLink,
)
from tcb_integration.mock_client import MockTcbClient
from tcb_integration.models import TcbSyncLog
from tcb_integration.services import issue_and_deposit_clip
from tenancy.models import Tenant


def offer_fields(tenant, link, code):
    now = timezone.now()
    return dict(
        tenant=tenant, tcb_manufacturer_link=link,
        ownership_mode="partner_managed", coupon_funder_id="123456789012",
        offer_code=code, base_gs1=f"test-{code}", title=f"Offer {code}",
        campaign_start_at=now, campaign_end_at=now + timedelta(days=1),
        redemption_start_at=now, redemption_end_at=now + timedelta(days=2),
        total_circulation=100, max_clips=100,
    )


class OfferPublicTokenTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Token test")
        self.link = TcbManufacturerLink.objects.create(
            tenant=self.tenant, manufacturer_email_domain="tokens.example",
        )

    def create_offer(self, code, **extra):
        return Offer.objects.create(**offer_fields(self.tenant, self.link, code), **extra)

    def test_tokens_generated_per_offer_and_survive_updates(self):
        first = self.create_offer("000001")
        second = self.create_offer("000002")
        token = first.public_token
        self.assertRegex(token, r"^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{10}$")
        self.assertRegex(second.public_token, r"^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{10}$")
        self.assertNotEqual(token, second.public_token)
        first.title = "Updated offer"
        first.save()
        first.refresh_from_db()
        self.assertEqual(first.public_token, token)

    def test_database_rejects_duplicate_token(self):
        first = self.create_offer("000001")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_offer("000002", public_token=first.public_token)

    def test_token_is_not_editable_in_model_forms(self):
        form = modelform_factory(Offer, fields="__all__")
        self.assertNotIn("public_token", form.base_fields)


class OfferPublicTokenMigrationTests(TransactionTestCase):
    def test_existing_offers_receive_distinct_tokens(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        old_target = [("offers", "0001_initial")]
        executor.migrate(old_target)
        apps = executor.loader.project_state(old_target).apps
        TenantBefore = apps.get_model("tenancy", "Tenant")
        LinkBefore = apps.get_model("offers", "TcbManufacturerLink")
        OfferBefore = apps.get_model("offers", "Offer")
        tenant = TenantBefore.objects.create(name="Existing tenant")
        link = LinkBefore.objects.create(
            tenant=tenant, manufacturer_email_domain="existing.example",
        )
        ids = [OfferBefore.objects.create(**offer_fields(tenant, link, code)).pk
               for code in ("000001", "000002")]

        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        rows = Offer.objects.filter(tenant_id=tenant.pk).order_by("offer_code")
        self.assertEqual([row.pk for row in rows], ids)
        tokens = [row.public_token for row in rows]
        self.assertEqual(len(set(tokens)), 2)
        for token in tokens:
            self.assertRegex(token, r"^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{10}$")


@override_settings(TCB_USE_MOCK=True, TCB_PLATFORM_EMAIL_DOMAIN="test-platform.example")
class SeedDemoOfferCommandTests(TestCase):
    def setUp(self):
        MockTcbClient.reset()

    def test_seed_demo_offer_creates_locked_demo_setup(self):
        out = StringIO()

        call_command("seed_demo_offer", stdout=out, base_url="http://demo.test")

        tenant = Tenant.objects.get(name="Demo CPG")
        link = TcbManufacturerLink.objects.get(
            tenant=tenant,
            manufacturer_email_domain="demo-cpg.example",
        )
        channel = DistributionChannel.objects.get(code="gs1_8112_barcode")
        offer = Offer.objects.get(
            base_gs1=build_base_data_string(
                coupon_format=Offer.CouponFormat.DIGITAL,
                funder_id="123456789012",
                offer_code="000001",
            )
        )

        self.assertEqual(link.connection_status, TcbManufacturerLink.ConnectionStatus.AUTHORIZED)
        self.assertEqual(offer.tenant, tenant)
        self.assertEqual(offer.tcb_manufacturer_link, link)
        self.assertEqual(offer.ownership_mode, Offer.OwnershipMode.PARTNER_MANAGED)
        self.assertEqual(offer.status, Offer.Status.LOCKED)
        self.assertTrue(OfferChannelConfig.objects.filter(offer=offer, channel=channel).exists())
        self.assertTrue(
            TcbSyncLog.objects.filter(
                offer=offer,
                operation=TcbSyncLog.Operation.DEPOSIT_OFFER,
                status=TcbSyncLog.Status.SUCCESS,
            ).exists()
        )

        clip = issue_and_deposit_clip(offer, channel)
        self.assertEqual(clip.state, CouponClip.State.DEPOSITED)
        self.assertTrue(clip.serialized_gs1.startswith(offer.base_gs1))
        self.assertIn(f"http://demo.test/offer/{offer.id}/", out.getvalue())

    def test_seed_demo_offer_is_rerunnable_after_mock_process_reset(self):
        call_command("seed_demo_offer", stdout=StringIO())
        MockTcbClient.reset()

        call_command("seed_demo_offer", stdout=StringIO())

        self.assertEqual(Tenant.objects.filter(name="Demo CPG").count(), 1)
        self.assertEqual(DistributionChannel.objects.filter(code="gs1_8112_barcode").count(), 1)
        self.assertEqual(
            TcbManufacturerLink.objects.filter(manufacturer_email_domain="demo-cpg.example").count(),
            1,
        )
        self.assertEqual(Offer.objects.filter(offer_code="000001", tenant__name="Demo CPG").count(), 1)
