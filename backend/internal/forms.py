from django import forms

from tenancy.models import TenantMembership


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
        base_class = (
            "block w-full rounded border border-slate-300 bg-white px-3 py-2 "
            "text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 "
            "focus:ring-slate-500"
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", base_class)

    def clean(self):
        cleaned = super().clean()
        total_circulation = cleaned.get("total_circulation")
        max_clips = cleaned.get("max_clips")
        if total_circulation and max_clips and max_clips > total_circulation:
            self.add_error("max_clips", "Max clips must be less than or equal to total circulation.")
        return cleaned
