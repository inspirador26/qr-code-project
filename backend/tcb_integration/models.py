import uuid

from django.db import models

from coupons.models import CouponClip
from offers.models import Offer
from tenancy.models import Tenant


class TcbSyncLog(models.Model):
    """Outbox pattern for every call to TCB — deposits, MOF registration,
    audit pulls. A deposit batch is logged here with status='pending' in the
    SAME transaction as creating the relevant CouponClip rows, so "clip
    exists, deposit unconfirmed" is always a recoverable, queryable state.
    See the plan's "TCB integration seam" section for the full retry policy
    (TCB's own documented schedule: retry 5XX after 10s, then 20s) and the
    per-item bucketed-response reconciliation this table exists to support.
    """

    class Operation(models.TextChoices):
        DEPOSIT_OFFER = "deposit_offer", "Deposit offer (MOF create/edit)"
        DEPOSIT_SERIAL_BATCH = "deposit_serial_batch", "Deposit serial batch"
        PULL_AUDIT = "pull_audit", "Pull audit data"
        CREATE_FETCH_CODE = "create_fetch_code", "Create fetch code"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"  # a batch deposit's per-item buckets weren't all success
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tcb_sync_logs")
    offer = models.ForeignKey(
        Offer, on_delete=models.SET_NULL, null=True, blank=True, related_name="tcb_sync_logs"
    )
    coupon_clip = models.ForeignKey(
        CouponClip,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tcb_sync_logs",
        help_text="Nullable — a batch deposit covers many clips; see "
        "TcbSyncLogClip for the full batch membership.",
    )

    operation = models.CharField(max_length=30, choices=Operation.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)

    attempt_count = models.PositiveIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "next_retry_at"]),
        ]

    def __str__(self):
        return f"{self.operation} ({self.status}) @ {self.tenant}"


class TcbSyncLogClip(models.Model):
    """Batch membership for a deposit_serial_batch sync log entry — up to 20
    CouponClips per TCB deposit call. Kept as an explicit join table (rather
    than a plain M2M) so we can record the per-item outcome bucket
    (newly_added / try_again / already_added / invalid_gs1s /
    no_copies_available / not_owned_by_you / not_yet_live / not_locked /
    expired / settled / metadata_not_set) TCB's real deposit response
    returns for each item in the batch.
    """

    sync_log = models.ForeignKey(TcbSyncLog, on_delete=models.CASCADE, related_name="clip_outcomes")
    coupon_clip = models.ForeignKey(CouponClip, on_delete=models.CASCADE)
    outcome_bucket = models.CharField(max_length=30, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sync_log", "coupon_clip"], name="unique_sync_log_clip"
            ),
        ]
