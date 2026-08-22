from django.contrib import admin

from .models import Tenant, TenantMembership


class TenantMembershipInline(admin.TabularInline):
    model = TenantMembership
    extra = 0
    fields = ["invited_email", "user", "role", "status"]


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "created_at"]
    list_filter = ["status"]
    inlines = [TenantMembershipInline]


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ["tenant", "invited_email", "user", "role", "status"]
    list_filter = ["role", "status"]
