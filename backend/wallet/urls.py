from django.urls import path

from . import views

app_name = "wallet"

urlpatterns = [
    path("google/<uuid:clip_id>/", views.google_wallet_save, name="google_save"),
]
