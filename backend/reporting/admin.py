from django.contrib import admin

from .models import ClipEvent, PromoReport, RedemptionEvent


@admin.register(ClipEvent)
class ClipEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "tenant", "offer", "occurred_at"]
    list_filter = ["event_type"]


@admin.register(RedemptionEvent)
class RedemptionEventAdmin(admin.ModelAdmin):
    list_display = ["coupon_clip", "tenant", "redeemed_at", "pulled_at"]


@admin.register(PromoReport)
class PromoReportAdmin(admin.ModelAdmin):
    list_display = ["offer", "tenant", "period_start", "period_end", "status"]
    list_filter = ["status"]
