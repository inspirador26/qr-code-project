from django.contrib import admin

from .models import TcbSyncLog, TcbSyncLogClip


class TcbSyncLogClipInline(admin.TabularInline):
    model = TcbSyncLogClip
    extra = 0
    readonly_fields = ["coupon_clip", "outcome_bucket"]


@admin.register(TcbSyncLog)
class TcbSyncLogAdmin(admin.ModelAdmin):
    list_display = ["operation", "status", "tenant", "attempt_count", "next_retry_at", "created_at"]
    list_filter = ["operation", "status"]
    readonly_fields = ["request_payload", "response_payload"]
    inlines = [TcbSyncLogClipInline]
