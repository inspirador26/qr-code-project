import json
import tempfile
from datetime import timedelta
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import TestCase, override_settings
from django.utils import timezone

from coupons.models import CouponClip
from offers.models import DistributionChannel, Offer, TcbManufacturerLink
from tenancy.models import Tenant

from .service import WalletConfigError, build_save_jwt, google_wallet_save_url


def _write_fake_service_account(tmp_path: Path) -> tuple[Path, rsa.RSAPrivateKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    sa_path = tmp_path / "wallet-sa.json"
    sa_path.write_text(
        json.dumps({"client_email": "wallet-sa@example.iam.gserviceaccount.com", "private_key": pem})
    )
    return sa_path, private_key


class GoogleWalletServiceTests(TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.sa_path, self.private_key = _write_fake_service_account(Path(self._tmpdir.name))

        self.tenant = Tenant.objects.create(name="Acme CPG")
        link = TcbManufacturerLink.objects.create(
            tenant=self.tenant, manufacturer_email_domain="acme-cpg.com"
        )
        now = timezone.now()
        self.offer = Offer.objects.create(
            tenant=self.tenant,
            tcb_manufacturer_link=link,
            ownership_mode=Offer.OwnershipMode.PARTNER_MANAGED,
            coupon_funder_id="123456789012",
            offer_code="000001",
            base_gs1="811200123456789012000001",
            title="Save $1 on Acme Sauce",
            campaign_start_at=now,
            campaign_end_at=now + timedelta(days=30),
            redemption_start_at=now,
            redemption_end_at=now + timedelta(days=60),
            total_circulation=1000,
            max_clips=1000,
        )
        self.channel, _ = DistributionChannel.objects.get_or_create(
            code="google_wallet", defaults={"display_name": "Google Wallet"}
        )
        self.clip = CouponClip.objects.create(
            offer=self.offer, tenant=self.tenant, distribution_channel=self.channel
        )

    def _settings(self):
        return override_settings(
            GOOGLE_WALLET_ISSUER_ID="3388000000000000000",
            GOOGLE_WALLET_ISSUER_NAME="TestIssuer",
            GOOGLE_WALLET_SERVICE_ACCOUNT_FILE=str(self.sa_path),
        )

    def test_build_save_jwt_signed_correctly_and_payload_shape(self):
        # lru_cache on _load_service_account would leak across tests/settings
        # otherwise — clear it so each test's override_settings takes effect.
        from . import service

        service._load_service_account.cache_clear()

        with self._settings():
            token = build_save_jwt(self.clip)

        public_key = self.private_key.public_key()
        decoded = jwt.decode(token, public_key, algorithms=["RS256"], audience="google")

        self.assertEqual(decoded["iss"], "wallet-sa@example.iam.gserviceaccount.com")
        self.assertEqual(decoded["typ"], "savetoandroidpay")

        offer_class = decoded["payload"]["offerClasses"][0]
        self.assertEqual(offer_class["id"], f"3388000000000000000.tenant_{self.tenant.id}")
        self.assertEqual(offer_class["provider"], "Acme CPG")
        self.assertNotIn("reviewStatus", offer_class)  # see service.py comment on why

        offer_object = decoded["payload"]["offerObjects"][0]
        self.assertEqual(offer_object["id"], f"3388000000000000000.{self.clip.id}")
        self.assertEqual(offer_object["classId"], offer_class["id"])
        self.assertEqual(offer_object["barcode"]["type"], "CODE_128")
        self.assertEqual(offer_object["barcode"]["value"], str(self.clip.id))

    def test_class_id_is_stable_across_offers_for_same_tenant(self):
        from . import service

        service._load_service_account.cache_clear()

        other_offer = Offer.objects.create(
            tenant=self.tenant,
            tcb_manufacturer_link=self.offer.tcb_manufacturer_link,
            ownership_mode=Offer.OwnershipMode.PARTNER_MANAGED,
            coupon_funder_id="123456789012",
            offer_code="000002",
            base_gs1="811200123456789012000002",
            title="Save $2 on Acme Sauce 2",
            campaign_start_at=self.offer.campaign_start_at,
            campaign_end_at=self.offer.campaign_end_at,
            redemption_start_at=self.offer.redemption_start_at,
            redemption_end_at=self.offer.redemption_end_at,
            total_circulation=1000,
            max_clips=1000,
        )
        other_clip = CouponClip.objects.create(
            offer=other_offer, tenant=self.tenant, distribution_channel=self.channel
        )

        with self._settings():
            token_a = build_save_jwt(self.clip)
            token_b = build_save_jwt(other_clip)

        public_key = self.private_key.public_key()
        class_a = jwt.decode(token_a, public_key, algorithms=["RS256"], audience="google")[
            "payload"
        ]["offerClasses"][0]["id"]
        class_b = jwt.decode(token_b, public_key, algorithms=["RS256"], audience="google")[
            "payload"
        ]["offerClasses"][0]["id"]

        self.assertEqual(class_a, class_b)

    def test_missing_config_raises_wallet_config_error(self):
        from . import service

        service._load_service_account.cache_clear()

        with override_settings(GOOGLE_WALLET_ISSUER_ID="", GOOGLE_WALLET_ISSUER_NAME=""):
            with self.assertRaises(WalletConfigError):
                build_save_jwt(self.clip)

    def test_save_url_has_expected_prefix(self):
        from . import service

        service._load_service_account.cache_clear()

        with self._settings():
            url = google_wallet_save_url(self.clip)

        self.assertTrue(url.startswith("https://pay.google.com/gp/v/save/"))
