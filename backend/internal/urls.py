from django.urls import path

from . import views

app_name = "internal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/new/", views.account_intake, name="account_intake"),
    path("offers/new/", views.offer_intake, name="offer_intake"),
]
