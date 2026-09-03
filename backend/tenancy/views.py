from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from offers.models import Offer

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

# Create your views here.
