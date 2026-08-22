import uuid

from django.core.exceptions import ValidationError
from django.db import models

from tenancy.models import Tenant


class TcbManufacturerLink(models.Model):
    """A CPG client's identity/access at The Coupon Bureau. TCB identifies
    stakeholders by email_domain, not an opaque account id — see the plan's
    "TCB integration seam" section. We (the platform) hold the actual TCB
    credentials at the platform level (settings.TCB_*), not per-tenant —
    this model only tracks which manufacturer email_domain belongs to which
    tenant, and that tenant's TCB brand id once known.
    """

    class ConnectionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tcb_links")
    manufacturer_email_domain = models.CharField(max_length=255)
    brand_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="TCB's internal brand id, fetched via Get Manufacturer Brands. "
        "Brands are created by the manufacturer themselves — we can only read them.",
    )
    connection_status = models.CharField(
        max_length=20, choices=ConnectionStatus.choices, default=ConnectionStatus.PENDING
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "manufacturer_email_domain"],
                name="unique_tenant_manufacturer_domain",
            ),
        ]

    def __str__(self):
        return f"{self.tenant} <-> {self.manufacturer_email_domain}"


class DistributionChannel(models.Model):
    """Data-driven, not schema-per-channel — "several distribution options,
    always expanding" is a stated product requirement, so new channels
    should be rows here, not new tables/code paths.
    """

    code = models.SlugField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name


class Offer(models.Model):
    """Mirrors the Master Offer File (MOF) fields TCB's real
    Create/Edit Master Offer File endpoint expects (see the plan's "TCB
    integration seam" and "Target Data Model" sections) — TCB remains the
    validation authority; this is our local copy for the admin UI and
    reporting.
    """

    class OwnershipMode(models.TextChoices):
        PARTNER_MANAGED = "partner_managed", "Partner managed"
        CLIENT_MANAGED = "client_managed", "Client managed"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_TCB_REGISTRATION = "pending_tcb_registration", "Pending TCB registration"
        LOCKED = "locked", "Locked"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        EXPIRED = "expired", "Expired"
        VOID = "void", "Void"

    class CouponFormat(models.TextChoices):
        DIGITAL = "0", "Digital"
        PAPER = "1", "Paper"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="offers")
    tcb_manufacturer_link = models.ForeignKey(
        TcbManufacturerLink, on_delete=models.RESTRICT, related_name="offers"
    )
    ownership_mode = models.CharField(max_length=20, choices=OwnershipMode.choices)

    # AI(8112) base data string components — see gs1/data_string.py.
    coupon_format = models.CharField(max_length=1, choices=CouponFormat.choices, default=CouponFormat.DIGITAL)
    coupon_funder_id = models.CharField(max_length=12, help_text="GS1 Company Prefix or GTIN, 6-12 digits")
    offer_code = models.CharField(max_length=6, help_text="6-digit offer code, unique per funder")
    base_gs1 = models.CharField(
        max_length=70,
        unique=True,
        help_text="The base AI(8112) data string TCB's MOF is keyed on — "
        "see gs1.data_string.build_base_data_string.",
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # TCB's own campaign/redemption windows — confirmed distinct fields in
    # the real Create/Edit Master Offer File endpoint.
    campaign_start_at = models.DateTimeField()
    campaign_end_at = models.DateTimeField()
    redemption_start_at = models.DateTimeField()
    redemption_end_at = models.DateTimeField()
    rolling_expiration = models.BooleanField(default=False)
    rolling_expiration_days = models.PositiveIntegerField(null=True, blank=True)

    total_circulation = models.PositiveIntegerField(
        help_text="TCB-enforced cap — can be raised, never lowered below current deposit count."
    )
    max_clips = models.PositiveIntegerField(
        help_text="Our own distribution cap; should be <= total_circulation."
    )

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)

    mof_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mirrors TCB's real MOF request-body fields: "
        "primary_purchase_save_value/requirements/req_code/gtins/eans, "
        "additional_purchase_rules_code, second_/third_purchase_*, "
        "save_value_code, applies_to_which_item, store_coupon.",
    )

    distribution_channels = models.ManyToManyField(
        DistributionChannel, through="OfferChannelConfig", related_name="offers"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Tenant-isolation invariant: an offer's tenant must match the tenant
        # that owns its tcb_manufacturer_link — see the plan's "Tenant
        # isolation guarantee" section.
        if self.tcb_manufacturer_link_id and self.tenant_id != self.tcb_manufacturer_link.tenant_id:
            raise ValidationError(
                "Offer.tenant must match the tenant that owns its tcb_manufacturer_link."
            )

    def __str__(self):
        return f"{self.title} ({self.tenant})"


class OfferChannelConfig(models.Model):
    """Per-offer, per-channel config. This is where the Google Wallet
    OfferClass id (formerly `merchants.class_id` in the Node POC) lives
    going forward.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="channel_configs")
    channel = models.ForeignKey(DistributionChannel, on_delete=models.RESTRICT)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["offer", "channel"], name="unique_offer_channel"),
        ]

    def __str__(self):
        return f"{self.offer} / {self.channel}"
