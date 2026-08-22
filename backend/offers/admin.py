from django.contrib import admin

from .models import DistributionChannel, Offer, OfferChannelConfig, TcbManufacturerLink


@admin.register(TcbManufacturerLink)
class TcbManufacturerLinkAdmin(admin.ModelAdmin):
    list_display = ["manufacturer_email_domain", "tenant", "brand_id", "connection_status"]
    list_filter = ["connection_status"]


@admin.register(DistributionChannel)
class DistributionChannelAdmin(admin.ModelAdmin):
    list_display = ["display_name", "code", "is_active"]


class OfferChannelConfigInline(admin.TabularInline):
    model = OfferChannelConfig
    extra = 0


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ["title", "tenant", "status", "ownership_mode", "base_gs1"]
    list_filter = ["status", "ownership_mode"]
    search_fields = ["title", "base_gs1", "offer_code"]
    inlines = [OfferChannelConfigInline]
