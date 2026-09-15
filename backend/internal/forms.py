from django import forms
from django.db.models.functions import Lower

from offers.models import TcbManufacturerLink
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
    tenant = forms.ModelChoiceField(label="Account", queryset=Tenant.objects.none())

    manufacturer_email_domain = forms.ChoiceField(label="Manufacturer email domain")
    brand_id = forms.CharField(label="TCB brand ID", required=False, disabled=True)

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
        self.fields["tenant"].queryset = Tenant.objects.order_by(Lower("name"), "pk")
        if not self.is_bound and not self.initial.get("tenant"):
            self.initial["tenant"] = self.fields["tenant"].queryset.first()
        try:
            tenant = self.fields["tenant"].clean(self["tenant"].value())
        except forms.ValidationError:
            tenant = None
        self.links = list(TcbManufacturerLink.objects.filter(tenant=tenant).order_by(
            Lower("manufacturer_email_domain"), "pk"
        ))
        self.fields["manufacturer_email_domain"].choices = [
            (link.manufacturer_email_domain, link.manufacturer_email_domain) for link in self.links
        ]
        if not self.is_bound and self.links:
            self.initial["manufacturer_email_domain"] = self.links[0].manufacturer_email_domain
        selected_domain = self["manufacturer_email_domain"].value()
        self.selected_link = next((link for link in self.links
                                   if link.manufacturer_email_domain == selected_domain), None)
        self.initial["brand_id"] = self.selected_link.brand_id if self.selected_link else ""
        self.fields["brand_id"].widget.attrs["placeholder"] = "No Brand ID recorded"
        apply_panel_field_classes(self)

    def clean(self):
        cleaned = super().clean()
        if not self.links:
            self.add_error(None, "This account has no manufacturer links. Add a link in admin before creating an offer.")
        if "manufacturer_email_domain" in cleaned and self.selected_link:
            cleaned["tcb_link"] = self.selected_link
        return clean_offer_limits(self)
