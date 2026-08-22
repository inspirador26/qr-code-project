"""
Business-logic layer between the app (views/admin/tasks) and the TCB client
seam (client.get_tcb_client(), currently backed by mock_client.MockTcbClient
by default — see settings.TCB_USE_MOCK). This is what actually writes
Offer/CouponClip/TcbSyncLog rows; views and admin actions should call these
functions, not the client directly, so every call is uniformly logged.

Synchronous for now, deliberately: the plan's fuller design calls for a
Celery-driven outbox worker draining `TcbSyncLog(status='pending')` rows in
batches with TCB's documented retry schedule (10s, then 20s) — that worker
isn't built yet. These functions are what it would call into once it is;
until then, callers get an immediate result or a raised TcbApiError.
"""

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from coupons.models import CouponClip
from offers.models import Offer

from .client import get_tcb_client
from .exceptions import TcbApiError
from .models import TcbSyncLog, TcbSyncLogClip


def _build_mof_fields(offer: Offer) -> dict:
    """Assembles the exact field names TCB's real Create/Edit Master Offer
    File endpoint expects, from Offer's explicit columns + mof_snapshot.
    See the plan's "TCB integration seam" section for the full field list.
    """
    fields = {
        "description": offer.description,
        "campaign_start_time": offer.campaign_start_at.strftime("%Y-%m-%d"),
        "campaign_end_time": offer.campaign_end_at.strftime("%Y-%m-%d"),
        "redemption_start_time": offer.redemption_start_at.strftime("%Y-%m-%d"),
        "redemption_end_time": offer.redemption_end_at.strftime("%Y-%m-%d"),
        "rolling_expiration": 1 if offer.rolling_expiration else 0,
        "total_circulation": offer.total_circulation,
    }
    if offer.rolling_expiration and offer.rolling_expiration_days:
        fields["rolling_expiration_days"] = offer.rolling_expiration_days
    fields.update(offer.mof_snapshot or {})
    return fields


def register_and_lock_offer(offer: Offer) -> Offer:
    """partner_managed path only: we create + lock the MOF and authorize
    ourselves as its Provider. For client_managed offers the CPG (or their
    own authorized partner) does this on their end — see the plan's
    ownership_mode split — calling this on a client_managed offer is a
    programming error, not a retryable failure.
    """
    if offer.ownership_mode != Offer.OwnershipMode.PARTNER_MANAGED:
        raise ValueError(
            f"register_and_lock_offer is only for partner_managed offers, "
            f"got {offer.ownership_mode!r} for offer {offer.id}"
        )

    from django.conf import settings

    client = get_tcb_client()
    manufacturer_domain = offer.tcb_manufacturer_link.manufacturer_email_domain

    log = TcbSyncLog.objects.create(
        tenant=offer.tenant,
        offer=offer,
        operation=TcbSyncLog.Operation.DEPOSIT_OFFER,
        request_payload={"base_gs1": offer.base_gs1, "manufacturer_domain": manufacturer_domain},
    )

    try:
        register_response = client.register_offer(
            base_gs1=offer.base_gs1,
            manufacturer_domain=manufacturer_domain,
            brand_id=offer.tcb_manufacturer_link.brand_id,
            update_mode=0 if offer.status == Offer.Status.DRAFT else 1,
            lock=True,
            mof_fields=_build_mof_fields(offer),
        )
        assign_response = client.assign_provider(
            base_gs1=offer.base_gs1,
            manufacturer_domain=manufacturer_domain,
            provider_domain=settings.TCB_PLATFORM_EMAIL_DOMAIN,
        )
    except TcbApiError as exc:
        log.status = TcbSyncLog.Status.FAILED
        log.response_payload = {"error": str(exc)}
        log.attempt_count += 1
        log.save(update_fields=["status", "response_payload", "attempt_count", "updated_at"])
        raise

    log.status = TcbSyncLog.Status.SUCCESS
    log.response_payload = {"register": register_response, "assign_provider": assign_response}
    log.attempt_count += 1
    log.save(update_fields=["status", "response_payload", "attempt_count", "updated_at"])

    offer.status = Offer.Status.LOCKED
    offer.save(update_fields=["status", "updated_at"])
    return offer


