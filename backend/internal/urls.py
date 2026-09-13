from django.urls import path

from . import views

app_name = "internal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/new/", views.account_intake, name="account_intake"),
    path("offers/new/", views.offer_intake, name="offer_intake"),
    path("offers/<uuid:offer_id>/", views.offer_detail, name="offer_detail"),
    path("offers/<uuid:offer_id>/edit/", views.offer_edit, name="offer_edit"),
]
