import uuid

from django.conf import settings
from django.db import models
from oauth2_provider.models import Application


class ApiClient(models.Model):
    """A CPG's programmatic access to their own reporting/offer data —
    OAuth2 client-credentials grant via django-oauth-toolkit. This model
    links a tenant to an oauth2_provider.Application rather than storing
    secrets itself (oauth-toolkit already handles client_secret hashing).
    See the plan's Auth architecture section.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="api_clients"
    )
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, related_name="api_client"
    )
    label = models.CharField(max_length=255, blank=True)
    scopes = models.JSONField(default=list, blank=True, help_text='e.g. ["read:offers", "read:reports"]')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.label or self.application.name} ({self.tenant})"
