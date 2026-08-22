from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import InternalOperator, User, UserIdentity


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "username", "is_staff", "is_active"]
    fieldsets = DjangoUserAdmin.fieldsets


@admin.register(UserIdentity)
class UserIdentityAdmin(admin.ModelAdmin):
    list_display = ["user", "provider", "provider_email", "last_used_at"]
    list_filter = ["provider"]


@admin.register(InternalOperator)
class InternalOperatorAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "created_at"]
