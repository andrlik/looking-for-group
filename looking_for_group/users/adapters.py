from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_field
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)  # pragma: no cover

    def save_user(self, request, user, form, commit=True):
        display_name = form.cleaned_data.get('display_name')
        if display_name:
            user_field(user, "display_name", display_name)
        return super().save_user(request, user, form, commit)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)  # pragma: no cover
