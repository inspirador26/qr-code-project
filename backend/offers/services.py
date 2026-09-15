"""Offer eligibility rules shared by every clip entry point."""

from django.utils import timezone

from coupons.models import CouponClip
from offers.exceptions import (
    OfferNotClippable, OfferSoldOut, OfferWindowClosed, OfferWindowNotStarted,
)
from offers.models import Offer


def ensure_offer_clippable(offer: Offer) -> None:
    """Check status, inclusive campaign window, and non-void clip count.

    The count is not locked; TCB's circulation cap remains the hard backstop
    for concurrent requests. Redemption dates are enforced by TCB at POS.
    """
    if offer.status != Offer.Status.ACTIVE:
        raise OfferNotClippable()
    now = timezone.now()
    if now < offer.campaign_start_at:
        raise OfferWindowNotStarted()
    if now > offer.campaign_end_at:
        raise OfferWindowClosed()
    issued = CouponClip.objects.filter(offer=offer).exclude(
        state=CouponClip.State.VOID,
    ).count()
    if issued >= offer.max_clips:
        raise OfferSoldOut()
