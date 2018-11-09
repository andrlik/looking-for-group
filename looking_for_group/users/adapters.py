from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_field
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.urls import reverse_lazy


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)  # pragma: no cover

    def save_user(self, request, user, form, commit=True):
        display_name = form.cleaned_data.get('display_name')
        tz = form.cleaned_data.get('timezone')
        if display_name:
            user_field(user, "display_name", display_name)
        if tz:
            user_field(user, "timezone", tz)
        return super().save_user(request, user, form, commit)

    def get_login_redirect_url(self, request):
        return reverse_lazy('dashboard')


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)  # pragma: no cover