def issue_and_deposit_clip(offer: Offer, distribution_channel, *, created_via=None) -> CouponClip:
    """Issues one CouponClip and deposits it with TCB in the same call —
    the plan's fuller outbox design would separate "issue" from "deposit
    now vs. later via the retry worker"; this collapses them for the
    framework's first pass. Raises TcbApiError if the deposit didn't land
    in the newly_added bucket (the clip row still exists, in ISSUED state,
    for a human/retry-worker to investigate — never silently lost).

    Deliberately NOT wrapped in @transaction.atomic: the whole point of
    logging a failure to TcbSyncLog/CouponClip is that it survives the
    exception this function raises on a non-newly_added outcome. Wrapping
    this in one atomic block would roll back that exact record on the
    exact path it exists to capture.
    """
    client = get_tcb_client()

    clip = CouponClip.objects.create(
        offer=offer,
        tenant=offer.tenant,
        distribution_channel=distribution_channel,
        created_via=created_via or CouponClip.CreatedVia.QR_SCAN,
    )

    log = TcbSyncLog.objects.create(
        tenant=offer.tenant,
        offer=offer,
        coupon_clip=clip,
        operation=TcbSyncLog.Operation.DEPOSIT_SERIAL_BATCH,
        request_payload={"gs1s": [offer.base_gs1], "mode": "base_gs1"},
    )

    try:
        result = client.deposit_serials(gs1s=[offer.base_gs1], mode="base_gs1")
    except TcbApiError as exc:
        log.status = TcbSyncLog.Status.FAILED
        log.response_payload = {"error": str(exc)}
        log.attempt_count += 1
        log.save(update_fields=["status", "response_payload", "attempt_count", "updated_at"])
        raise

    log.attempt_count += 1

    if result.newly_added:
        deposited = result.newly_added[0]
        clip.serialized_gs1 = deposited.gs1
        clip.serial_number = deposited.gs1[len(offer.base_gs1) + 1 :]  # skip base_gs1 + serial VLI digit
        clip.state = CouponClip.State.DEPOSITED
        clip.deposited_at = timezone.now()
        clip.valid_from_at = deposited.valid_from
        clip.valid_till_at = deposited.valid_till
        clip.tcb_deposit_status = "newly_added"
        clip.save()

        TcbSyncLogClip.objects.create(sync_log=log, coupon_clip=clip, outcome_bucket="newly_added")
        log.status = TcbSyncLog.Status.SUCCESS
        log.response_payload = {"gs1": deposited.gs1}
        log.save(update_fields=["status", "attempt_count", "response_payload", "updated_at"])
        return clip

    # Every other bucket means the clip was NOT deposited — find which one.
    bucket = result.bucket_for(offer.base_gs1)
    clip.tcb_deposit_status = bucket
    clip.save(update_fields=["tcb_deposit_status"])

    TcbSyncLogClip.objects.create(sync_log=log, coupon_clip=clip, outcome_bucket=bucket)
    log.status = TcbSyncLog.Status.PARTIAL
    log.response_payload = {"bucket": bucket}
    log.save(update_fields=["status", "attempt_count", "response_payload", "updated_at"])

    raise TcbApiError(
        f"Deposit for offer {offer.id} landed in bucket {bucket!r}, not newly_added — "
        f"clip {clip.id} was created but is NOT redeemable. See TcbSyncLog {log.id}."
    )


def pull_and_reconcile_redemptions() -> int:
    """Pulls redemption audit data from TCB and creates RedemptionEvent rows
    for anything newly redeemed, updating the matching CouponClip's state.
    Returns the count of newly-reconciled redemptions. Paginates until
    next_page_no is None.
    """
    from reporting.models import RedemptionEvent

    client = get_tcb_client()
    reconciled = 0
    page_no = None

    while True:
        records, next_page = client.pull_audit_data(mode="redemption", page_no=page_no)
        for record in records:
            if not record.redeem_timestamp:
                continue
            try:
                clip = CouponClip.objects.get(serialized_gs1=record.serialized_gs1)
            except CouponClip.DoesNotExist:
                continue  # not one of ours (shouldn't happen, but don't crash the sync)

            redeemed_at = parse_datetime(record.redeem_timestamp)
            if redeemed_at is None:
                continue  # unparseable timestamp — surfaced via TcbSyncLog on the next real pull, not here

            _, created = RedemptionEvent.objects.get_or_create(
                coupon_clip=clip,
                defaults={
                    "tenant": clip.tenant,
                    "redeemed_at": redeemed_at,
                    "tcb_transaction_ref": "",
                    "raw_payload": {
                        "serialized_gs1": record.serialized_gs1,
                        "redeem_timestamp": record.redeem_timestamp,
                    },
                },
            )
            if created:
                reconciled += 1
                clip.state = CouponClip.State.REDEEMED
                clip.redeemed_at = redeemed_at
                clip.save(update_fields=["state", "redeemed_at"])

        if next_page is None:
            break
        page_no = next_page

    return reconciled
