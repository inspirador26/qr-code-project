from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from gs1.data_string import build_base_data_string
from offers.models import (
    DistributionChannel,
    Offer,
    OfferChannelConfig,
    TcbManufacturerLink,
)
from tcb_integration.exceptions import TcbApiError
from tcb_integration.services import register_and_lock_offer
from tenancy.models import Tenant


class Command(BaseCommand):
    help = "Seed a locked demo Tenant/Offer setup for the MVP clip demo."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-name", default="Demo CPG")
        parser.add_argument("--tenant-legal-name", default="Demo CPG, Inc.")
        parser.add_argument("--billing-email", default="billing@demo-cpg.example")
        parser.add_argument("--manufacturer-domain", default="demo-cpg.example")
        parser.add_argument("--brand-id", default="demo-brand-001")
        parser.add_argument("--coupon-funder-id", default="123456789012")
        parser.add_argument("--offer-code", default="000001")
        parser.add_argument("--title", default="Save $1 on Demo Sauce")
        parser.add_argument(
            "--description",
            default="Demo offer seeded for the QR to GS1 barcode clip flow.",
        )
        parser.add_argument("--total-circulation", type=int, default=1000)
        parser.add_argument("--max-clips", type=int, default=1000)
        parser.add_argument("--campaign-days", type=int, default=30)
        parser.add_argument("--redemption-days", type=int, default=60)
        parser.add_argument("--base-url", default="http://127.0.0.1:8000")
        parser.add_argument(
            "--allow-real-tcb",
            action="store_true",
            help=(
                "Allow this demo command to call the real TCB client "
                "if TCB_USE_MOCK=False."
            ),
        )

    def handle(self, *args, **options):
        if not settings.TCB_USE_MOCK and not options["allow_real_tcb"]:
            raise CommandError(
                "seed_demo_offer is intended for local/mock demo data. "
                "Set TCB_USE_MOCK=True or pass --allow-real-tcb intentionally."
            )
        if options["total_circulation"] <= 0:
            raise CommandError("--total-circulation must be greater than zero.")
        if options["max_clips"] <= 0:
            raise CommandError("--max-clips must be greater than zero.")
        if options["max_clips"] > options["total_circulation"]:
            raise CommandError(
                "--max-clips must be less than or equal to --total-circulation."
            )

        tenant = self._seed_tenant(options)
        link = self._seed_tcb_link(tenant, options)
        channel = self._seed_distribution_channel()
        offer = self._seed_offer(tenant, link, options)
        OfferChannelConfig.objects.get_or_create(
            offer=offer,
            channel=channel,
            defaults={"config": {}},
        )

        self._register_for_demo(offer)

        offer.refresh_from_db()
        base_url = options["base_url"].rstrip("/")
        self.stdout.write(self.style.SUCCESS("Seeded demo offer."))
        self.stdout.write(f"Tenant: {tenant.name} ({tenant.id})")
        self.stdout.write(f"Offer: {offer.title} ({offer.id})")
        self.stdout.write(f"Offer status: {offer.status}")
        self.stdout.write(f"Distribution channel: {channel.code}")
        self.stdout.write(f"Planned offer URL: {base_url}/offer/{offer.id}/")

    def _seed_tenant(self, options):
        tenant, _ = Tenant.objects.get_or_create(
            name=options["tenant_name"],
            defaults={
                "legal_name": options["tenant_legal_name"],
                "billing_contact_email": options["billing_email"],
                "status": Tenant.Status.ACTIVE,
            },
        )
        tenant.legal_name = options["tenant_legal_name"]
        tenant.billing_contact_email = options["billing_email"]
        tenant.status = Tenant.Status.ACTIVE
        tenant.save(
            update_fields=["legal_name", "billing_contact_email", "status", "updated_at"]
        )
        return tenant

    def _seed_tcb_link(self, tenant, options):
        link, _ = TcbManufacturerLink.objects.update_or_create(
            tenant=tenant,
            manufacturer_email_domain=options["manufacturer_domain"],
            defaults={
                "brand_id": options["brand_id"],
                "connection_status": TcbManufacturerLink.ConnectionStatus.AUTHORIZED,
                "verified_at": timezone.now(),
            },
        )
        return link

    def _seed_distribution_channel(self):
        channel, _ = DistributionChannel.objects.update_or_create(
            code="gs1_8112_barcode",
            defaults={"display_name": "GS1 8112 Barcode", "is_active": True},
        )
        return channel

    def _seed_offer(self, tenant, link, options):
        now = timezone.now()
        base_gs1 = build_base_data_string(
            coupon_format=Offer.CouponFormat.DIGITAL,
            funder_id=options["coupon_funder_id"],
            offer_code=options["offer_code"],
        )
        defaults = {
            "tenant": tenant,
            "tcb_manufacturer_link": link,
            "ownership_mode": Offer.OwnershipMode.PARTNER_MANAGED,
            "coupon_format": Offer.CouponFormat.DIGITAL,
            "coupon_funder_id": options["coupon_funder_id"],
            "offer_code": options["offer_code"],
            "title": options["title"],
            "description": options["description"],
            "campaign_start_at": now,
            "campaign_end_at": now + timedelta(days=options["campaign_days"]),
            "redemption_start_at": now,
            "redemption_end_at": now + timedelta(days=options["redemption_days"]),
            "rolling_expiration": False,
            "rolling_expiration_days": None,
            "total_circulation": options["total_circulation"],
            "max_clips": options["max_clips"],
            "status": Offer.Status.DRAFT,
            "mof_snapshot": {},
        }
        offer, created = Offer.objects.get_or_create(
            base_gs1=base_gs1,
            defaults=defaults,
        )
        if not created and offer.tenant_id != tenant.id:
            raise CommandError(
                f"base_gs1 {base_gs1} already belongs to tenant {offer.tenant_id}; "
                "refusing to move it to the demo tenant."
            )

        for field, value in defaults.items():
            setattr(offer, field, value)
        offer.full_clean()
        offer.save()
        return offer

    def _register_for_demo(self, offer):
        previous_status = offer.status

        if settings.TCB_USE_MOCK:
            offer.status = Offer.Status.DRAFT
            offer.save(update_fields=["status", "updated_at"])

        try:
            register_and_lock_offer(offer)
        except TcbApiError as exc:
            if settings.TCB_USE_MOCK and "already exists (update_mode=0 requires create)" in str(
                exc
            ):
                offer.status = Offer.Status.LOCKED
                offer.save(update_fields=["status", "updated_at"])
                self.stdout.write(
                    self.style.WARNING(
                        "Demo offer was already present in this mock TCB process; "
                        "leaving the database offer locked."
                    )
                )
                return

            offer.status = previous_status
            offer.save(update_fields=["status", "updated_at"])
            raise CommandError(f"Could not register and lock demo offer: {exc}") from exc
