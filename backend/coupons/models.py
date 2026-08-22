import uuid

from django.db import models

from offers.models import DistributionChannel, Offer
from tenancy.models import Tenant


class CouponClip(models.Model):
    """One row per issued serial — supersedes the Node POC's `codes` table.
    Critical semantic change from that POC: `redeemed_at`/`state` transition
    to redeemed must be written ONLY by the TCB audit-sync job (see
    tcb_integration), never by a consumer-facing endpoint — TCB/the
    retailer's POS is the sole redemption authority under AI(8112).
    """

    class State(models.TextChoices):
        ISSUED = "issued", "Issued"
        PENDING_DEPOSIT = "pending_deposit", "Pending deposit"
        DEPOSITED = "deposited", "Deposited"
        REDEEMED = "redeemed", "Redeemed"
        EXPIRED = "expired", "Expired"
        VOID = "void", "Void"

    class CreatedVia(models.TextChoices):
        QR_SCAN = "qr_scan", "QR scan"
        DIRECT_LINK = "direct_link", "Direct link"
        API = "api", "API"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey(Offer, on_delete=models.RESTRICT, related_name="clips")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="clips")  # denormalized
    distribution_channel = models.ForeignKey(DistributionChannel, on_delete=models.RESTRICT)

    # Populated once deposited — see tcb_integration.client.deposit_serials.
    # Recommended default is TCB-generated serials (mode="base_gs1"), so
    # these are null until the deposit response comes back.
    serialized_gs1 = models.CharField(max_length=70, blank=True)
    serial_number = models.CharField(
        max_length=15,
        blank=True,
        help_text="Consumer-code portion only; must start with our TCB-issued "
        "serialization prefix if we generate it ourselves rather than TCB.",
    )

    state = models.CharField(max_length=20, choices=State.choices, default=State.ISSUED)

    issued_at = models.DateTimeField(auto_now_add=True)
    deposited_at = models.DateTimeField(null=True, blank=True)
    valid_from_at = models.DateTimeField(
        null=True, blank=True, help_text="Returned per-item by the real deposit response."
    )
    valid_till_at = models.DateTimeField(null=True, blank=True)

    tcb_deposit_status = models.CharField(max_length=20, blank=True)

    redeemed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Written ONLY by the TCB audit-sync job. Never set this from a "
        "consumer-facing view or endpoint.",
    )

    created_via = models.CharField(max_length=20, choices=CreatedVia.choices, default=CreatedVia.QR_SCAN)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["serialized_gs1"],
                name="unique_serialized_gs1",
                condition=models.Q(serialized_gs1__gt=""),
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "state"]),
            models.Index(fields=["offer"]),
        ]

    def __str__(self):
        return self.serialized_gs1 or f"clip {self.id} (undeposited)"


class CouponFetchCode(models.Model):
    """A short-lived numeric/alphanumeric PIN covering 1-15 already-deposited
    CouponClips — TCB's `POST /provider/time_bound_fetch_code`. This is very
    likely the actual mechanism behind the client's own description of
    depositing "a unique pincode" per offer, and is a first-class
    distribution mechanism (POS keypad / ecommerce checkout entry), not an
    edge case — see the plan's "Target Data Model" section.
    """

    class Mode(models.TextChoices):
        POS = "pos", "Point of sale"
        ECOMM = "ecomm", "Ecommerce"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="fetch_codes")
    clips = models.ManyToManyField(CouponClip, related_name="fetch_codes")
    fetch_code = models.CharField(
        max_length=32,
        help_text="Format enforced by TCB itself (prefixed with our provider prefix).",
    )
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.POS)
    valid_till_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.fetch_code
