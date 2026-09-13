from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from offers.models import Offer
from internal.forms import OfferEditForm

from .middleware import set_active_tenant
from .models import Tenant, TenantMembership


def _active_memberships(user):
    return TenantMembership.objects.select_related("tenant").filter(
        user=user,
        status=TenantMembership.Status.ACTIVE,
    )


@login_required
def tenant_select(request):
    memberships = _active_memberships(request.user).order_by("tenant__name")
    return render(request, "tenancy/tenant_select.html", {"memberships": memberships})


@login_required
def select_tenant(request, tenant_id):
    if request.method != "POST":
        raise PermissionDenied
    membership = get_object_or_404(_active_memberships(request.user), tenant_id=tenant_id)
    set_active_tenant(request, membership.tenant)
    messages.success(request, f"Working in {membership.tenant.name}.")
    return redirect("tenancy:dashboard")


@login_required
def dashboard(request):
    memberships = _active_memberships(request.user)
    if not memberships.exists():
        raise PermissionDenied

    tenant = request.tenant
    if tenant is None:
        return redirect("tenancy:tenant_select")

    tenant = get_object_or_404(Tenant, memberships__in=memberships, id=tenant.id)
    offers = Offer.objects.filter(tenant=tenant).order_by("-created_at")
    return render(
        request,
        "tenancy/dashboard.html",
        {"tenant": tenant, "offers": offers, "memberships": memberships},
    )


def _selected_membership(request):
    if request.tenant is None:
        return None
    return get_object_or_404(
        _active_memberships(request.user),
        tenant_id=request.tenant.id,
    )


def _membership_can_edit_offers(membership):
    return membership.role in {
        TenantMembership.Role.ADMIN,
        TenantMembership.Role.EDITOR,
    }


@login_required
def offer_detail(request, offer_id):
    membership = _selected_membership(request)
    if membership is None:
        return redirect("tenancy:tenant_select")

    offer = get_object_or_404(
        Offer.objects.select_related("tenant", "tcb_manufacturer_link"),
        id=offer_id,
        tenant=membership.tenant,
    )
    can_edit = (
        _membership_can_edit_offers(membership)
        and offer.ownership_mode == Offer.OwnershipMode.PARTNER_MANAGED
    )
    return render(
        request,
        "offers/detail.html",
        {
            "offer": offer,
            "back_url": "tenancy:dashboard",
            "edit_url": "tenancy:offer_edit",
            "can_edit": can_edit,
            "show_internal_data": False,
            "sync_logs": offer.tcb_sync_logs.order_by("-created_at")[:10],
            "clip_count": offer.clips.count(),
            "redemption_count": offer.clips.filter(state="redeemed").count(),
        },
    )


@login_required
def offer_edit(request, offer_id):
    membership = _selected_membership(request)
    if membership is None:
        return redirect("tenancy:tenant_select")

    offer = get_object_or_404(
        Offer.objects.select_related("tenant"),
        id=offer_id,
        tenant=membership.tenant,
    )
    if not _membership_can_edit_offers(membership):
        raise PermissionDenied
    if offer.ownership_mode != Offer.OwnershipMode.PARTNER_MANAGED:
        raise PermissionDenied

    if request.method == "POST":
        form = OfferEditForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated offer {offer.title}.")
            return redirect("tenancy:offer_detail", offer_id=offer.id)
    else:
        form = OfferEditForm(instance=offer)

    return render(
        request,
        "offers/edit.html",
        {
            "offer": offer,
            "form": form,
            "detail_url": "tenancy:offer_detail",
        },
    )

# Create your views here.
