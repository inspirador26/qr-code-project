from allauth.account.utils import user_email
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from tenancy.models import TenantMembership


class InviteOnlySocialAccountAdapter(DefaultSocialAccountAdapter):
    """Enforces invite-based provisioning: an SSO login only attaches to a
    tenant if the authenticated email matches a pending TenantMembership
    invite (created by a tenant_admin) or an existing membership/internal
    operator record. There is no self-service signup — see the plan's Auth
    architecture section for why this is load-bearing for tenant isolation.
    """

    def is_open_for_signup(self, request, sociallogin):
        email = user_email(sociallogin.user)
        if not email:
            return False
        has_pending_invite = TenantMembership.objects.filter(
            invited_email__iexact=email,
            status=TenantMembership.Status.INVITED,
        ).exists()
        return has_pending_invite

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        email = user_email(user)
        TenantMembership.objects.filter(
            invited_email__iexact=email,
            status=TenantMembership.Status.INVITED,
        ).update(user=user, status=TenantMembership.Status.ACTIVE)
        return user
