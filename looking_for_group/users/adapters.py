import re

from allauth.account import app_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import filter_users_by_username, user_field, user_username, user_email, valid_email_or_none
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import generate_unique_username
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.text import slugify


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

    def clean_username(self, username, shallow=False):
        """
        Validates a username and if it is invalid.

        :returns: username
        :raises:`django.core.exceptions.ValidationError`
        """
        for validator in app_settings.USERNAME_VALIDATORS:
            validator(username)
        username_blacklist_lower = [ub.lower() for ub in app_settings.USERNAME_BLACKLIST]
        if username.lower() in username_blacklist_lower:
            raise ValidationError("Username is blacklisted")
        if not shallow:
            if filter_users_by_username(username).exists():
                raise ValidationError("Username already exists")
        return username

    def populate_user(self, request, sociallogin, data):
        """
        Override of allauth method that makes sure usernames stay url safe.
        """
        display_name = None
        external_username = data.get('username')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        name = data.get('name')
        discriminator = data.get('discriminator')
        user = sociallogin.user
        if re.match('[\S!$?+=#.@%^*(){}]', username):
            username = slugify(external_username)
        else:
            username = external_username
        try:
            username = self.clean_username(username)
        except ValidationError:
            username = generate_unique_username([first_name, last_name, email, username, discriminator, 'user'])
        if username != external_username:
            display_name = external_username
        user_username(user, username or '')
        user_email(user, valid_email_or_none(email) or '')
        name_parts = (name or '').partition(' ')
        user_field(user, 'first_name', first_name or name_parts[0])
        user_field(user, 'last_name', last_name or name_parts[2])
        user_field(user, 'display_name', display_name)
        return user
