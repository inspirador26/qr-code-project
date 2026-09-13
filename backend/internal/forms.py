from django import forms
from offers.models import Offer
from tenancy.models import Tenant, TenantMembership


def apply_panel_field_classes(form):
    base_class = (
        "block w-full rounded border border-slate-300 bg-white px-3 py-2 "
        "text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 "
        "focus:ring-slate-500"
    )
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", base_class)


def clean_offer_limits(form):
    cleaned = form.cleaned_data
    total_circulation = cleaned.get("total_circulation")
    max_clips = cleaned.get("max_clips")
    if total_circulation and max_clips and max_clips > total_circulation:
        form.add_error("max_clips", "Max clips must be less than or equal to total circulation.")
    return cleaned


class AccountIntakeForm(forms.Form):
    tenant_name = forms.CharField(label="Account name", max_length=255)
    tenant_legal_name = forms.CharField(label="Legal name", max_length=255, required=False)
    billing_contact_email = forms.EmailField(label="Billing contact email", required=False)

    manufacturer_email_domain = forms.CharField(label="Manufacturer email domain", max_length=255)
    brand_id = forms.CharField(label="TCB brand ID", max_length=64, required=False)

    offer_title = forms.CharField(label="Offer title", max_length=255)
    offer_description = forms.CharField(
        label="Offer description",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    coupon_funder_id = forms.RegexField(
        label="Coupon funder ID",
        regex=r"^\d{6,12}$",
        max_length=12,
        error_messages={"invalid": "Enter 6 to 12 digits."},
    )
    offer_code = forms.RegexField(
        label="Offer code",
        regex=r"^\d{6}$",
        max_length=6,
        error_messages={"invalid": "Enter exactly 6 digits."},
    )
    total_circulation = forms.IntegerField(label="Total circulation", min_value=1)
    max_clips = forms.IntegerField(label="Max clips", min_value=1)
    campaign_days = forms.IntegerField(label="Campaign days", min_value=1, initial=30)
    redemption_days = forms.IntegerField(label="Redemption days", min_value=1, initial=60)

    invite_email = forms.EmailField(label="Invite email", required=False)
    invite_role = forms.ChoiceField(
        label="Invite role",
        choices=TenantMembership.Role.choices,
        initial=TenantMembership.Role.ADMIN,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_panel_field_classes(self)

    def clean(self):
        cleaned = super().clean()
        return clean_offer_limits(self)


class OfferIntakeForm(forms.Form):
    tenant = forms.ModelChoiceField(
        label="Account", 
        queryset=Tenant.objects.none()
    )

    manufacturer_email_domain = forms.CharField(
        label="Manufacturer email domain", 
        max_length=255,
    )
    brand_id = forms.CharField(
        label="TCB brand ID", 
        max_length=64, 
        required=False
    )

    offer_title = forms.CharField(label="Offer title", max_length=255)
    offer_description = forms.CharField(
        label="Offer description",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    coupon_funder_id = forms.RegexField(
        label="Coupon funder ID",
        regex=r"^\d{6,12}$",
        max_length=12,
        error_messages={"invalid": "Enter 6 to 12 digits."},
    )
    offer_code = forms.RegexField(
        label="Offer code",
        regex=r"^\d{6}$",
        max_length=6,
        error_messages={"invalid": "Enter exactly 6 digits."},
    )
    total_circulation = forms.IntegerField(label="Total circulation", min_value=1)
    max_clips = forms.IntegerField(label="Max clips", min_value=1)
    campaign_days = forms.IntegerField(label="Campaign days", min_value=1, initial=30)
    redemption_days = forms.IntegerField(label="Redemption days", min_value=1, initial=60)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tenant"].queryset = Tenant.objects.order_by("name")
        apply_panel_field_classes(self)

    def clean(self):
        cleaned = super().clean()
        return clean_offer_limits(self)


class OfferEditForm(forms.ModelForm):
    """Edit local offer data without implying an unsupported TCB update.

    Once a partner-managed offer has been registered/locked, only local
    presentation and distribution-limit fields remain editable. TCB-owned
    terms stay visible on the detail page but read-only until a dedicated,
    verified MOF update workflow exists.
    """

    class Meta:
        model = Offer
        fields = [
            "title",
            "description",
            "campaign_start_at",
            "campaign_end_at",
            "redemption_start_at",
            "redemption_end_at",
            "total_circulation",
            "max_clips",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "campaign_start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "campaign_end_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "redemption_start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "redemption_end_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    tcb_controlled_fields = {
        "description",
        "campaign_start_at",
        "campaign_end_at",
        "redemption_start_at",
        "redemption_end_at",
        "total_circulation",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in (
            "campaign_start_at",
            "campaign_end_at",
            "redemption_start_at",
            "redemption_end_at",
        ):
            self.fields[name].input_formats = ["%Y-%m-%dT%H:%M"]

        terms_are_locked = (
            self.instance.status != Offer.Status.DRAFT
            or self.instance.ownership_mode == Offer.OwnershipMode.CLIENT_MANAGED
        )
        if terms_are_locked:
            for name in self.tcb_controlled_fields:
                self.fields[name].disabled = True
                self.fields[name].help_text = "Read-only because these terms are controlled by TCB."

        apply_panel_field_classes(self)

    def clean(self):
        cleaned = super().clean()
        total_circulation = cleaned.get("total_circulation")
        max_clips = cleaned.get("max_clips")
        campaign_start = cleaned.get("campaign_start_at")
        campaign_end = cleaned.get("campaign_end_at")
        redemption_start = cleaned.get("redemption_start_at")
        redemption_end = cleaned.get("redemption_end_at")
        issued_count = self.instance.clips.count() if self.instance.pk else 0

        if total_circulation and max_clips and max_clips > total_circulation:
            self.add_error("max_clips", "Max clips must be less than or equal to total circulation.")
        if max_clips is not None and max_clips < issued_count:
            self.add_error(
                "max_clips",
                f"Max clips cannot be lower than the {issued_count} clips already issued.",
            )
        if campaign_start and campaign_end and campaign_end <= campaign_start:
            self.add_error("campaign_end_at", "Campaign end must be after campaign start.")
        if redemption_start and redemption_end and redemption_end < redemption_start:
            self.add_error("redemption_end_at", "Redemption end cannot be before redemption start.")
        if campaign_end and redemption_end and redemption_end < campaign_end:
            self.add_error("redemption_end_at", "Redemption end cannot be before campaign end.")
        return cleaned
