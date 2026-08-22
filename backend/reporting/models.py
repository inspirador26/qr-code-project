import uuid

from django.db import models

from coupons.models import CouponClip
from offers.models import Offer
from tenancy.models import Tenant


class ClipEvent(models.Model):
    """Raw, append-only funnel/attribution telemetry — deliberately separate
    from CouponClip (the transactional lifecycle record) so high-cardinality
    event capture never risks the transactional table, and so raw events can
    be pruned/aggregated independently. Field list here is intentionally
    conservative; `raw_context` is the extensible landing spot for anything
    else, pending legal/privacy sign-off on what's actually capturable — see
    the plan's Open Item 5.
    """

    class EventType(models.TextChoices):
        LINK_OPENED = "link_opened", "Link opened"
        CLIP_CONFIRMED = "clip_confirmed", "Clip confirmed"
        WALLET_SAVED = "wallet_saved", "Wallet saved"
        BARCODE_VIEWED = "barcode_viewed", "Barcode viewed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="clip_events")
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="clip_events")
    coupon_clip = models.ForeignKey(
        CouponClip,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        help_text="Nullable — e.g. a link_opened event can precede a confirmed clip.",
    )

    event_type = models.CharField(max_length=20, choices=EventType.choices)
    occurred_at = models.DateTimeField(auto_now_add=True)

    session_id = models.CharField(max_length=64, blank=True)
    ip_hash = models.CharField(max_length=128, blank=True, help_text="Hashed, never raw IP.")
    user_agent = models.CharField(max_length=512, blank=True)
    referrer = models.CharField(max_length=512, blank=True)

    utm_source = models.CharField(max_length=128, blank=True)
    utm_medium = models.CharField(max_length=128, blank=True)
    utm_campaign = models.CharField(max_length=128, blank=True)
    utm_content = models.CharField(max_length=128, blank=True)

    geo_coarse = models.CharField(max_length=128, blank=True, help_text="City/region/country only.")
    device_type = models.CharField(max_length=32, blank=True)

    raw_context = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "offer", "event_type"]),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.occurred_at}"


class RedemptionEvent(models.Model):
    """Sourced entirely from TCB's audit API
    (tcb_integration.client.pull_audit_data), reconciled against CouponClip
    by serial/clip id. This — not any local "redeem" endpoint — is the sole
    source of redemption truth; see the plan's TCB integration seam section.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="redemption_events")
    coupon_clip = models.ForeignKey(CouponClip, on_delete=models.CASCADE, related_name="redemption_events")

    tcb_transaction_ref = models.CharField(max_length=128, blank=True)
    redeemed_at = models.DateTimeField()
    retailer_info = models.JSONField(default=dict, blank=True)

    pulled_at = models.DateTimeField(auto_now_add=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["coupon_clip"], name="unique_redemption_per_clip"),
        ]

    def __str__(self):
        return f"redeemed {self.coupon_clip} @ {self.redeemed_at}"


class PromoReport(models.Model):
    """End-of-promo compiled metrics snapshot per offer — see the plan's
    Reporting section. `metrics` is a snapshot (not live-queried each time)
    so a historical report stays stable even as new events/redemptions
    continue to arrive after generation.
    """

    class Status(models.TextChoices):
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="promo_reports")
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="promo_reports")

    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    generated_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATING)
    metrics = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.offer} report {self.period_start:%Y-%m-%d}–{self.period_end:%Y-%m-%d}"
