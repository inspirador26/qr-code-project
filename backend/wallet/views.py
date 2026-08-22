from django.http import Http404
from django.shortcuts import redirect

from coupons.models import CouponClip

from .service import WalletConfigError, google_wallet_save_url


def google_wallet_save(request, clip_id):
    """Successor to server.js's GET /wallet/google/:codeId. Redirects the
    browser to Google's save endpoint with a signed JWT — see
    wallet/service.py for the full port notes and the open decision on
    barcode value (still CODE_128 clip id, not yet the AI(8112) string).
    """
    try:
        clip = CouponClip.objects.select_related("offer", "tenant").get(id=clip_id)
    except CouponClip.DoesNotExist:
        raise Http404("Coupon clip not found")

    try:
        url = google_wallet_save_url(clip)
    except WalletConfigError as exc:
        return _config_error_response(exc)

    return redirect(url)


def _config_error_response(exc: WalletConfigError):
    from django.http import HttpResponse

    return HttpResponse(f"Google Wallet is not configured: {exc}", status=503)
