"""
Google Wallet "Save to Wallet" — ported from server.js's `/wallet/google/:codeId`
route. Behavior is a faithful port, not a redesign, except where the tenant
model requires it:

- `ISSUER_ID`/`ISSUER_NAME`/the wallet-sa.json service account are a
  platform-level Google Wallet Issuer, shared across all tenants — same
  pattern as the TCB credentials (we hold one Issuer account; tenants are
  scoped underneath it), now sourced from settings instead of hardcoded.
- **OfferClass scope**: the Node POC had one class per `merchant`, reused
  across all of that merchant's offers/codes. The new schema doesn't have a
  `merchants` table — `merchant.provider`/`redemption_channel` most closely
  maps onto `Tenant` (the CPG), not `Offer`, so the class id is derived
  deterministically from `tenant.id` (`{ISSUER_ID}.tenant_{tenant.id}`) and
  reused across every offer that tenant has — matching the original "stable,
  one class per merchant" design intent rather than minting a new class per
  offer. The computed value is still recorded in each offer's
  `OfferChannelConfig` (channel `google_wallet`) for inspection/audit.
- **OfferObject scope**: one per `CouponClip`, same as one per `codes` row
  in the Node POC.
- **Barcode value**: kept as CODE_128 encoding `coupon_clip.id` (the same
  shape the Node POC used, now a UUID clip id rather than a codes.id UUID)
  — **not** yet switched to the AI(8112) serialized data string. That switch
  is a real redemption-semantics change flagged as an open decision in the
  plan (Open Item 6) and needs explicit confirmation before implementing,
  not something to decide unilaterally while porting.
- `redemption_channel` (INSTORE/ONLINE/BOTH) was a column on `merchants` in
  the Node POC; here it's channel-specific config, read from
  `OfferChannelConfig.config` (defaults to "BOTH" if unset), matching the
  plan's explicit statement that this kind of Google-Wallet-specific data
  belongs in that JSONField.
"""

import json
from functools import lru_cache

import jwt
from django.conf import settings

from coupons.models import CouponClip
from offers.models import DistributionChannel, OfferChannelConfig

GOOGLE_WALLET_CHANNEL_CODE = "google_wallet"


class WalletConfigError(RuntimeError):
    """Raised when Google Wallet settings/credentials aren't configured."""


@lru_cache(maxsize=1)
def _load_service_account():
    if not settings.GOOGLE_WALLET_SERVICE_ACCOUNT_FILE:
        raise WalletConfigError(
            "GOOGLE_WALLET_SERVICE_ACCOUNT_FILE is not set — see .env.example."
        )
    with open(settings.GOOGLE_WALLET_SERVICE_ACCOUNT_FILE, encoding="utf-8") as f:
        return json.load(f)


def _class_id_for_tenant(tenant) -> str:
    return f"{settings.GOOGLE_WALLET_ISSUER_ID}.tenant_{tenant.id}"


def _object_id_for_clip(clip: CouponClip) -> str:
    return f"{settings.GOOGLE_WALLET_ISSUER_ID}.{clip.id}"


def _get_or_create_channel_config(offer, class_id: str, redemption_channel: str) -> OfferChannelConfig:
    channel, _ = DistributionChannel.objects.get_or_create(
        code=GOOGLE_WALLET_CHANNEL_CODE,
        defaults={"display_name": "Google Wallet"},
    )
    config, _ = OfferChannelConfig.objects.get_or_create(
        offer=offer,
        channel=channel,
        defaults={"config": {"class_id": class_id, "redemption_channel": redemption_channel}},
    )
    return config


def build_save_jwt(clip: CouponClip) -> str:
    """Builds and RS256-signs the Google Wallet save JWT for one issued
    coupon clip. Raises WalletConfigError if Google Wallet settings/
    credentials aren't configured.
    """
    if not settings.GOOGLE_WALLET_ISSUER_ID or not settings.GOOGLE_WALLET_ISSUER_NAME:
        raise WalletConfigError(
            "GOOGLE_WALLET_ISSUER_ID and GOOGLE_WALLET_ISSUER_NAME must be set — see .env.example."
        )

    wallet_key = _load_service_account()
    offer = clip.offer
    tenant = clip.tenant

    class_id = _class_id_for_tenant(tenant)
    object_id = _object_id_for_clip(clip)

    channel_config = _get_or_create_channel_config(offer, class_id, redemption_channel="BOTH")
    redemption_channel = channel_config.config.get("redemption_channel", "BOTH")

    jwt_payload = {
        "iss": wallet_key["client_email"],
        "aud": "google",
        "typ": "savetoandroidpay",
        "payload": {
            # Omit reviewStatus: classes already exist server-side as
            # 'approved' once created, and a save JWT can't downgrade an
            # approved class — see .claude/skills/google-wallet/SKILL.md for
            # the original bug this caused in the Node POC.
            "offerClasses": [
                {
                    "id": class_id,
                    "issuerName": settings.GOOGLE_WALLET_ISSUER_NAME,
                    "title": tenant.name,
                    "provider": tenant.name,
                    "redemptionChannel": redemption_channel,
                }
            ],
            "offerObjects": [
                {
                    "id": object_id,
                    "classId": class_id,
                    "state": "ACTIVE",
                    "title": offer.title,
                    "header": {"defaultValue": {"language": "en", "value": tenant.name}},
                    "barcode": {
                        "type": "CODE_128",
                        "value": str(clip.id),
                        "alternateText": str(clip.id),
                    },
                    "validTimeInterval": {
                        "start": {"date": offer.redemption_start_at.isoformat()},
                        "end": {"date": offer.redemption_end_at.isoformat()},
                    },
                }
            ],
        },
    }

    return jwt.encode(jwt_payload, wallet_key["private_key"], algorithm="RS256")


def google_wallet_save_url(clip: CouponClip) -> str:
    token = build_save_jwt(clip)
    return f"https://pay.google.com/gp/v/save/{token}"
