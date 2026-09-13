from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import InternalOperator
from offers.models import Offer
from tcb_integration.exceptions import TcbApiError
from tenancy.models import Tenant

from .forms import AccountIntakeForm, OfferEditForm, OfferIntakeForm
from .services import create_account_with_offer, create_offer_for_tenant


def _is_internal_operator(user) -> bool:
    return user.is_authenticated and (
        user.is_superuser or InternalOperator.objects.filter(user=user).exists()
    )


def internal_operator_required(view_func):
    @login_required
    def wrapped(request, *args, **kwargs):
        if not _is_internal_operator(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped


@internal_operator_required
def dashboard(request):
    tenants = Tenant.objects.order_by("name")
    recent_offers = Offer.objects.select_related("tenant").order_by("-created_at")[:10]
    return render(
        request,
        "internal/dashboard.html",
        {"tenants": tenants, "recent_offers": recent_offers},
    )


@internal_operator_required
def offer_detail(request, offer_id):
    offer = get_object_or_404(
        Offer.objects.select_related("tenant", "tcb_manufacturer_link"),
        id=offer_id,
    )
    return render(
        request,
        "offers/detail.html",
        {
            "offer": offer,
            "back_url": "internal:dashboard",
            "edit_url": "internal:offer_edit",
            "can_edit": offer.ownership_mode == Offer.OwnershipMode.PARTNER_MANAGED,
            "show_internal_data": True,
            "sync_logs": offer.tcb_sync_logs.order_by("-created_at")[:10],
            "clip_count": offer.clips.count(),
            "redemption_count": offer.clips.filter(state="redeemed").count(),
        },
    )


@internal_operator_required
def offer_edit(request, offer_id):
    offer = get_object_or_404(Offer.objects.select_related("tenant"), id=offer_id)
    if offer.ownership_mode != Offer.OwnershipMode.PARTNER_MANAGED:
        raise PermissionDenied

    if request.method == "POST":
        form = OfferEditForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated offer {offer.title}.")
            return redirect("internal:offer_detail", offer_id=offer.id)
    else:
        form = OfferEditForm(instance=offer)

    return render(
        request,
        "offers/edit.html",
        {
            "offer": offer,
            "form": form,
            "detail_url": "internal:offer_detail",
        },
    )


@internal_operator_required
def account_intake(request):
    if request.method == "POST":
        form = AccountIntakeForm(request.POST)
        if form.is_valid():
            try:
                result = create_account_with_offer(data=form.cleaned_data, invited_by=request.user)
            except (TcbApiError, ValueError) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    f"Created {result.tenant.name} and locked offer {result.offer.title}.",
                )
                return redirect("internal:dashboard")
    else:
        form = AccountIntakeForm(
            initial={
                "coupon_funder_id": "123456789012",
                "offer_code": "000001",
                "total_circulation": 1000,
                "max_clips": 1000,
            }
        )
    return render(request, "internal/account_intake.html", {"form": form})


@internal_operator_required
def offer_intake(request):
    if request.method == "POST":
        form = OfferIntakeForm(request.POST)
        if form.is_valid():
            try:
                result = create_offer_for_tenant(
                    tenant=form.cleaned_data["tenant"],
                    data=form.cleaned_data,
                )
            except (TcbApiError, ValueError) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    f"Added and locked offer {result.offer.title} for {result.tenant.name}.",
                )
                return redirect("internal:dashboard")
    else:
        form = OfferIntakeForm(
            initial={
                "tenant": request.GET.get("tenant"),
                "coupon_funder_id": "123456789012",
                "offer_code": "000001",
                "total_circulation": 1000,
                "max_clips": 1000,
            }
        )
    return render(request, "internal/offer_intake.html", {"form": form})
