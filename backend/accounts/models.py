import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class _EmailUserManager(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        return super()._create_user(username or email, email, password, **extra_fields)


class User(AbstractUser):
    """Global identity — not tenant-owned. A person (e.g. agency staff) can
    hold memberships in more than one tenant; see tenancy.TenantMembership.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = _EmailUserManager()

    def __str__(self):
        return self.email


class UserIdentity(models.Model):
    """Links a User to one SSO login. Resolved by (provider, provider_subject)
    on every OIDC callback — see accounts/adapters.py.
    """

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        MICROSOFT = "microsoft", "Microsoft"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="identities")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_subject = models.CharField(max_length=255)
    provider_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_subject"],
                name="unique_provider_subject",
            )
        ]

    def __str__(self):
        return f"{self.user.email} via {self.provider}"


class InternalOperator(models.Model):
    """Our own ops/support staff. Deliberately separate from
    tenancy.TenantMembership (not a pseudo-tenant) so cross-tenant power is
    distinct and auditable, never confusable with a client role.
    """

    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin"
        SUPPORT = "support", "Support"
        OPS = "ops", "Ops"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="internal_operator")
    role = models.CharField(max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} ({self.role})"
