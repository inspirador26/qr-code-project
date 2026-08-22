from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from coupons.models import CouponClip
from gs1.data_string import build_base_data_string
from offers.models import DistributionChannel, Offer, TcbManufacturerLink
from reporting.models import RedemptionEvent
from tenancy.models import Tenant

from .client import get_tcb_client
from .exceptions import TcbApiError
from .mock_client import MockTcbClient
from .models import TcbSyncLog
from .services import issue_and_deposit_clip, pull_and_reconcile_redemptions, register_and_lock_offer

TEST_PROVIDER_DOMAIN = "test-platform.example"


@override_settings(TCB_USE_MOCK=True, TCB_PLATFORM_EMAIL_DOMAIN=TEST_PROVIDER_DOMAIN)
class TcbFrameworkTests(TestCase):
    def setUp(self):
        MockTcbClient.reset()

        self.tenant = Tenant.objects.create(name="Acme CPG")
        self.link = TcbManufacturerLink.objects.create(
            tenant=self.tenant,
            manufacturer_email_domain="acme-cpg.com",
            brand_id="brand-123",
        )
        self.channel, _ = DistributionChannel.objects.get_or_create(
            code="gs1_8112_barcode", defaults={"display_name": "GS1 8112 Barcode"}
        )

    def _make_offer(self, *, total_circulation=10, ownership_mode=None):
        now = timezone.now()
        base_gs1 = build_base_data_string(
            coupon_format="0", funder_id="123456789012", offer_code="000001"
        )
        return Offer.objects.create(
            tenant=self.tenant,
            tcb_manufacturer_link=self.link,
            ownership_mode=ownership_mode or Offer.OwnershipMode.PARTNER_MANAGED,
            coupon_funder_id="123456789012",
            offer_code="000001",
            base_gs1=base_gs1,
            title="Save $1 on Acme Sauce",
            campaign_start_at=now,
            campaign_end_at=now + timedelta(days=30),
            redemption_start_at=now,
            redemption_end_at=now + timedelta(days=60),
            total_circulation=total_circulation,
            max_clips=total_circulation,
        )

    def test_get_tcb_client_returns_mock_by_default(self):
        self.assertIsInstance(get_tcb_client(), MockTcbClient)

    def test_full_happy_path_register_deposit_redeem_reconcile(self):
        offer = self._make_offer()

        register_and_lock_offer(offer)
        offer.refresh_from_db()
        self.assertEqual(offer.status, Offer.Status.LOCKED)

        clip = issue_and_deposit_clip(offer, self.channel)
        self.assertEqual(clip.state, CouponClip.State.DEPOSITED)
        self.assertTrue(clip.serialized_gs1.startswith(offer.base_gs1))
        self.assertTrue(clip.serial_number)

        sync_logs = TcbSyncLog.objects.filter(offer=offer)
        self.assertEqual(sync_logs.filter(status=TcbSyncLog.Status.SUCCESS).count(), 2)  # register + deposit

        # No real POS in tests — use the mock's test-only helper.
        MockTcbClient.simulate_redemption(clip.serialized_gs1)

        reconciled_count = pull_and_reconcile_redemptions()
        self.assertEqual(reconciled_count, 1)

        clip.refresh_from_db()
        self.assertEqual(clip.state, CouponClip.State.REDEEMED)
        self.assertIsNotNone(clip.redeemed_at)
        self.assertTrue(RedemptionEvent.objects.filter(coupon_clip=clip).exists())

        # Idempotent: a second pull shouldn't double-count or error.
        self.assertEqual(pull_and_reconcile_redemptions(), 0)

    def test_deposit_fails_cleanly_when_offer_never_registered(self):
        offer = self._make_offer()
        # Deliberately skip register_and_lock_offer — the MOF doesn't exist
        # in TCB at all yet, distinct from "exists but not locked" below.
        with self.assertRaises(TcbApiError):
            issue_and_deposit_clip(offer, self.channel)

        clip = CouponClip.objects.get(offer=offer)
        self.assertEqual(clip.state, CouponClip.State.ISSUED)  # created, but never deposited
        self.assertEqual(clip.tcb_deposit_status, "invalid_gs1s")

    def test_deposit_fails_cleanly_when_offer_registered_but_not_locked(self):
        offer = self._make_offer()
        client = get_tcb_client()
        # Register the MOF directly via the client (bypassing
        # register_and_lock_offer, which always locks) so it exists but
        # lock=False — the real API's documented precondition for deposit.
        client.register_offer(
            base_gs1=offer.base_gs1,
            manufacturer_domain=self.link.manufacturer_email_domain,
            brand_id=self.link.brand_id,
            update_mode=0,
            lock=False,
            mof_fields={"total_circulation": offer.total_circulation},
        )
        client.assign_provider(
            base_gs1=offer.base_gs1,
            manufacturer_domain=self.link.manufacturer_email_domain,
            provider_domain=TEST_PROVIDER_DOMAIN,
        )

        with self.assertRaises(TcbApiError):
            issue_and_deposit_clip(offer, self.channel)

        clip = CouponClip.objects.get(offer=offer)
        self.assertEqual(clip.state, CouponClip.State.ISSUED)
        self.assertEqual(clip.tcb_deposit_status, "not_locked")

    def test_deposit_fails_when_circulation_exhausted(self):
        offer = self._make_offer(total_circulation=1)
        register_and_lock_offer(offer)

        first = issue_and_deposit_clip(offer, self.channel)
        self.assertEqual(first.state, CouponClip.State.DEPOSITED)

        with self.assertRaises(TcbApiError):
            issue_and_deposit_clip(offer, self.channel)

        second = CouponClip.objects.exclude(id=first.id).get(offer=offer)
        self.assertEqual(second.tcb_deposit_status, "no_copies_available")

    def test_client_managed_offer_cannot_be_registered_by_us(self):
        offer = self._make_offer(ownership_mode=Offer.OwnershipMode.CLIENT_MANAGED)
        with self.assertRaises(ValueError):
            register_and_lock_offer(offer)

    def test_assign_provider_toggles(self):
        client = get_tcb_client()
        offer = self._make_offer()
        register_and_lock_offer(offer)  # registers + assigns us as provider

        # Toggling again should unassign, per TCB's real documented behavior.
        resp = client.assign_provider(
            base_gs1=offer.base_gs1,
            manufacturer_domain=self.link.manufacturer_email_domain,
            provider_domain=TEST_PROVIDER_DOMAIN,
        )
        self.assertEqual(resp["action"], "deleted")

        # Now deposits should fail as not_owned_by_you.
        with self.assertRaises(TcbApiError):
            issue_and_deposit_clip(offer, self.channel)
        clip = CouponClip.objects.filter(offer=offer).latest("issued_at")
        self.assertEqual(clip.tcb_deposit_status, "not_owned_by_you")
