import uuid

from django.conf import settings
from django.db import models


class Tenant(models.Model):
    """One row per CPG client."""

    class Status(models.TextChoices):
        ONBOARDING = "onboarding", "Onboarding"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ONBOARDING)
    billing_contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class TenantMembership(models.Model):
    """The actual tenant-isolation boundary at the app layer: every
    tenant-scoped request must resolve through a membership row here before
    touching tenant-scoped data. See TenantContextMiddleware.
    """

    class Role(models.TextChoices):
        ADMIN = "tenant_admin", "Tenant Admin"
        EDITOR = "tenant_editor", "Tenant Editor"
        VIEWER = "tenant_viewer", "Tenant Viewer"

    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_memberships",
        null=True,
        blank=True,
        help_text="Null until the invited_email completes SSO login and the "
        "invite is accepted — see accounts.adapters.InviteOnlySocialAccountAdapter.",
    )
    invited_email = models.EmailField(
        help_text="Set at invite time; membership attaches to `user` once that "
        "email completes SSO login. See accounts.adapters.InviteOnlySocialAccountAdapter."
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INVITED)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships_invited",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "user"], name="unique_tenant_user"),
            models.UniqueConstraint(
                fields=["tenant", "invited_email"], name="unique_tenant_invited_email"
            ),
        ]

    def __str__(self):
        return f"{self.user} @ {self.tenant} ({self.role})"
