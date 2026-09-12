from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from gs1.data_string import build_base_data_string
from offers.models import DistributionChannel, Offer, OfferChannelConfig, TcbManufacturerLink
from tcb_integration.services import register_and_lock_offer
from tenancy.models import Tenant, TenantMembership


@dataclass(frozen=True)
class AccountIntakeResult:
    tenant: Tenant
    offer: Offer
    tcb_link: TcbManufacturerLink
    channel: DistributionChannel
    membership: TenantMembership | None


@dataclass(frozen=True)
class OfferIntakeResult:
    tenant: Tenant
    offer: Offer
    tcb_link: TcbManufacturerLink
    channel: DistributionChannel


def create_account_with_offer(*, data: dict, invited_by=None) -> AccountIntakeResult:
    tenant, _ = Tenant.objects.update_or_create(
        name=data["tenant_name"],
        defaults={
            "legal_name": data.get("tenant_legal_name", ""),
            "billing_contact_email": data.get("billing_contact_email", ""),
            "status": Tenant.Status.ACTIVE,
        },
    )

    offer_result = create_offer_for_tenant(tenant=tenant, data=data)

    membership = None
    invite_email = data.get("invite_email")
    if invite_email:
        membership, _ = TenantMembership.objects.update_or_create(
            tenant=tenant,
            invited_email=invite_email,
            defaults={
                "role": data.get("invite_role") or TenantMembership.Role.ADMIN,
                "status": TenantMembership.Status.INVITED,
                "invited_by": invited_by,
            },
        )

    return AccountIntakeResult(
        tenant=tenant,
        offer=offer_result.offer,
        tcb_link=offer_result.tcb_link,
        channel=offer_result.channel,
        membership=membership,
    )


def create_offer_for_tenant(*, tenant: Tenant, data: dict) -> OfferIntakeResult:
    tcb_link, _ = TcbManufacturerLink.objects.update_or_create(
        tenant=tenant,
        manufacturer_email_domain=data["manufacturer_email_domain"],
        defaults={
            "brand_id": data.get("brand_id", ""),
            "connection_status": TcbManufacturerLink.ConnectionStatus.AUTHORIZED,
            "verified_at": timezone.now(),
        },
    )
    channel, _ = DistributionChannel.objects.update_or_create(
        code="gs1_8112_barcode",
        defaults={"display_name": "GS1 8112 Barcode", "is_active": True},
    )

    now = timezone.now()
    base_gs1 = build_base_data_string(
        coupon_format=Offer.CouponFormat.DIGITAL,
        funder_id=data["coupon_funder_id"],
        offer_code=data["offer_code"],
    )
    offer_defaults = {
        "tenant": tenant,
        "tcb_manufacturer_link": tcb_link,
        "ownership_mode": Offer.OwnershipMode.PARTNER_MANAGED,
        "coupon_format": Offer.CouponFormat.DIGITAL,
        "coupon_funder_id": data["coupon_funder_id"],
        "offer_code": data["offer_code"],
        "title": data["offer_title"],
        "description": data.get("offer_description", ""),
        "campaign_start_at": now,
        "campaign_end_at": now + timedelta(days=data["campaign_days"]),
        "redemption_start_at": now,
        "redemption_end_at": now + timedelta(days=data["redemption_days"]),
        "rolling_expiration": False,
        "rolling_expiration_days": None,
        "total_circulation": data["total_circulation"],
        "max_clips": data["max_clips"],
        "status": Offer.Status.DRAFT,
        "mof_snapshot": {},
    }
    offer, created = Offer.objects.get_or_create(base_gs1=base_gs1, defaults=offer_defaults)
    if not created and offer.tenant_id != tenant.id:
        raise ValueError(f"base_gs1 {base_gs1} already belongs to another tenant.")
    for field, value in offer_defaults.items():
        setattr(offer, field, value)
    offer.full_clean()
    offer.save()

    OfferChannelConfig.objects.get_or_create(
        offer=offer,
        channel=channel,
        defaults={"config": {}},
    )

    # Keep this outside any atomic block: register_and_lock_offer writes TCB
    # logs that must survive raised exceptions.
    register_and_lock_offer(offer)
    offer.refresh_from_db()

    return OfferIntakeResult(
        tenant=tenant,
        offer=offer,
        tcb_link=tcb_link,
        channel=channel,
    )
