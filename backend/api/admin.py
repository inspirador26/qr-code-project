from django.contrib import admin

from .models import ApiClient


@admin.register(ApiClient)
class ApiClientAdmin(admin.ModelAdmin):
    list_display = ["label", "tenant", "status", "created_at", "last_used_at"]
    list_filter = ["status"]
