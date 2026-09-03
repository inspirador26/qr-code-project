from django.urls import path

from . import views

app_name = "tenancy"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tenants/", views.tenant_select, name="tenant_select"),
    path("tenants/<uuid:tenant_id>/select/", views.select_tenant, name="select_tenant"),
]
