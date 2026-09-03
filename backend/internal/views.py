from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from accounts.models import InternalOperator
from offers.models import Offer
from tcb_integration.exceptions import TcbApiError
from tenancy.models import Tenant

from .forms import AccountIntakeForm
from .services import create_account_with_offer


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
