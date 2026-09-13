from django.urls import path

from . import views

app_name = "tenancy"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tenants/", views.tenant_select, name="tenant_select"),
    path("tenants/<uuid:tenant_id>/select/", views.select_tenant, name="select_tenant"),
    path("offers/<uuid:offer_id>/", views.offer_detail, name="offer_detail"),
    path("offers/<uuid:offer_id>/edit/", views.offer_edit, name="offer_edit"),
]
