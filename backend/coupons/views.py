from django.http import JsonResponse


def health(request):
    """Placeholder landing/health-check view. The real consumer-facing clip
    landing page (successor to the Node POC's GET /o/:offerId) lands in
    Phase 2 — see the plan's "TCB integration seam" and phase sequence.
    """
    return JsonResponse({"status": "ok", "service": "coupon-platform"})
