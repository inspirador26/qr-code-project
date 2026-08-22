from django.contrib import admin

from .models import CouponClip, CouponFetchCode


@admin.register(CouponClip)
class CouponClipAdmin(admin.ModelAdmin):
    list_display = ["id", "offer", "tenant", "state", "issued_at", "redeemed_at"]
    list_filter = ["state"]
    search_fields = ["serialized_gs1", "serial_number"]
    readonly_fields = ["redeemed_at"]  # written only by the TCB audit-sync job


@admin.register(CouponFetchCode)
class CouponFetchCodeAdmin(admin.ModelAdmin):
    list_display = ["fetch_code", "tenant", "mode", "valid_till_at"]
    list_filter = ["mode"]
