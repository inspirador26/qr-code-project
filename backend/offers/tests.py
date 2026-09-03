from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

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
